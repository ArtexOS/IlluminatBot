import logging
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput
import random

# --- КОНСТАНТЫ ---
MEMBER_ROLE_ID = 1405996768876822539 # ID роли, которую выдавать после верификации

logger = logging.getLogger(__name__)

class VerificationModal(discord.ui.Modal):
    def __init__(self, correct_number: int):
        super().__init__(title="🔮 Тайный код Иллюмината")
        self.correct_number = correct_number

        self.code_input = TextInput(
            label=f"Введите священный код: {self.correct_number}",
            placeholder="✦ 4-значный таинственный код ✦",
            style=discord.TextStyle.short,
            min_length=4,
            max_length=4,
            required=True,
        )
        self.add_item(self.code_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_input = self.code_input.value
            if not user_input.isdigit():
                await interaction.response.send_message("❌ Код должен состоять из цифр.", ephemeral=True)
                return

            if int(user_input) == self.correct_number:
                role = interaction.guild.get_role(MEMBER_ROLE_ID)
                if role:
                    await interaction.user.add_roles(role)
                    await interaction.response.send_message("✨ Вы приняты в Орден Иллюмината! Добро пожаловать.", ephemeral=True)
                    logger.info(f"{interaction.user} успешно прошёл верификацию.")
                else:
                    await interaction.response.send_message("⚠️ Роль таинственного члена не найдена. Свяжитесь с Верховным Светочем.", ephemeral=True)
                    logger.error(f"Роль с ID {MEMBER_ROLE_ID} не найдена при выдаче.")
            else:
                await interaction.response.send_message("❌ Код неверен. Тени не пустят вас внутрь.", ephemeral=True)
                logger.warning(f"{interaction.user} ввёл неверный код: {user_input}")

        except Exception as e:
            logger.error(f"Ошибка в модалке верификации: {e}", exc_info=True)
            await interaction.response.send_message("⚡ Произошла магическая ошибка. Попробуйте ещё раз.", ephemeral=True)


class VerifyView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Начать ритуал верификации", style=discord.ButtonStyle.gray, emoji="🕯️", custom_id="verify_button")
    async def verify_button(self, interaction: discord.Interaction, button: Button):
        try:
            verification_role = interaction.guild.get_role(MEMBER_ROLE_ID)
            if not verification_role:
                logger.error(f"Роль для верификации с ID {MEMBER_ROLE_ID} не найдена!")
                await interaction.response.send_message("⚠️ Ошибка магии. Свяжитесь с Верховным Светочем.", ephemeral=True)
                return

            if verification_role in interaction.user.roles:
                await interaction.response.send_message("🔔 Вы уже инициированы в Орден Иллюмината!", ephemeral=True)
                return

            correct_number = random.randint(1000, 9999)
            modal = VerificationModal(correct_number)
            await interaction.response.send_modal(modal)

        except Exception as e:
            logger.error(f"Ошибка при нажатии кнопки верификации: {e}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message("⚡ Произошла магическая ошибка. Попробуйте позже.", ephemeral=True)


class Verify(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.add_view(VerifyView())

    @app_commands.command(name="отправить-верификацию", description="Отправляет сообщение для верификации в текущий канал.")
    @app_commands.default_permissions(administrator=True)
    async def send_verify_message(self, inter: discord.Interaction):
        embed = discord.Embed(
            description="🔐 Добро пожаловать, путник. Чтобы открыть врата Ордена, необходимо пройти ритуал верификации. Нажмите на свечу ниже, чтобы начать тайный процесс.",
            color=0x393a41
        )
        embed.set_footer(text="Если тени мешают вам пройти ритуал, обратитесь к Верховному Светочу.")

        try:
            file = discord.File("images/verify.png", filename="verification.png")
            embed.set_image(url="attachment://verification.png")
            await inter.channel.send(embed=embed, view=VerifyView(), file=file)
        except FileNotFoundError:
            logger.warning("Файл images/verify.png не найден. Сообщение будет отправлено без изображения.")
            await inter.channel.send(embed=embed, view=VerifyView())

        await inter.response.send_message("✅ Сообщение для верификации отправлено.", ephemeral=True)
        logger.info(f"Сообщение верификации отправлено в канал {inter.channel.name} администратором {inter.user.name}.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Verify(bot))