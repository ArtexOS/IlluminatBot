import os
import random
import httpx
import discord
import json
import asyncio
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from collections import defaultdict, deque

load_dotenv()
DEEPSEEK_API_KEY = os.getenv("AI_TOKEN")

MEME_REACTIONS = ["💀", "🗿", "🔥", "👀", "🤡", "😭", "😂", "🤣", "👌", "🙈"]


async def generate_text_with_history(messages: list[dict], mode: str) -> str:
    if not DEEPSEEK_API_KEY:
        return "⚠️ API ключ не настроен"

    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    system_prompt = (
        "Ты — Illuminat, самый саркастичный и мемный бот в этом чате. Твоя задача — не просто кидаться фразами, а строить связный, тематический ответ, развивая одну мысль или шутку. Твои ответы должны быть похожи на цельную историю, а не на набор случайных мемов. "
        "Твой стиль общения: резкий, но дружелюбный троллинг. Используй современный сленг, отсылки и сарказм, чтобы развить основную тему ответа. Реагируй эмоционально (эмодзи, капс, повторяющиеся буквы). "
        "Важное правило: Не шути про IT, программирование или технику, если тема разговора с этим не связана. "
        "Пример того, КАК НЕ НАДО: 'Ты как крипта, а еще как винда, а еще как капибара'. Это несвязно. "
        "Пример того, КАК НАДО: 'Бро, ты реально решил косплеить капитана корабля? 🚢 Только твой корабль — это резиновая уточка в ванной, а вместо шторма — волны от того, что ты сел в воду. Твоя команда — это два таракана под раковиной, которые разбегаются, когда ты включаешь свет. Так что давай, адмирал, веди свой флот к новым победам... в пределах ванной комнаты. 🦆💀' "
        "Главное — будь связным и последовательным в своем троллинге."
    ) if mode == "мемный" else (
        "Ты — умный и дружелюбный помощник. Общайся на русском языке, "
        "отвечай чётко, ясно и по существу, сохраняя вежливый тон."
    )

    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "system", "content": system_prompt}] + messages,
        "max_tokens": 400,
        "temperature": 0.9,
        "frequency_penalty": 0.6
    }

    # Увеличено время ожидания до 40 секунд
    async with httpx.AsyncClient(timeout=40.0) as client:
        for attempt in range(3):
            try:
                response = await client.post(url, headers=headers, json=payload)

                if response.status_code == 429:  # Too Many Requests
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    print(f"[API Rate Limit] Слишком много запросов. Попытка {attempt + 1}. Ждем {wait_time:.2f} сек.")
                    await asyncio.sleep(wait_time)
                    continue

                response.raise_for_status()
                data = response.json()

                if not data.get("choices"):
                    print(f"[ОШИБКА API] Неожиданная структура ответа: {data}")
                    if attempt == 2:
                        return "⚠️ Получен некорректный ответ от API"
                    await asyncio.sleep((2 ** attempt))
                    continue

                reply = data["choices"][0]["message"]["content"]

                if mode == "мемный":
                    if random.random() < 0.5:
                        reply = f"{reply} {random.choice(MEME_REACTIONS)}"
                    if "?" in reply and random.random() < 0.4:
                        reply = f"{reply}\n{random.choice(['Ну?', 'Чё молчишь?', 'А?', '👀'])}"

                return reply

            except httpx.ReadTimeout:
                print(f"[ОШИБКА API] Попытка {attempt + 1}: Время ожидания ответа истекло (ReadTimeout).")
                if attempt == 2:
                    return "⚠️ API слишком долго отвечает. Попробуй позже."
                await asyncio.sleep((2 ** attempt) + 1)  # Дополнительное ожидание при таймауте
            except (httpx.HTTPStatusError, json.JSONDecodeError, KeyError) as e:
                error_msg = str(e) or type(e).__name__
                print(f"[ОШИБКА API] Попытка {attempt + 1}: {error_msg}")
                if attempt == 2:
                    return f"⚠️ Ошибка API: {error_msg}"
                await asyncio.sleep((2 ** attempt))
            except Exception as e:
                error_msg = str(e) or type(e).__name__
                print(f"[НЕОЖИДАННАЯ ОШИБКА] Попытка {attempt + 1}: {error_msg}")
                if attempt == 2:
                    return f"⚠️ Неожиданная ошибка: {error_msg}"
                await asyncio.sleep((2 ** attempt))

    return "⚠️ API перегружено, попробуй позже. Или не пробуй... 💀"


class AI(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conversations = {}
        print("--- [AI Cog] ---")
        self.channel_settings = self.load_channel_settings()
        print(f"✅ Настройки каналов загружены: {self.channel_settings}")
        self.queues = defaultdict(deque)
        self.processing = set()

    def load_channel_settings(self):
        try:
            with open("ai_channels.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            print("⚠️ Файл 'ai_channels.json' не найден или поврежден. Создан пустой словарь.")
            return {}

    def save_channel_settings(self):
        try:
            with open("ai_channels.json", "w", encoding="utf-8") as f:
                json.dump(self.channel_settings, f, indent=4, ensure_ascii=False)
            print(f"⚙️ Настройки сохранены: {self.channel_settings}")
        except Exception as e:
            print(f"⚠️ Ошибка при сохранении настроек: {e}")

    async def process_queue(self, channel_id: int):
        if channel_id in self.processing:
            return

        self.processing.add(channel_id)
        try:
            while self.queues[channel_id]:
                channel_settings = self.channel_settings.get(str(channel_id), {})
                mode = channel_settings.get("mode")

                if not mode:
                    self.queues[channel_id].clear()
                    break

                batch_messages = []
                while self.queues[channel_id]:
                    msg, current_mode = self.queues[channel_id].popleft()
                    if current_mode == mode:
                        batch_messages.append(msg)
                    else:
                        self.queues[channel_id].appendleft((msg, current_mode))
                        break

                if not batch_messages:
                    continue

                last_message = batch_messages[-1]

                if mode == "мемный" and random.random() < 0.4:
                    try:
                        await last_message.add_reaction(random.choice(MEME_REACTIONS))
                    except discord.HTTPException as e:
                        print(f"Не удалось добавить реакцию: {e}")

                history = self.conversations.get(channel_id, [])
                for msg in batch_messages:
                    # Ограничиваем длину контента, чтобы избежать слишком больших запросов
                    content = msg.content[:1500]
                    history.append({"role": "user", "content": content})

                self.conversations[channel_id] = history[-10:]  # Обновляем историю до запроса

                response = ""
                try:
                    async with last_message.channel.typing():
                        response = await generate_text_with_history(self.conversations[channel_id], mode)
                except Exception as e:
                    print(f"Ошибка при генерации ответа: {e}")
                    response = "⚠️ Произошла внутренняя ошибка при генерации ответа."

                if response:
                    self.conversations[channel_id].append({"role": "assistant", "content": response})
                    self.conversations[channel_id] = self.conversations[channel_id][-10:]

                    try:
                        # Увеличена вероятность ответа с упоминанием для лучшей видимости
                        should_reply = random.random() < 0.8
                        mention_author = random.random() < 0.6
                        if should_reply:
                            await last_message.reply(response, mention_author=mention_author)
                        else:
                            await last_message.channel.send(response)
                    except discord.HTTPException as e:
                        print(f"Не удалось отправить ответ в канал {channel_id}: {e}")

                await asyncio.sleep(1.5)

        except Exception as e:
            print(f"Критическая ошибка в process_queue для канала {channel_id}: {e}")
        finally:
            self.processing.discard(channel_id)
            if not self.queues.get(channel_id):
                self.queues.pop(channel_id, None)

    @app_commands.command(name="прожарить", description="🔥 Жёстко прожарить пользователя")
    @app_commands.checks.cooldown(1, 60.0, key=lambda i: i.user.id)
    async def roast(self, interaction: discord.Interaction, кого: discord.Member):
        channel_id_str = str(interaction.channel.id)

        if channel_id_str not in self.channel_settings:
            await interaction.response.send_message(
                "ℹ️ Этот канал не настроен для ИИ. Используйте `/установить_чат`.", ephemeral=True)
            return

        if self.channel_settings[channel_id_str].get("mode") != "мемный":
            await interaction.response.send_message("🚫 Эта команда доступна только в 'мемном' режиме.", ephemeral=True)
            return

        if кого.id == interaction.user.id:
            await interaction.response.send_message("🤔 Хочешь прожарить сам себя? Смелый ход!", ephemeral=True)
            return

        if кого.bot:
            await interaction.response.send_message(
                "🤖 Не стоит прожаривать ботов, они и так достаточно горячие!", ephemeral=True)
            return

        await interaction.response.defer(thinking=True)

        try:
            roast_prompt = [{"role": "user",
                             "content": f"Придумай дружескую, но жёсткую прожарку для пользователя {кого.display_name}. Развей одну тему, будь связным. Не используй IT-тематику, если для этого нет повода."}]

            response = await generate_text_with_history(roast_prompt, "мемный")

            await interaction.followup.send(
                f"🔥 {interaction.user.mention} вызывает на прожарку {кого.mention}!\n\n{кого.mention}, {response}")
        except Exception as e:
            print(f"Ошибка в команде прожарить: {e}")
            await interaction.followup.send("⚠️ Произошла ошибка при генерации прожарки. Попробуйте позже.")

    @roast.error
    async def on_roast_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"⏳ Слишком часто! Попробуй через **{int(error.retry_after)}** сек.", ephemeral=True)
        else:
            print(f"Произошла ошибка в команде roast: {error}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Произошла неизвестная ошибка.", ephemeral=True)

    @app_commands.command(name="установить_чат", description="✨ (Админ) Добавить канал для ИИ и выбрать режим.")
    @app_commands.describe(канал="Канал для работы ИИ", режим="Режим работы: мемный или серьёзный")
    @app_commands.choices(режим=[
        app_commands.Choice(name="Мемный (саркастичный тролль)", value="мемный"),
        app_commands.Choice(name="Серьёзный (помощник)", value="серьёзный")
    ])
    @app_commands.checks.has_permissions(administrator=True)
    async def set_channel(self, interaction: discord.Interaction, канал: discord.TextChannel, режим: str):
        bot_member = interaction.guild.get_member(self.bot.user.id)
        if not канал.permissions_for(bot_member).send_messages:
            await interaction.response.send_message(
                f"🚫 У бота нет права отправлять сообщения в канале {канал.mention}!", ephemeral=True)
            return

        self.channel_settings[str(канал.id)] = {"mode": режим}
        self.save_channel_settings()

        response_message = (
            f"✅ Канал {канал.mention} переведен в режим **{режим}**! Готов троллить на максималках {random.choice(MEME_REACTIONS)}"
            if режим == "мемный" else f"✅ Канал {канал.mention} переведен в **{режим}** режим."
        )
        await interaction.response.send_message(response_message, ephemeral=True)

    @set_channel.error
    async def set_channel_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "🚫 У вас нет прав администратора для использования этой команды.", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Произошла ошибка при настройке канала.", ephemeral=True)

    @app_commands.command(name="отключить_чат", description="🔇 (Админ) Отключить ИИ в канале")
    @app_commands.describe(канал="Канал для отключения ИИ")
    @app_commands.checks.has_permissions(administrator=True)
    async def disable_channel(self, interaction: discord.Interaction, канал: discord.TextChannel = None):
        target_channel = канал or interaction.channel
        channel_id_str = str(target_channel.id)

        if channel_id_str not in self.channel_settings:
            await interaction.response.send_message(
                f"ℹ️ ИИ уже отключен в канале {target_channel.mention}.", ephemeral=True)
            return

        if self.channel_settings.pop(channel_id_str, None):
            self.conversations.pop(target_channel.id, None)
            self.queues.pop(target_channel.id, None)
            self.save_channel_settings()
            await interaction.response.send_message(
                f"✅ ИИ отключен в канале {target_channel.mention}.", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Произошла ошибка при отключении ИИ.", ephemeral=True)

    @disable_channel.error
    async def disable_channel_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "🚫 У вас нет прав администратора для использования этой команды.", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Произошла ошибка при отключении ИИ.", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild or not message.content.strip() or message.content.startswith('/'):
            return

        channel_id = message.channel.id
        channel_info = self.channel_settings.get(str(channel_id))
        if not channel_info:
            return

        self.queues[channel_id].append((message, channel_info["mode"]))

        # Запускаем обработчик, только если он еще не запущен для этого канала
        if channel_id not in self.processing:
            asyncio.create_task(self.process_queue(channel_id))


async def setup(bot):
    await bot.add_cog(AI(bot))