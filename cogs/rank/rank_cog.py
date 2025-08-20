# cogs/rank/rank_cog.py
import discord
from discord import app_commands
from discord.ext import commands

from database.rank.functions import RankDatabase
from database.rank.connection import create_rank_tables
from database.rank.models import RankUser

LOG_CHANNEL_ID = 1407738293830942730
ADMIN_ROLE_ID = 1399711308676595785


class RankCog(commands.Cog, name="Ранги"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = RankDatabase()
        self.log_channel = None
        self.no_xp_channels = set()

    async def cog_load(self):
        await create_rank_tables()
        self.log_channel = self.bot.get_channel(LOG_CHANNEL_ID)
        self.no_xp_channels = await self.db.get_no_xp_channels()

    async def send_log(self, embed: discord.Embed):
        if self.log_channel:
            await self.log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.channel.id in self.no_xp_channels:
            return

        user, leveled_up = await self.db.update_user_xp(message.author.id, 10)

        if leveled_up:
            embed = discord.Embed(
                description=f"🎉 **Поздравляем, {message.author.mention}!**\nВы достигли **{user.level}** уровня!",
                color=discord.Color.green()
            )
            await message.channel.send(embed=embed)

            log_embed = discord.Embed(
                title="📝 Лог: Повышение уровня",
                color=0x00aaff,
                description=f"Пользователь {message.author.mention} достиг **{user.level}** уровня."
            )
            log_embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
            await self.send_log(log_embed)

    @app_commands.command(name="уровень", description="🏅 Показывает ваш текущий уровень и опыт.")
    @app_commands.describe(user="Пользователь, чей уровень вы хотите посмотреть (необязательно)")
    async def level(self, inter: discord.Interaction, user: discord.Member = None):
        target_user = user or inter.user
        db_user = await self.db.get_user(target_user.id)

        if not db_user:
            db_user = RankUser(user_id=target_user.id, level=0, xp=0)

        xp_needed = (db_user.level + 1) * 100

        embed = discord.Embed(
            title=f"🏅 Ранг {target_user.display_name}",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=target_user.display_avatar.url)
        embed.add_field(name="Уровень", value=f"**{db_user.level}**", inline=True)
        embed.add_field(name="Опыт", value=f"**{db_user.xp} / {xp_needed}**", inline=True)
        await inter.response.send_message(embed=embed)

    @app_commands.command(name="ранг_топ", description="🏆 Показывает топ-10 пользователей по уровню.")
    async def rank_top(self, inter: discord.Interaction):
        top_users_db = await self.db.get_top_users(10)
        embed = discord.Embed(
            title="🏆 Таблица лидеров",
            description="Топ-10 пользователей сервера по уровню и опыту.",
            color=discord.Color.blurple()
        )

        lines = []
        for i, user_db in enumerate(top_users_db):
            user = self.bot.get_user(user_db.user_id)
            username = user.display_name if user else f"ID: {user_db.user_id}"
            lines.append(f"`{i + 1}.` **{username}** — Уровень **{user_db.level}** (`{user_db.xp} XP`)")

        embed.description = "\n".join(lines) if lines else "Пока что здесь пусто..."
        await inter.response.send_message(embed=embed)

    @app_commands.command(name="установить_уровень", description="👑 (Админ) Устанавливает уровень пользователю.")
    @app_commands.checks.has_role(ADMIN_ROLE_ID)
    @app_commands.describe(пользователь="Пользователь, которому нужно изменить уровень.", уровень="Новый уровень.")
    async def set_level(self, inter: discord.Interaction, пользователь: discord.Member,
                        уровень: app_commands.Range[int, 0]):
        await self.db.set_user_rank(пользователь.id, level=уровень)
        embed = discord.Embed(description=f"✅ Уровень для {пользователь.mention} установлен на **{уровень}**.",
                              color=discord.Color.green())
        await inter.response.send_message(embed=embed, ephemeral=True)

        log_embed = discord.Embed(title="📝 Лог: Админ | Установка уровня", color=0xffa500)
        log_embed.add_field(name="Администратор", value=inter.user.mention)
        log_embed.add_field(name="Пользователь", value=пользователь.mention)
        log_embed.add_field(name="Новый уровень", value=str(уровень))
        await self.send_log(log_embed)

    @app_commands.command(name="установить_опыт", description="👑 (Админ) Устанавливает опыт пользователю.")
    @app_commands.checks.has_role(ADMIN_ROLE_ID)
    @app_commands.describe(пользователь="Пользователь, которому нужно изменить опыт.", опыт="Новое количество опыта.")
    async def set_xp(self, inter: discord.Interaction, пользователь: discord.Member, опыт: app_commands.Range[int, 0]):
        await self.db.set_user_rank(пользователь.id, xp=опыт)
        embed = discord.Embed(description=f"✅ Опыт для {пользователь.mention} установлен на **{опыт}**.",
                              color=discord.Color.green())
        await inter.response.send_message(embed=embed, ephemeral=True)

        log_embed = discord.Embed(title="📝 Лог: Админ | Установка опыта", color=0xffa500)
        log_embed.add_field(name="Администратор", value=inter.user.mention)
        log_embed.add_field(name="Пользователь", value=пользователь.mention)
        log_embed.add_field(name="Новый опыт", value=str(опыт))
        await self.send_log(log_embed)

    @app_commands.command(name="запретить_опыт", description="👑 (Админ) Запрещает получение опыта в канале.")
    @app_commands.checks.has_role(ADMIN_ROLE_ID)
    @app_commands.describe(канал="Канал, в котором нужно запретить опыт.")
    async def disable_xp(self, inter: discord.Interaction, канал: discord.TextChannel):
        success = await self.db.add_no_xp_channel(канал.id)
        if success:
            self.no_xp_channels.add(канал.id)
            embed = discord.Embed(description=f"✅ Опыт в канале {канал.mention} **запрещён**.",
                                  color=discord.Color.green())
            await inter.response.send_message(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(description=f"⚠️ Опыт в канале {канал.mention} уже был запрещён.", color=0xffa500)
            await inter.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="разрешить_опыт", description="👑 (Админ) Разрешает получение опыта в канале.")
    @app_commands.checks.has_role(ADMIN_ROLE_ID)
    @app_commands.describe(канал="Канал, в котором нужно разрешить опыт.")
    async def enable_xp(self, inter: discord.Interaction, канал: discord.TextChannel):
        success = await self.db.remove_no_xp_channel(канал.id)
        if success:
            if канал.id in self.no_xp_channels:
                self.no_xp_channels.remove(канал.id)
            embed = discord.Embed(description=f"✅ Опыт в канале {канал.mention} снова **разрешён**.",
                                  color=discord.Color.green())
            await inter.response.send_message(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(description=f"⚠️ Опыт в канале {канал.mention} не был запрещён.", color=0xffa500)
            await inter.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(RankCog(bot))