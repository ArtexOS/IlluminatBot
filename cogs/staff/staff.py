import discord
import json
import os
from discord import app_commands
from discord.ext import commands

CONFIG_FILE = "staff_config.json"


def load_config():
    if not os.path.exists(CONFIG_FILE):
        default_config = {
            "application_channel_id": None,
            "roles": []
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=4, ensure_ascii=False)
        return default_config

    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"application_channel_id": None, "roles": []}


def save_config(config):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Ошибка при сохранении {CONFIG_FILE}: {e}")


class StaffApplicationModal(discord.ui.Modal, title="Заявка на должность"):
    def __init__(self, selected_role: dict):
        super().__init__()
        self.selected_role = selected_role

        self.name_input = discord.ui.TextInput(label="Как вас зовут?", placeholder="Например: Иван", required=True)
        self.age_input = discord.ui.TextInput(label="Сколько вам лет?", placeholder="Например: 18", required=True,
                                              max_length=3)
        self.timezone_input = discord.ui.TextInput(label="Ваш часовой пояс?", placeholder="Например: МСК (UTC+3)",
                                                   required=True)
        self.availability_input = discord.ui.TextInput(label="Сколько времени готовы уделять серверу?",
                                                       style=discord.TextStyle.long,
                                                       placeholder="Например: 2-3 часа в будни, 4-5 часов в выходные.",
                                                       required=True)
        self.trust_input = discord.ui.TextInput(label="Почему мы можем вам доверять?", style=discord.TextStyle.long,
                                                placeholder="Расскажите о своем опыте, сильных сторонах и мотивации.",
                                                required=True)

        self.add_item(self.name_input)
        self.add_item(self.age_input)
        self.add_item(self.timezone_input)
        self.add_item(self.availability_input)
        self.add_item(self.trust_input)

    async def on_submit(self, interaction: discord.Interaction):
        config = load_config()
        channel_id = config.get("application_channel_id")
        if not channel_id:
            return await interaction.response.send_message(
                "⚠️ Канал для заявок не настроен. Обратитесь к администрации.", ephemeral=True)

        channel = interaction.guild.get_channel(channel_id)
        if not channel:
            return await interaction.response.send_message("⚠️ Канал для заявок не найден. Обратитесь к администрации.",
                                                           ephemeral=True)

        embed = discord.Embed(
            title=f"📥 Новая заявка на должность",
            description=f"**Кандидат:** {interaction.user.mention}\n**Претендует на:** {self.selected_role['label']}",
            color=discord.Color.blue()
        )
        embed.set_author(name=interaction.user, icon_url=interaction.user.avatar)
        embed.add_field(name="📝 Имя", value=self.name_input.value, inline=False)
        embed.add_field(name="⏳ Возраст", value=self.age_input.value, inline=False)
        embed.add_field(name="⏰ Часовой пояс", value=self.timezone_input.value, inline=False)
        embed.add_field(name="🕒 Активность", value=self.availability_input.value, inline=False)
        embed.add_field(name="🤝 Доверие", value=self.trust_input.value, inline=False)
        embed.set_footer(text=f"UserID:{interaction.user.id}|RoleValue:{self.selected_role['value']}")

        try:
            await channel.send(embed=embed, view=ApplicationActionsView())
            await interaction.response.send_message("✅ Ваша заявка успешно отправлена! Ожидайте ответа.",
                                                    ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Произошла ошибка при отправке: {e}", ephemeral=True)


class StaffSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        custom_id="staff_persistent_select",
        placeholder="Выберите желаемую должность...",
        min_values=1, max_values=1
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        config = load_config()
        selected_value = select.values[0]

        selected_role_data = next((role for role in config['roles'] if role['value'] == selected_value), None)

        if not selected_role_data:
            return await interaction.response.send_message("❌ Выбранная роль больше не актуальна.", ephemeral=True)

        modal = StaffApplicationModal(selected_role=selected_role_data)
        await interaction.response.send_modal(modal)


class ApplicationActionsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message("⛔ У вас нет прав для выполнения этого действия.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Принять", style=discord.ButtonStyle.green, custom_id="staff_accept_button")
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        original_embed = interaction.message.embeds[0]
        footer_text = original_embed.footer.text

        try:
            user_id = int(footer_text.split('|')[0].replace('UserID:', ''))
            role_value = footer_text.split('|')[1].replace('RoleValue:', '')
        except (IndexError, ValueError):
            return await interaction.response.send_message("❌ Не удалось прочитать данные из заявки.", ephemeral=True)

        member = interaction.guild.get_member(user_id)
        if not member:
            return await interaction.response.send_message("❌ Пользователь не найден на сервере.", ephemeral=True,
                                                           delete_after=10)

        config = load_config()
        role_data = next((r for r in config['roles'] if r['value'] == role_value), None)

        role_to_give = None
        if role_data and role_data.get('role_id'):
            role_to_give = interaction.guild.get_role(role_data['role_id'])

        new_embed = original_embed.copy()
        new_embed.color = discord.Color.green()
        new_embed.title = "✅ Заявка принята"
        new_embed.add_field(name="Решение принял", value=interaction.user.mention, inline=False)

        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(embed=new_embed, view=self)

        dm_message = f"🎉 Поздравляем, **{member.display_name}**! Ваша заявка на сервере **{interaction.guild.name}** была одобрена."
        if role_to_give:
            try:
                await member.add_roles(role_to_give,
                                       reason=f"Принят на должность по заявке. Решение: {interaction.user}")
                dm_message += f"\nВам была выдана роль: **{role_to_give.name}**."
            except discord.Forbidden:
                await interaction.followup.send("⚠️ Не удалось выдать роль. Проверьте права и иерархию ролей бота.",
                                                ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"⚠️ Произошла ошибка при выдаче роли: {e}", ephemeral=True)

        try:
            await member.send(dm_message)
        except discord.Forbidden:
            pass

    @discord.ui.button(label="Отклонить", style=discord.ButtonStyle.red, custom_id="staff_reject_button")
    async def reject_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        original_embed = interaction.message.embeds[0]
        footer_text = original_embed.footer.text

        try:
            user_id = int(footer_text.split('|')[0].replace('UserID:', ''))
        except (IndexError, ValueError):
            return await interaction.response.send_message("❌ Не удалось прочитать данные из заявки.", ephemeral=True)

        member = interaction.guild.get_member(user_id)

        new_embed = original_embed.copy()
        new_embed.color = discord.Color.red()
        new_embed.title = "❌ Заявка отклонена"
        new_embed.add_field(name="Решение принял", value=interaction.user.mention, inline=False)

        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(embed=new_embed, view=self)

        if member:
            try:
                await member.send(
                    f"😔 К сожалению, **{member.display_name}**, ваша заявка на сервере **{interaction.guild.name}** была отклонена.")
            except discord.Forbidden:
                pass


class Staff(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.add_view(StaffSelectView())
        self.bot.add_view(ApplicationActionsView())

    @app_commands.command(name="staff_send_message",
                          description="👑 Отправить сообщение для набора в стафф в указанный канал.")
    @app_commands.describe(канал="Канал, куда будет отправлено сообщение с выбором должности.")
    @app_commands.checks.has_permissions(administrator=True)
    async def staff_send_message(self, interaction: discord.Interaction, канал: discord.TextChannel):
        config = load_config()
        roles = config.get('roles', [])

        if not roles:
            return await interaction.response.send_message(
                "❌ Нет ни одной должности для набора. Сначала добавьте их командой `/add_staff_role`.", ephemeral=True)

        embed = discord.Embed(
            title="Набор в персонал сервера",
            description="Хотите стать частью нашей команды и помогать в развитии сервера? Выберите желаемую должность из списка ниже, чтобы подать заявку.",
            color=discord.Color.gold()
        )
        embed.set_footer(text="Пожалуйста, отвечайте на вопросы честно и развернуто.")

        view = StaffSelectView()
        select_menu = view.children[0]
        select_menu.options = [discord.SelectOption(label=r['label'], value=r['value']) for r in roles]

        try:
            await канал.send(embed=embed, view=view)
            await interaction.response.send_message(f"✅ Сообщение для набора отправлено в {канал.mention}.",
                                                    ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(f"❌ У бота нет прав на отправку сообщений в {канал.mention}.",
                                                    ephemeral=True)

    @app_commands.command(name="set_applications_channel",
                          description="⭐ (Админ) Установить канал для ПРОВЕРКИ заявок в стафф.")
    @app_commands.describe(канал="Текстовый канал, куда будут приходить готовые заявки.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_applications_channel(self, interaction: discord.Interaction, канал: discord.TextChannel):
        config = load_config()
        config['application_channel_id'] = канал.id
        save_config(config)
        await interaction.response.send_message(
            f"✅ Канал {канал.mention} успешно установлен для приема и проверки заявок.",
            ephemeral=True
        )

    @app_commands.command(name="add_staff_role", description="⭐ (Админ) Добавить новую должность для набора.")
    @app_commands.describe(
        название="Название, которое будет в списке (например, 'Модератор').",
        значение="Уникальный ID (латиницей, без пробелов, например 'moderator').",
        роль="Роль Discord, которая будет выдана при принятии (необязательно)."
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def add_staff_role(self, interaction: discord.Interaction, название: str, значение: str,
                             роль: discord.Role = None):
        config = load_config()
        if any(r['value'] == значение for r in config['roles']):
            return await interaction.response.send_message(f"❌ Ошибка: Значение '{значение}' уже используется.",
                                                           ephemeral=True)

        new_role = {"label": название, "value": значение, "role_id": роль.id if роль else None}
        config['roles'].append(new_role)
        save_config(config)
        await interaction.response.send_message(f"✅ Должность '{название}' добавлена.", ephemeral=True)

    @app_commands.command(name="remove_staff_role", description="⭐ (Админ) Удалить должность из списка набора.")
    @app_commands.describe(значение="Уникальный ID должности для удаления.")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_staff_role(self, interaction: discord.Interaction, значение: str):
        config = load_config()
        initial_len = len(config['roles'])
        config['roles'] = [r for r in config['roles'] if r['value'] != значение]

        if len(config['roles']) < initial_len:
            save_config(config)
            await interaction.response.send_message(f"✅ Должность '{значение}' удалена.", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Должность '{значение}' не найдена.", ephemeral=True)

    @remove_staff_role.autocomplete('значение')
    async def remove_staff_role_autocomplete(self, _: discord.Interaction, current: str) -> list[
        app_commands.Choice[str]]:
        config = load_config()
        choices = [
            app_commands.Choice(name=role['label'], value=role['value'])
            for role in config.get('roles', [])
            if current.lower() in role['label'].lower() or current.lower() in role['value'].lower()
        ]
        return choices[:25]


async def setup(bot: commands.Bot):
    await bot.add_cog(Staff(bot))
