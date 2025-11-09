import logging
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View, TextInput
import random

# --- НАСТРОЙКИ ---
MEMBER_ROLE_ID = 1405996768876822539  # ID роли, которую бот выдаёт после проверки

logger = logging.getLogger(__name__)


class VerificationModal(discord.ui.Modal):
    def __init__(self, correct_number: int):
        super().__init__(title="Проверка")
        self.correct_number = correct_number

        self.code_input = TextInput(
            label="Введите 4-значный код",
            placeholder=f"Например: {self.correct_number}",
            style=discord.TextStyle.short,
            min_length=4,
            max_length=4,
            required=True,
        )
        self.add_item(self.code_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_input = self.code_input.value.strip()

            if not user_input.isdigit():
                await interaction.response.send_message("❌ Код должен состоять только из цифр.", ephemeral=True)
                return

            if int(user_input) == self.correct_number:
                role = interaction.guild.get_role(MEMBER_ROLE_ID)
                if role:
                    await interaction.user.add_roles(role)
                    await interaction.response.send_message("✅ Проверка пройдена! Роль выдана.", ephemeral=True)
                    logger.info(f"{interaction.user} успешно прошёл проверку.")
                else:
                    await interaction.response.send_message(
                        "⚠️ Роль для проверки не найдена. Обратитесь к администратору.", ephemeral=True
                    )
                    logger.error(f"Роль с ID {MEMBER_ROLE_ID} не найдена.")
            else:
                await interaction.response.send_message("❌ Неверный код. Попробуйте ещё раз.", ephemeral=True)
                logger.warning(f"{interaction.user} ввёл неверный код: {user_input}")

        except Exception as e:
            logger.error(f"Ошибка в модалке проверки: {e}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message("⚡ Произошла ошибка. Попробуйте позже.", ephemeral=True)


class VerifyView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Пройти проверку", style=discord.ButtonStyle.gray, emoji="✅", custom_id="verify_button")
    async def verify_button(self, interaction: discord.Interaction, button: Button):
        try:
            role = interaction.guild.get_role(MEMBER_ROLE_ID)
            if not role:
                logger.error(f"Роль с ID {MEMBER_ROLE_ID} не найдена.")
                await interaction.response.send_message("⚠️ Ошибка. Роль не найдена.", ephemeral=True)
                return

            if role in interaction.user.roles:
                await interaction.response.send_message("ℹ️ Вы уже прошли проверку.", ephemeral=True)
                return

            correct_number = random.randint(1000, 9999)
            modal = VerificationModal(correct_number)
            await interaction.response.send_modal(modal)

        except Exception as e:
            logger.error(f"Ошибка при попытке проверки: {e}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message("⚡ Ошибка. Попробуйте позже.", ephemeral=True)


class Verify(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.add_view(VerifyView())

    @app_commands.command(name="отправить-проверку", description="Отправить сообщение с кнопкой проверки.")
    @app_commands.default_permissions(administrator=True)
    async def send_verify_message(self, inter: discord.Interaction):
        await inter.response.defer(ephemeral=True)

        embed = discord.Embed(
            description="Чтобы получить доступ к серверу, нажмите кнопку ниже и введите проверочный код.",
            color=0x2b2d31
        )
        embed.set_footer(text="Если что-то не работает — обратитесь к администратору.")

        try:
            file = discord.File("images/verify.png", filename="verify.png")
            embed.set_image(url="attachment://verify.png")
            await inter.channel.send(embed=embed, view=VerifyView(), file=file)
        except FileNotFoundError:
            logger.warning("⚠️ Файл images/verify.png не найден, отправка без изображения.")
            await inter.channel.send(embed=embed, view=VerifyView())
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения проверки: {e}", exc_info=True)
            await inter.followup.send("❌ Не удалось отправить сообщение проверки.", ephemeral=True)
            return

        await inter.followup.send("✅ Сообщение для проверки успешно отправлено.", ephemeral=True)
        logger.info(f"Сообщение проверки отправлено в {inter.channel.name} пользователем {inter.user}.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Verify(bot))
