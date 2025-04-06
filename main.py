import discord
from discord.ext import commands
import os
import logging
import sys
from dotenv import load_dotenv
import asyncio
import datetime

# Charger les variables d'environnement
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
PREFIX = os.getenv('COMMAND_PREFIX', '!')
VERSION = os.getenv('VERSION', '1.0.0')

# Vérifier la présence du fichier .env et des informations essentielles
if not os.path.exists('.env'):
    print("\n⚠️  ERREUR: Fichier .env manquant! Veuillez le créer en suivant le modèle fourni.")
    sys.exit(1)

if not TOKEN:
    print("\n⚠️  ERREUR: Token Discord manquant dans le fichier .env!")
    sys.exit(1)

# Créer les dossiers nécessaires
os.makedirs('data', exist_ok=True)
os.makedirs('logs', exist_ok=True)
os.makedirs('backups', exist_ok=True)

# Configuration des logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs/bot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("discord_bot")

# Configuration des intentions (Intents)
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
try:
    intents.presences = True
    logger.info("Intention 'presences' activée")
except Exception as e:
    logger.warning(f"Impossible d'activer l'intention 'presences': {e}")

# Initialisation du bot
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)
bot.version = VERSION

# Définir les propriétaires du bot
owner_ids_str = os.getenv('OWNER_IDS', '')
bot.owner_ids = set(map(int, owner_ids_str.split(','))) if owner_ids_str else set()
logger.info(f"Propriétaires du bot configurés: {bot.owner_ids}")

# Initialisation de la base de données
try:
    from utils.db_handler import DatabaseHandler
    db = DatabaseHandler()
    db.setup_database()
    db.close()
    logger.info("Base de données initialisée avec succès")
except Exception as e:
    logger.error(f"Erreur lors de l'initialisation de la base de données: {e}")

# Chargement des extensions (cogs)
async def load_extensions():
    """Charge tous les modules depuis le dossier cogs"""
    cog_count = 0
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            cog_name = f'cogs.{filename[:-3]}'
            try:
                await bot.load_extension(cog_name)
                logger.info(f"Module chargé: {cog_name}")
                cog_count += 1
            except Exception as e:
                logger.error(f"Erreur lors du chargement de {cog_name}: {e}")
    
    logger.info(f"Total: {cog_count} modules chargés")
    return cog_count

@bot.event
async def on_ready():
    """Événement déclenché lorsque le bot est prêt"""
    logger.info(f'Bot connecté en tant que {bot.user.name} (ID: {bot.user.id})')
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching, name=f"{PREFIX}help | Surveillance du serveur"
    ))
    
    # Synchroniser les commandes slash
    logger.info("Synchronisation des commandes slash...")
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synchronisation terminée ({len(synced)} commandes)")
    except Exception as e:
        logger.error(f"Erreur lors de la synchronisation des commandes: {e}")

@bot.event
async def on_connect():
    """Événement déclenché lorsque le bot se connecte à Discord"""
    logger.info(f"Bot connecté à Discord (version {VERSION})")

@bot.event
async def on_disconnect():
    """Événement déclenché lorsque le bot se déconnecte de Discord"""
    logger.warning("Bot déconnecté de Discord")

@bot.event
async def on_command_error(ctx, error):
    """Gestion globale des erreurs de commandes"""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"⚠️ Argument manquant : `{error.param.name}`")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"⚠️ Argument invalide : {error}")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("⚠️ Vous n'avez pas les permissions nécessaires pour exécuter cette commande.")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send(f"⚠️ Je n'ai pas les permissions nécessaires: {', '.join(error.missing_permissions)}")
    elif isinstance(error, commands.NotOwner):
        await ctx.send("⚠️ Cette commande est réservée aux propriétaires du bot.")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⚠️ Cette commande est en cooldown. Réessayez dans {error.retry_after:.1f} secondes.")
    else:
        logger.error(f"Erreur non gérée: {error}")
        await ctx.send(f"❌ Une erreur s'est produite: `{error}`")

async def main():
    """Fonction principale"""
    logger.info(f"Démarrage du bot (version {VERSION})...")
    
    # Chargement des modules
    cog_count = await load_extensions()
    if cog_count == 0:
        logger.critical("Aucun module n'a été chargé. Le bot ne peut pas démarrer correctement.")
    
    # Connexion à Discord
    try:
        await bot.start(TOKEN)
    except discord.errors.LoginFailure:
        logger.critical("Token invalide. Vérifiez votre fichier .env")
    except Exception as e:
        logger.critical(f"Erreur lors du démarrage du bot: {e}")

# Point d'entrée
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Arrêt du bot (interruption clavier)")
    except Exception as e:
        logger.critical(f"Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
