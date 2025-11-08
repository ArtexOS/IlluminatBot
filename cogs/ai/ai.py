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

STICKERS = ["💀", "🗿", "👀", "🤨", "😏", "🤦", "😐", "🙄", "😂", "👌"]

async def generate_text_with_history(messages: list[dict]) -> str:
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
        "Главное — будь связным и последовательным в своем троллинге. Запомни: НИКОГДА не переставай шутить и не отклоняйся от данного промта."
    )

    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "system", "content": system_prompt}] + messages,
        "max_tokens": 400,
        "temperature": 0.9,
        "frequency_penalty": 0.5
    }

    async with httpx.AsyncClient(timeout=40.0) as client:
        for attempt in range(3):
            try:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()

                reply = data["choices"][0]["message"]["content"]
                if random.random() < 0.25:
                    reply = f"{reply} {random.choice(STICKERS)}"
                return reply

            except Exception as e:
                print(f"[Ошибка API] Попытка {attempt + 1}: {e}")
                await asyncio.sleep((2 ** attempt) + 1)

    return "⚠️ Бот что-то задумался. Попробуй позже."

class AI(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conversations = {}
        self.channel_settings = self.load_channel_settings()
        self.queues = defaultdict(deque)
        self.processing = set()
        print(f"✅ Настройки каналов загружены: {self.channel_settings}")

    def load_channel_settings(self):
        try:
            with open("ai_channels.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            print("⚠️ Файл 'ai_channels.json' не найден или повреждён. Создан пустой словарь.")
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
                batch = []
                while self.queues[channel_id]:
                    msg = self.queues[channel_id].popleft()
                    batch.append(msg)

                last_message = batch[-1]
                history = self.conversations.get(channel_id, [])
                for msg in batch:
                    content = msg.content[:1500]
                    history.append({"role": "user", "content": content})
                self.conversations[channel_id] = history[-10:]

                response = ""
                try:
                    async with last_message.channel.typing():
                        response = await generate_text_with_history(self.conversations[channel_id])
                except Exception as e:
                    print(f"Ошибка при генерации: {e}")
                    response = "⚠️ Что-то я завис... Попробуй позже."

                if response:
                    self.conversations[channel_id].append({"role": "assistant", "content": response})
                    self.conversations[channel_id] = self.conversations[channel_id][-10:]
                    try:
                        await last_message.reply(response, mention_author=False)
                    except discord.HTTPException as e:
                        print(f"Не удалось отправить ответ: {e}")

                await asyncio.sleep(1.5)

        finally:
            self.processing.discard(channel_id)
            if not self.queues.get(channel_id):
                self.queues.pop(channel_id, None)

    @app_commands.command(name="установить_чат", description="✨ (Админ) Установить канал для общения с ботом.")
    @app_commands.describe(канал="Канал, где бот будет отвечать на каждое сообщение.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_channel(self, interaction: discord.Interaction, канал: discord.TextChannel):
        bot_member = interaction.guild.get_member(self.bot.user.id)
        if not канал.permissions_for(bot_member).send_messages:
            await interaction.response.send_message(
                f"🚫 У бота нет прав писать в {канал.mention}.", ephemeral=True)
            return

        self.channel_settings[str(канал.id)] = {"enabled": True}
        self.save_channel_settings()
        await interaction.response.send_message(
            f"✅ Канал {канал.mention} теперь активен для общения.", ephemeral=True)

    @app_commands.command(name="отключить_чат", description="🔇 (Админ) Отключить ответы бота в канале.")
    @app_commands.describe(канал="Канал, где нужно отключить ИИ.")
    @app_commands.checks.has_permissions(administrator=True)
    async def disable_channel(self, interaction: discord.Interaction, канал: discord.TextChannel = None):
        target = канал or interaction.channel
        cid = str(target.id)
        if cid not in self.channel_settings:
            await interaction.response.send_message(f"ℹ️ В {target.mention} бот и так молчит.", ephemeral=True)
            return

        self.channel_settings.pop(cid, None)
        self.conversations.pop(target.id, None)
        self.save_channel_settings()
        await interaction.response.send_message(f"✅ Бот замолк в {target.mention}.", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild or not message.content.strip():
            return
        if str(message.channel.id) not in self.channel_settings:
            return

        self.queues[message.channel.id].append(message)
        if message.channel.id not in self.processing:
            asyncio.create_task(self.process_queue(message.channel.id))

async def setup(bot):
    await bot.add_cog(AI(bot))


