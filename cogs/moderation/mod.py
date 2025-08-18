import datetime
import discord
import re
from discord import app_commands
from discord.ext import commands

from database.warn.functions import Database
from database.warn.connection import create_tables

# --- ID Ролей и канала для логов ---
LOG_CHANNEL_ID = 1400850936640831630
OWNER_ROLES = [1405996238519926984]
ADMIN_ROLES = OWNER_ROLES + [1405996476487696566, 1405996543592497333]
HEAD_MODERATOR_ROLES = ADMIN_ROLES + [1407064998932516874]
MODERATOR_ROLES = HEAD_MODERATOR_ROLES + [1405996596474417323]
JR_MODERATOR_ROLES = MODERATOR_ROLES + [1407064791914119219]
TRAINEE_ROLES = JR_MODERATOR_ROLES + [1407063984921645117]


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = Database()
        self.log_channel = None

    # --- Новая функция для отправки логов ---
    async def _send_log(self, embed: discord.Embed):
        if self.log_channel:
            try:
                await self.log_channel.send(embed=embed)
            except (discord.Forbidden, discord.HTTPException) as e:
                print(f"ERROR: Could not send log message. {e}")

    @commands.Cog.listener()
    async def on_ready(self):
        await create_tables()
        # --- Получаем канал для логов при старте ---
        if LOG_CHANNEL_ID:
            self.log_channel = self.bot.get_channel(LOG_CHANNEL_ID)
            if self.log_channel is None:
                try:
                    self.log_channel = await self.bot.fetch_channel(LOG_CHANNEL_ID)
                except (discord.NotFound, discord.Forbidden):
                    print(f"ERROR: Could not find or access the log channel with ID {LOG_CHANNEL_ID}.")

        print("Moderation Cog is Ready")

    # --- КОМАНДЫ ПРЕДУПРЕЖДЕНИЙ ---

    @app_commands.command(name="пред", description="✔️ Выдать предупреждение участнику")
    @app_commands.checks.has_any_role(*TRAINEE_ROLES)
    async def warn_cmd(self, inter: discord.Interaction, участник: discord.Member, причина: str):
        if участник.bot or участник == inter.user:
            embed = discord.Embed(description="❌ Нельзя выдать предупреждение боту или самому себе.",
                                  color=discord.Color.red())
            await inter.response.send_message(embed=embed, ephemeral=True)
            return

        await self.db.add_warn(user_id=участник.id, moderator_id=inter.user.id, reason=причина,
                               start_time=datetime.datetime.now())

        # Ответ в чат
        embed = discord.Embed(title="✅ Предупреждение выдано",
                              description=f"Модератор {inter.user.mention} выдал предупреждение {участник.mention}\n**Причина:** {причина}",
                              color=discord.Color.orange())
        await inter.response.send_message(embed=embed)

        # Логирование
        log_embed = discord.Embed(title="📜 Выдано предупреждение", color=discord.Color.orange(),
                                  timestamp=datetime.datetime.now())
        log_embed.add_field(name="Участник", value=f"{участник.mention} (`{участник.id}`)", inline=False)
        log_embed.add_field(name="Модератор", value=f"{inter.user.mention} (`{inter.user.id}`)", inline=False)
        log_embed.add_field(name="Причина", value=причина, inline=False)
        await self._send_log(log_embed)

    @app_commands.command(name="преды", description="📜 Посмотреть предупреждения участника")
    @app_commands.checks.has_any_role(*TRAINEE_ROLES)
    async def warns_cmd(self, inter: discord.Interaction, участник: discord.Member = None):
        if not участник: участник = inter.user
        warns = await self.db.get_warns(user_id=участник.id)
        if not warns:
            embed = discord.Embed(description=f"✨ У {участник.mention} нет предупреждений.",
                                  color=discord.Color.green())
            await inter.response.send_message(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(title=f"⚠️ Предупреждения {участник.display_name} ({len(warns)} шт.)",
                              color=discord.Color.gold())
        description = []
        for warn in warns:
            start_time_formatted = discord.utils.format_dt(warn.start_time, 'R')
            description.append(
                f"**ID:** `{warn.id}` | **Выдан:** {start_time_formatted}\n👮 **Модератор:** <@{warn.moderator_id}>\n💬 **Причина:** {warn.reason}")
        embed.description = "\n\n".join(description)
        await inter.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="снятьпред", description="🗑️ Снять предупреждение по ID")
    @app_commands.checks.has_any_role(*MODERATOR_ROLES)
    async def unwarn_cmd(self, inter: discord.Interaction, id: int):
        await self.db.remove_warn_by_id(warn_id=id)
        embed = discord.Embed(description=f"✅ Предупреждение с ID `{id}` было успешно удалено.",
                              color=discord.Color.green())
        await inter.response.send_message(embed=embed, ephemeral=True)

        # Логирование
        log_embed = discord.Embed(title="🗑️ Снято предупреждение", color=0x99B873, timestamp=datetime.datetime.now())
        log_embed.add_field(name="ID Предупреждения", value=f"`{id}`", inline=False)
        log_embed.add_field(name="Модератор", value=f"{inter.user.mention} (`{inter.user.id}`)", inline=False)
        await self._send_log(log_embed)

    @app_commands.command(name="сброспред", description="🗑️🗑️ Снять все предупреждения с участника")
    @app_commands.checks.has_any_role(*HEAD_MODERATOR_ROLES)
    async def clearwarns_cmd(self, inter: discord.Interaction, участник: discord.Member):
        await self.db.remove_all_warns(user_id=участник.id)
        embed = discord.Embed(description=f"✅ Все предупреждения для {участник.mention} были сняты.",
                              color=discord.Color.green())
        await inter.response.send_message(embed=embed)

        # Логирование
        log_embed = discord.Embed(title="🗑️🗑️ Сняты все предупреждения", color=0x99B873,
                                  timestamp=datetime.datetime.now())
        log_embed.add_field(name="Участник", value=f"{участник.mention} (`{участник.id}`)", inline=False)
        log_embed.add_field(name="Модератор", value=f"{inter.user.mention} (`{inter.user.id}`)", inline=False)
        await self._send_log(log_embed)

    # --- ОСНОВНЫЕ КОМАНДЫ МОДЕРАЦИИ ---

    @app_commands.command(name="кик", description="👢 Кикнуть участника с сервера")
    @app_commands.checks.has_any_role(*MODERATOR_ROLES)
    async def kick_cmd(self, inter: discord.Interaction, участник: discord.Member, причина: str):
        embed = discord.Embed(title="👢 Участник кикнут",
                              description=f"{участник.mention} был кикнут.\n**Причина:** {причина}", color=0xDD742B)
        await участник.kick(reason=f"Модератор: {inter.user.display_name}. Причина: {причина}")
        await inter.response.send_message(embed=embed)

        # Логирование
        log_embed = discord.Embed(title="👢 Кик", color=0xDD742B, timestamp=datetime.datetime.now())
        log_embed.add_field(name="Участник", value=f"{участник.mention} (`{участник.id}`)", inline=False)
        log_embed.add_field(name="Модератор", value=f"{inter.user.mention} (`{inter.user.id}`)", inline=False)
        log_embed.add_field(name="Причина", value=причина, inline=False)
        await self._send_log(log_embed)

    @app_commands.command(name="бан", description="🚫 Забанить участника на сервере")
    @app_commands.checks.has_any_role(*HEAD_MODERATOR_ROLES)
    async def ban_cmd(self, inter: discord.Interaction, участник: discord.Member, причина: str):
        embed = discord.Embed(title="🚫 Участник забанен",
                              description=f"{участник.mention} был забанен.\n**Причина:** {причина}", color=0xA22C2C)
        await участник.ban(reason=f"Модератор: {inter.user.display_name}. Причина: {причина}")
        await inter.response.send_message(embed=embed)

        # Логирование
        log_embed = discord.Embed(title="🚫 Бан", color=0xA22C2C, timestamp=datetime.datetime.now())
        log_embed.add_field(name="Участник", value=f"{участник.mention} (`{участник.id}`)", inline=False)
        log_embed.add_field(name="Модератор", value=f"{inter.user.mention} (`{inter.user.id}`)", inline=False)
        log_embed.add_field(name="Причина", value=причина, inline=False)
        await self._send_log(log_embed)

    @app_commands.command(name="разбан", description="✅ Разбанить участника по ID")
    @app_commands.describe(пользователь_id="ID пользователя, которого нужно разбанить", причина="Причина разбана")
    @app_commands.checks.has_any_role(*HEAD_MODERATOR_ROLES)
    async def unban_cmd(self, inter: discord.Interaction, пользователь_id: str, причина: str = "Не указана"):
        # Проверяем, является ли ID числом
        if not пользователь_id.isdigit():
            embed = discord.Embed(title="❌ Ошибка", description="ID пользователя должен состоять только из цифр.",
                                  color=discord.Color.red())
            await inter.response.send_message(embed=embed, ephemeral=True)
            return

        user_id_int = int(пользователь_id)

        try:
            # Пытаемся получить пользователя по ID
            user = await self.bot.fetch_user(user_id_int)
            # Пытаемся разбанить
            await inter.guild.unban(user, reason=причина)

            # Ответ в чат
            embed = discord.Embed(title="✅ Участник разбанен", description=f"{user.mention} был успешно разбанен.",
                                  color=discord.Color.green())
            await inter.response.send_message(embed=embed)

            # Логирование
            log_embed = discord.Embed(title="✅ Разбан", color=discord.Color.green(), timestamp=datetime.datetime.now())
            log_embed.add_field(name="Участник", value=f"{user.mention} (`{user.id}`)", inline=False)
            log_embed.add_field(name="Модератор", value=f"{inter.user.mention} (`{inter.user.id}`)", inline=False)
            log_embed.add_field(name="Причина", value=причина, inline=False)
            await self._send_log(log_embed)

        except discord.NotFound:
            # Если пользователь с таким ID не найден в бане
            embed = discord.Embed(title="❌ Ошибка",
                                  description=f"Пользователь с ID `{user_id_int}` не найден в списке забаненных.",
                                  color=discord.Color.red())
            await inter.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            # Другие возможные ошибки
            embed = discord.Embed(title="❌ Произошла ошибка", description=f"Не удалось разбанить пользователя. {e}",
                                  color=discord.Color.red())
            await inter.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="мьют", description="🔇 Выдать мьют (тайм-аут) участнику")
    @app_commands.describe(время="Например: 10s, 5m, 3h, 7d", причина="Причина тайм-аута")
    @app_commands.checks.has_any_role(*JR_MODERATOR_ROLES)
    async def mute_cmd(self, inter: discord.Interaction, участник: discord.Member, время: str, причина: str):
        match = re.match(r"(\d+)\s*([smhd])", время.lower())
        if not match:
            embed = discord.Embed(title="❌ Ошибка формата",
                                  description="Неверный формат времени. Используйте `s`, `m`, `h`, `d`.\n**Пример:** `10m`, `2h`, `7d`",
                                  color=discord.Color.red())
            await inter.response.send_message(embed=embed, ephemeral=True)
            return

        value, unit = int(match.group(1)), match.group(2)
        duration = None
        if unit == 's':
            duration = datetime.timedelta(seconds=value)
        elif unit == 'm':
            duration = datetime.timedelta(minutes=value)
        elif unit == 'h':
            duration = datetime.timedelta(hours=value)
        elif unit == 'd':
            duration = datetime.timedelta(days=value)

        if duration > datetime.timedelta(days=28):
            embed = discord.Embed(title="❌ Ошибка длительности", description="Тайм-аут не может превышать **28 дней**.",
                                  color=discord.Color.red())
            await inter.response.send_message(embed=embed, ephemeral=True)
            return

        await участник.timeout(duration, reason=причина)
        embed = discord.Embed(title="🔇 Участнику выдан мьют",
                              description=f"{участник.mention} получил тайм-аут на **{время}**.\n**Причина:** {причина}",
                              color=0x6E6E6E)
        await inter.response.send_message(embed=embed)

        # Логирование
        log_embed = discord.Embed(title="🔇 Мьют", color=0x6E6E6E, timestamp=datetime.datetime.now())
        log_embed.add_field(name="Участник", value=f"{участник.mention} (`{участник.id}`)", inline=False)
        log_embed.add_field(name="Модератор", value=f"{inter.user.mention} (`{inter.user.id}`)", inline=False)
        log_embed.add_field(name="Длительность", value=время, inline=False)
        log_embed.add_field(name="Причина", value=причина, inline=False)
        await self._send_log(log_embed)

    @app_commands.command(name="размьют", description="🔊 Снять мьют (тайм-аут) с участника")
    @app_commands.checks.has_any_role(*JR_MODERATOR_ROLES)
    async def unmute_cmd(self, inter: discord.Interaction, участник: discord.Member):
        await участник.timeout(None)
        embed = discord.Embed(title="🔊 С участника снят мьют", description=f"С {участник.mention} был снят тайм-аут.",
                              color=0x99B873)
        await inter.response.send_message(embed=embed)

        # Логирование
        log_embed = discord.Embed(title="🔊 Размьют", color=0x99B873, timestamp=datetime.datetime.now())
        log_embed.add_field(name="Участник", value=f"{участник.mention} (`{участник.id}`)", inline=False)
        log_embed.add_field(name="Модератор", value=f"{inter.user.mention} (`{inter.user.id}`)", inline=False)
        await self._send_log(log_embed)

    @app_commands.command(name="очистить", description="🧹 Очистить сообщения в чате")
    @app_commands.describe(количество="Сколько сообщений удалить (макс. 100)")
    @app_commands.checks.has_any_role(*JR_MODERATOR_ROLES)
    async def clear_cmd(self, inter: discord.Interaction, количество: app_commands.Range[int, 1, 100]):
        await inter.response.defer(ephemeral=True)
        deleted = await inter.channel.purge(limit=количество)
        embed = discord.Embed(description=f"🧹 Удалено **{len(deleted)}** сообщений.", color=discord.Color.blurple())
        await inter.followup.send(embed=embed)

        # Логирование
        log_embed = discord.Embed(title="🧹 Очистка сообщений", color=discord.Color.blurple(),
                                  timestamp=datetime.datetime.now())
        log_embed.add_field(name="Канал", value=inter.channel.mention, inline=False)
        log_embed.add_field(name="Модератор", value=f"{inter.user.mention} (`{inter.user.id}`)", inline=False)
        log_embed.add_field(name="Количество", value=f"{len(deleted)}", inline=False)
        await self._send_log(log_embed)


async def setup(bot):
    await bot.add_cog(Moderation(bot))