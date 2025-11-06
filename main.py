import asyncio
import logging
import os

import discord
from discord.ext import commands

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger('discord').setLevel(logging.ERROR)

class IlluminatBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=".",
            help_command=None,
            intents=discord.Intents.all()
        )

    async def load_cogs(self):
        for folder in os.listdir("./cogs"):
            if os.path.isdir(f"./cogs/{folder}"):
                for file in os.listdir(f"./cogs/{folder}/"):
                    if file.endswith(".py") and not file.startswith("_"):
                        await self.load_extension(f"cogs.{folder}.{file[:-3]}")

    async def setup_hook(self):
        guild_id = int(os.getenv("DISCORD_GUILD"))
        await self.load_cogs()

        if guild_id:
            guild = discord.Object(id=guild_id)
            self.tree.copy_global_to(guild=guild)
        synced = await self.tree.sync()
        logger.info(f"Synced {len(synced)} commands!")

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            await ctx.send(discord.Embed(
                description=f"Команда '{ctx.message.content}' не найдена!",
                color=discord.Color.red()
            ))
        else:
            raise error

async def main():
    bot = IlluminatBot()
    await bot.start(os.getenv("BOT_TOKEN"))

if __name__ == "__main__":
    asyncio.run(main())
