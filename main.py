import discord
from discord.ext import commands
import os
import logging
from config import TOKEN, PREFIX
import asyncio

# Configuration des logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("discord_bot")

# Configuration des intentions (Intents)
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

# Initialisation du bot
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# Chargement des extensions (cogs)
async def load_extensions():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            await bot.load_extension(f'cogs.{filename[:-3]}')
            logger.info(f"Loaded extension: {filename[:-3]}")

@bot.event
async def on_ready():
    logger.info(f'Bot connecté en tant que {bot.user.name}')
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching, name=f"{PREFIX}help | Surveillance du serveur"
    ))
    
    # Synchroniser les commandes slash
    logger.info("Synchronisation des commandes slash...")
    await bot.tree.sync()
    logger.info("Synchronisation terminée")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Argument manquant : {error.param}")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("Vous n'avez pas les permissions nécessaires.")
    else:
        logger.error(f"Erreur: {error}")
        await ctx.send(f"Une erreur s'est produite : {error}")

async def main():
    await load_extensions()
    await bot.start(TOKEN)

# Point d'entrée
if __name__ == "__main__":
    asyncio.run(main())
