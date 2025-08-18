from discord import app_commands, Embed, Interaction, TextStyle
from discord.ui import Modal, TextInput
from discord.ext import commands


class GenEmbedModal(Modal, title="Генерация Embed"):
    def __init__(self, cog):
        super().__init__(title="Генерация Embed")
        self.cog = cog
        self.title_input = TextInput(label="Заголовок", style=TextStyle.short, required=False)
        self.description_input = TextInput(label="Описание", style=TextStyle.paragraph, required=False)
        self.color_input = TextInput(label="Цвет", style=TextStyle.short, required=False, placeholder="ff0000 (HEX)")
        self.author_input = TextInput(label="Автор", style=TextStyle.short, required=False)
        self.footer_input = TextInput(label="Футер", style=TextStyle.short, required=False)

        self.add_item(self.title_input)
        self.add_item(self.description_input)
        self.add_item(self.color_input)
        self.add_item(self.author_input)
        self.add_item(self.footer_input)

    async def on_submit(self, inter: Interaction):
        color_value = 0x2f3136
        if self.color_input.value:
            try:
                color_value = int(self.color_input.value.strip().replace("#", ""), 16)
            except ValueError:
                await inter.response.send_message("⚠ Некорректный цвет. Используй HEX, например `ff0000`", ephemeral=True)
                return

        embed = Embed(
            title=self.title_input.value or None,
            description=self.description_input.value or None,
            color=color_value
        )

        if self.author_input.value:
            embed.set_author(name=self.author_input.value)
        if self.footer_input.value:
            embed.set_footer(text=self.footer_input.value)

        self.cog.embeds[inter.user.id] = embed
        await inter.response.send_message("✅ Базовый Embed создан! Используй `/gen_embed_extra`, чтобы дополнить его.", ephemeral=True)


class GenEmbedExtraModal(Modal, title="Доп. параметры Embed"):
    def __init__(self, cog):
        super().__init__(title="Доп. параметры Embed")
        self.cog = cog

        self.url_input = TextInput(label="URL (ссылка)", style=TextStyle.short, required=False, placeholder="https://example.com")
        self.thumbnail_input = TextInput(label="Миниатюра (URL)", style=TextStyle.short, required=False)
        self.image_input = TextInput(label="Изображение (URL)", style=TextStyle.short, required=False)
        self.field1_input = TextInput(label="Поле 1 (имя:значение)", style=TextStyle.paragraph, required=False, placeholder="Название: Значение")
        self.field2_input = TextInput(label="Поле 2 (имя:значение)", style=TextStyle.paragraph, required=False, placeholder="Название: Значение")

        self.add_item(self.url_input)
        self.add_item(self.thumbnail_input)
        self.add_item(self.image_input)
        self.add_item(self.field1_input)
        self.add_item(self.field2_input)

    async def on_submit(self, inter: Interaction):
        embed = self.cog.embeds.get(inter.user.id)
        if not embed:
            await inter.response.send_message("⚠ Сначала создай embed с помощью `/gen_embed`!", ephemeral=True)
            return

        if self.url_input.value:
            embed.url = self.url_input.value
        if self.thumbnail_input.value:
            embed.set_thumbnail(url=self.thumbnail_input.value)
        if self.image_input.value:
            embed.set_image(url=self.image_input.value)

        for field in (self.field1_input, self.field2_input):
            if field.value and ":" in field.value:
                name, value = field.value.split(":", 1)
                embed.add_field(name=name.strip(), value=value.strip(), inline=False)

        self.cog.embeds.pop(inter.user.id, None)

        await inter.response.defer(ephemeral=True)
        await inter.channel.send(embed=embed)


class EmbedGeneration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.embeds = {}
    
    @app_commands.command(name="gen_embed", description="Генерация embed-сообщения (основное)")
    async def embed_gen_cmd(self, inter: Interaction):
        await inter.response.send_modal(GenEmbedModal(self))

    @app_commands.command(name="gen_embed_extra", description="Дополнение ранее созданного embed")
    async def embed_gen_extra_cmd(self, inter: Interaction):
        await inter.response.send_modal(GenEmbedExtraModal(self))


async def setup(bot):
    await bot.add_cog(EmbedGeneration(bot))
