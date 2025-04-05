import os
from dotenv import load_dotenv

load_dotenv()

# Configuration principale
TOKEN = os.getenv('DISCORD_TOKEN')
PREFIX = os.getenv('COMMAND_PREFIX', '!')

# IDs des serveurs
MAIN_SERVER_ID = int(os.getenv('MAIN_SERVER_ID'))
MODERATION_SERVER_ID = int(os.getenv('MODERATION_SERVER_ID'))

# Canaux spécifiques
MOD_LOGS_CHANNEL_ID = int(os.getenv('MOD_LOGS_CHANNEL_ID'))
REPORT_CHANNEL_ID = int(os.getenv('REPORT_CHANNEL_ID'))

# Rôles importants
ADMIN_ROLE_ID = int(os.getenv('ADMIN_ROLE_ID'))
MOD_ROLE_ID = int(os.getenv('MOD_ROLE_ID'))

# Configuration base de données
DATABASE_PATH = os.getenv('DATABASE_PATH', 'data/database.db')

# Cooldowns et limites
WARN_THRESHOLD = int(os.getenv('WARN_THRESHOLD', 3))
MUTE_DURATION = int(os.getenv('DEFAULT_MUTE_DURATION', 3600))  # en secondes (1 heure)
