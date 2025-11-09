import datetime
import re
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from database.warn.functions import Database
from database.warn.connection import create_tables

# ---------- Константы ----------

LOG_CHANNEL_ID = 1400850936640831630
OWNER_ROLES = [1405996238519926984]
ADMIN_ROLES = OWNER_ROLES + [1405996476487696566, 1405996543592497333]
HEAD_MODERATOR_ROLES = ADMIN_ROLES + [1407064998932516874]
MODERATOR_ROLES = HEAD_MODERATOR_ROLES + [1405996596474417323]
JR_MODERATOR_ROLES = MODERATOR_ROLES + [1407064791914119219]
TRAINEE_ROLES = JR_MODERATOR_ROLES + [1407063984921645117]
ALERT_CHANNEL_ID = 1437102750033776800


# ---------- Класс Moderation ----------

class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = Database()
        self.log_channel: Optional[discord.TextChannel] = None
        self.alert_channel: Optional[discord.TextChannel] = None
        self.allowed_mentions = discord.AllowedMentions(users=True, roles=False, everyone=False)

    # ---------- Вспомогательные функции ----------

    async def _resolve_channel(self, channel_id: int) -> Optional[discord.TextChannel]:
        ch = self.bot.get_channel(channel_id)
        if ch is None:
            try:
                ch = await self.bot.fetch_channel(channel_id)  # type: ignore
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                return None
        return ch if isinstance(ch, discord.TextChannel) else None

    async def _send_log(self, embed: discord.Embed):
        if not self.log_channel:
            return
        try:
            await self.log_channel.send(embed=embed)
        except (discord.Forbidden, discord.HTTPException) as e:
            print(f"⚠️ Не удалось отправить лог: {e}")

    async def _send_public_alert(self, text: str):
        if not self.alert_channel:
            self.alert_channel = await self._resolve_channel(ALERT_CHANNEL_ID)
        if not self.alert_channel:
            print(f"⚠️ Канал с ID {ALERT_CHANNEL_ID} не найден.")
            return
        try:
            await self.alert_channel.send(text, allowed_mentions=self.allowed_mentions)
        except discord.Forbidden:
            print(f"⚠️ Нет прав для отправки сообщений в канал {ALERT_CHANNEL_ID}.")
        except discord.HTTPException as e:
            print(f"⚠️ Ошибка при отправке публичного оповещения: {e}")

    @commands.Cog.listener()
    async def on_ready(self):
        await create_tables()
        self.log_channel = await self._resolve_channel(LOG_CHANNEL_ID)
        self.alert_channel = await self._resolve_channel(ALERT_CHANNEL_ID)
        print("Moderation Cog is Ready ✅")

    def _parse_duration(self, raw: str) -> Optional[datetime.timedelta]:
        m = re.fullmatch(r"(\d+)\s*([smhdSMHD])", raw.strip())
        if not m:
            return None
        val = int(m.group(1))
        unit = m.group(2).lower()
        return {
            "s": datetime.timedelta(seconds=val),
            "m": datetime.timedelta(minutes=val),
            "h": datetime.timedelta(hours=val),
            "d": datetime.timedelta(days=val)
        }.get(unit)

    def _can_act_on(self, inter: discord.Interaction, target: discord.Member) -> Optional[str]:
        me = inter.guild.me if inter.guild else None  # type: ignore
        if not inter.guild or not me:
            return "Команда доступна только на сервере."
        if target == inter.user:
            return "Нельзя применить действие к самому себе."
        if target == me:
            return "Нельзя применить действие к боту."
        if inter.user.id == inter.guild.owner_id:
            return None
        if target.top_role >= inter.user.top_role:
            return "У участника равная или более высокая роль."
        if target.top_role >= me.top_role:
            return "У участника роль выше роли бота."
        return None

    # ---------- Команды ----------

    @app_commands.command(name="пред", description="✔️ Выдать предупреждение участнику")
    @app_commands.checks.has_any_role(*TRAINEE_ROLES)
    async def warn_cmd(self, inter: discord.Interaction, участник: discord.Member, причина: str):
        if участник.bot or участник == inter.user:
            await inter.response.send_message(
                embed=discord.Embed(description="❌ Нельзя выдать предупреждение боту или самому себе.", color=discord.Color.red()),
                ephemeral=True
            )
            return

        # ✅ фикс offset-naive / offset-aware
        now = datetime.datetime.now()
        if now.tzinfo is not None:
            now = now.replace(tzinfo=None)

        await self.db.add_warn(
            user_id=участник.id,
            moderator_id=inter.user.id,
            reason=причина,
            start_time=now
        )

        embed = discord.Embed(
            title="✅ Предупреждение выдано",
            description=f"Модератор {inter.user.mention} выдал предупреждение {участник.mention}\n**Причина:** {причина}",
            color=discord.Color.orange()
        )
        await inter.response.send_message(embed=embed)
        await self._send_public_alert(f"⚠️ {участник.mention} получил предупреждение. Причина: {причина}")

        log_embed = discord.Embed(
            title="📜 Выдано предупреждение",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )
        log_embed.add_field(name="Участник", value=f"{участник.mention} (`{участник.id}`)")
        log_embed.add_field(name="Модератор", value=f"{inter.user.mention} (`{inter.user.id}`)")
        log_embed.add_field(name="Причина", value=причина)
        await self._send_log(log_embed)

        try:
            dm_embed = discord.Embed(
                title=f"Вы получили предупреждение на сервере {inter.guild.name}",
                color=0xFF8C00
            )
            dm_embed.add_field(name="Причина", value=причина)
            dm_embed.set_footer(text=f"Наказание выдал: {inter.user.display_name}")
            await участник.send(embed=dm_embed)
        except (discord.Forbidden, discord.HTTPException):
            pass

    @app_commands.command(name="преды", description="📜 Посмотреть предупреждения участника")
    @app_commands.checks.has_any_role(*TRAINEE_ROLES)
    async def warns_cmd(self, inter: discord.Interaction, участник: Optional[discord.Member] = None):
        target_user = участник or inter.user
        await inter.response.defer(ephemeral=True)
        warns = await self.db.get_warns(user_id=target_user.id)
        if not warns:
            await inter.followup.send(
                embed=discord.Embed(description=f"✨ У {target_user.mention} нет предупреждений.", color=discord.Color.green())
            )
            return

        embed = discord.Embed(
            title=f"⚠️ Предупреждения {target_user.display_name} ({len(warns)} шт.)",
            color=discord.Color.gold()
        )

        parts = []
        for w in warns:
            issued = discord.utils.format_dt(w.start_time, 'R') if isinstance(w.start_time, datetime.datetime) else str(w.start_time)
            parts.append(
                f"### 🆔 **ID:** `{w.id}`\n"
                f"**Выдан:** {issued}\n"
                f"👮 **Модератор:** <@{w.moderator_id}>\n"
                f"💬 **Причина:** {w.reason}"
            )
        embed.description = "\n\n".join(parts)
        await inter.followup.send(embed=embed)

    @app_commands.command(name="снятьпред", description="🗑️ Снять предупреждение по ID")
    @app_commands.checks.has_any_role(*MODERATOR_ROLES)
    async def unwarn_cmd(self, inter: discord.Interaction, id: int):
        await self.db.remove_warn_by_id(warn_id=id)
        await inter.response.send_message(
            embed=discord.Embed(description=f"✅ Предупреждение с ID `{id}` было успешно удалено.", color=discord.Color.green()),
            ephemeral=True
        )
        await self._send_public_alert(f"🗑️ Предупреждение с ID `{id}` снято модератором {inter.user.mention}.")
        log_embed = discord.Embed(title="🗑️ Снято предупреждение", color=0x99B873, timestamp=discord.utils.utcnow())
        log_embed.add_field(name="ID Предупреждения", value=f"`{id}`")
        log_embed.add_field(name="Модератор", value=f"{inter.user.mention} (`{inter.user.id}`)")
        await self._send_log(log_embed)

    @app_commands.command(name="сброспред", description="🗑️🗑️ Снять все предупреждения с участника")
    @app_commands.checks.has_any_role(*HEAD_MODERATOR_ROLES)
    async def clearwarns_cmd(self, inter: discord.Interaction, участник: discord.Member):
        await self.db.remove_all_warns(user_id=участник.id)
        await inter.response.send_message(
            embed=discord.Embed(description=f"✅ Все предупреждения для {участник.mention} были сняты.", color=discord.Color.green())
        )
        log_embed = discord.Embed(title="🗑️🗑️ Сняты все предупреждения", color=0x99B873, timestamp=discord.utils.utcnow())
        log_embed.add_field(name="Участник", value=f"{участник.mention} (`{участник.id}`)")
        log_embed.add_field(name="Модератор", value=f"{inter.user.mention} (`{inter.user.id}`)")
        await self._send_log(log_embed)


# ---------- Регистрация ----------

async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
