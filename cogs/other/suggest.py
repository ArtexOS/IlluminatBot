import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
import datetime
from typing import Optional, Dict


class Suggestion:
    def __init__(self, author_id: int, message_id: int, channel_id: int, text: str):
        self.author_id = author_id
        self.message_id = message_id
        self.channel_id = channel_id
        self.text = text
        self.status = "pending"
        self.upvotes = set()
        self.downvotes = set()

    def count_upvotes(self) -> int:
        return len(self.upvotes)

    def count_downvotes(self) -> int:
        return len(self.downvotes)


class SuggestModal(Modal, title="💡 Новое предложение"):
    def __init__(self, cog: "SuggestCog"):
        super().__init__(timeout=120)
        self.cog = cog
        self.idea_input = TextInput(
            label="Опиши свою идею",
            placeholder="Напиши предложение, идею или улучшение для сервера...",
            max_length=2000,
            style=discord.TextStyle.paragraph,
            required=True
        )
        self.add_item(self.idea_input)

    async def on_submit(self, interaction: discord.Interaction):
        if not self.cog.suggest_channel_id:
            await interaction.response.send_message("⚠️ Канал для предложений не установлен.", ephemeral=True)
            return

        channel = interaction.guild.get_channel(self.cog.suggest_channel_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("⚠️ Канал для предложений не найден.", ephemeral=True)
            return

        idea_text = self.idea_input.value.strip()
        embed = discord.Embed(
            title="💡 Новое предложение",
            description=idea_text,
            color=discord.Color.blurple(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="👍 За", value="0", inline=True)
        embed.add_field(name="👎 Против", value="0", inline=True)
        embed.set_footer(text="Статус: На рассмотрении")

        view = SuggestVoteView(self.cog)
        message = await channel.send(embed=embed, view=view)

        # Сохраняем в память
        suggestion = Suggestion(interaction.user.id, message.id, channel.id, idea_text)
        self.cog.suggestions[message.id] = suggestion

        await interaction.response.send_message("✅ Твоя идея отправлена!", ephemeral=True)


class SuggestVoteView(View):
    def __init__(self, cog: "SuggestCog"):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="0", emoji="👍", style=discord.ButtonStyle.green, custom_id="suggest_upvote")
    async def upvote(self, interaction: discord.Interaction, button: Button):
        s = self.cog.suggestions.get(interaction.message.id)
        if not s:
            await interaction.response.send_message("⚠️ Ошибка: предложение не найдено.", ephemeral=True)
            return

        user_id = interaction.user.id
        if user_id in s.downvotes:
            s.downvotes.remove(user_id)
        if user_id in s.upvotes:
            s.upvotes.remove(user_id)
        else:
            s.upvotes.add(user_id)

        await self.update_message(interaction, s)

    @discord.ui.button(label="0", emoji="👎", style=discord.ButtonStyle.red, custom_id="suggest_downvote")
    async def downvote(self, interaction: discord.Interaction, button: Button):
        s = self.cog.suggestions.get(interaction.message.id)
        if not s:
            await interaction.response.send_message("⚠️ Ошибка: предложение не найдено.", ephemeral=True)
            return

        user_id = interaction.user.id
        if user_id in s.upvotes:
            s.upvotes.remove(user_id)
        if user_id in s.downvotes:
            s.downvotes.remove(user_id)
        else:
            s.downvotes.add(user_id)

        await self.update_message(interaction, s)

    async def update_message(self, interaction: discord.Interaction, s: Suggestion):
        upvotes, downvotes = s.count_upvotes(), s.count_downvotes()
        embed = interaction.message.embeds[0]
        embed.set_field_at(0, name="👍 За", value=str(upvotes), inline=True)
        embed.set_field_at(1, name="👎 Против", value=str(downvotes), inline=True)

        embed.color = discord.Color.green() if upvotes > downvotes else discord.Color.red() if downvotes > upvotes else discord.Color.blurple()

        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.defer()


class SuggestCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.suggest_channel_id: Optional[int] = None
        self.suggestions: Dict[int, Suggestion] = {}  # message_id -> Suggestion
        self.bot.add_view(SuggestVoteView(self))

    # ---------- Команды ----------

    @app_commands.command(name="предложить", description="💡 Отправить идею или предложение для сервера.")
    async def suggest(self, inter: discord.Interaction):
        modal = SuggestModal(self)
        await inter.response.send_modal(modal)

    @app_commands.command(name="канал-предложений", description="📩 Установить канал для идей.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_channel(self, inter: discord.Interaction, канал: discord.TextChannel):
        self.suggest_channel_id = канал.id
        await inter.response.send_message(f"✅ Канал для предложений установлен: {канал.mention}", ephemeral=True)

    @app_commands.command(name="принять-идею", description="✅ Принять идею по ID сообщения.")
    @app_commands.checks.has_permissions(administrator=True)
    async def accept(self, inter: discord.Interaction, message_id: str):
        msg_id = int(message_id)
        s = self.suggestions.get(msg_id)
        if not s:
            await inter.response.send_message("❌ Идея не найдена.", ephemeral=True)
            return

        channel = self.bot.get_channel(s.channel_id)
        if not channel:
            await inter.response.send_message("⚠️ Канал не найден.", ephemeral=True)
            return

        try:
            message = await channel.fetch_message(s.message_id)
            embed = message.embeds[0]
            embed.color = discord.Color.green()
            embed.set_footer(text="Статус: ✅ Принята")
            await message.edit(embed=embed)
            s.status = "accepted"
            await inter.response.send_message(f"✅ Идея {s.message_id} принята!", ephemeral=True)
        except Exception as e:
            await inter.response.send_message(f"⚠️ Ошибка при изменении идеи: {e}", ephemeral=True)

    @app_commands.command(name="отклонить-идею", description="❌ Отклонить идею по ID сообщения.")
    @app_commands.checks.has_permissions(administrator=True)
    async def reject(self, inter: discord.Interaction, message_id: str):
        msg_id = int(message_id)
        s = self.suggestions.get(msg_id)
        if not s:
            await inter.response.send_message("❌ Идея не найдена.", ephemeral=True)
            return

        channel = self.bot.get_channel(s.channel_id)
        if not channel:
            await inter.response.send_message("⚠️ Канал не найден.", ephemeral=True)
            return

        try:
            message = await channel.fetch_message(s.message_id)
            embed = message.embeds[0]
            embed.color = discord.Color.red()
            embed.set_footer(text="Статус: ❌ Отклонена")
            await message.edit(embed=embed)
            s.status = "rejected"
            await inter.response.send_message(f"❌ Идея {s.message_id} отклонена.", ephemeral=True)
        except Exception as e:
            await inter.response.send_message(f"⚠️ Ошибка при изменении идеи: {e}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(SuggestCog(bot))
