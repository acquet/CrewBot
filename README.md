# Bot Discord de Modération et d'Utilitaires

## Description
Ce bot Discord est conçu pour faciliter la modération et offrir diverses fonctionnalités utilitaires pour votre serveur. Il inclut des commandes de modération, des sondages, des giveaways, des suggestions, et plus encore.

## Fonctionnalités principales
- **Commandes d'information**: ping, serverinfo, userinfo, avatar
- **Outils de communauté**: sondages, suggestions, rappels, giveaways
- **Système de modération**: Gestion des avertissements avec un seuil configurable
- **Interface hybride**: Compatible avec les commandes slash et les commandes textuelles

## Prérequis
- Python 3.8 ou supérieur
- Packages listés dans `requirements.txt`
- Un token bot Discord

## Installation
1. Clonez le dépôt:
```bash
git clone [URL_DU_REPO]
cd [NOM_DU_REPO]
```

2. Installez les dépendances:
```bash
pip install -r requirements.txt
```

3. Configurez le fichier `.env` en vous basant sur le modèle fourni:
```
# Tokens et identifiants
DISCORD_TOKEN=votre_token_discord_ici
COMMAND_PREFIX=!
OWNER_IDS=12345678901234567,98765432109876543

# IDs des serveurs
MAIN_SERVER_ID=ID_du_serveur_principal
MODERATION_SERVER_ID=ID_du_serveur_de_moderation
ADMIN_SERVER_ID=ID_du_serveur_admin

# Canaux spécifiques
MOD_LOGS_CHANNEL_ID=ID_du_canal_de_logs_moderation
REPORT_CHANNEL_ID=ID_du_canal_de_rapports
VERSION_CHANNEL_ID=ID_du_canal_version

# Rôles importants
ADMIN_ROLE_ID=ID_du_role_admin
MOD_ROLE_ID=ID_du_role_moderateur

# Configuration base de données
DATABASE_PATH=data/database.db

# Paramètres de modération
WARN_THRESHOLD=3
DEFAULT_MUTE_DURATION=3600
```

4. Lancez le bot:
```bash
python main.py
```

## Structure du projet
- `main.py` - Point d'entrée principal du bot
- `config.py` - Configuration et variables d'environnement
- `cogs/` - Modules avec différentes fonctionnalités
- `data/` - Stockage des données persistantes
- `utils/` - Utilitaires et fonctions d'aide

## Commandes disponibles

### Utilitaires
- `!ping` - Vérifier la latence du bot
- `!serverinfo` - Afficher les informations du serveur
- `!userinfo [membre]` - Afficher les informations d'un utilisateur
- `!poll <question> [choix1|choix2|...]` - Créer un sondage
- `!avatar [membre]` - Afficher l'avatar d'un utilisateur
- `!reminder <minutes> <message>` - Définir un rappel
- `!help [commande]` - Afficher l'aide des commandes

### Suggestions
- `!setup_suggestions <canal> [enable_voting]` - Configurer un canal de suggestions
- `!suggest <suggestion>` - Faire une suggestion

### Giveaways
- `!giveaway <durée_minutes> <nb_gagnants> <prix>` - Créer un tirage au sort

## Mentions légales

### Licence
Ce projet est distribué sous la licence [INSÉRER VOTRE LICENCE ICI]. Veuillez consulter le fichier LICENSE pour plus de détails.

### Confidentialité
Ce bot collecte et stocke certaines données nécessaires à son fonctionnement:
- IDs des messages et des utilisateurs pour la modération et les fonctionnalités
- Paramètres spécifiques aux serveurs pour la personnalisation
- Logs d'activité pour le débogage

Ces données sont stockées localement et ne sont pas partagées avec des tiers.

### Avis de non-responsabilité
Ce bot est fourni "tel quel", sans garantie d'aucune sorte. Les développeurs ne peuvent être tenus responsables des problèmes liés à son utilisation.

## Contribution
Les contributions sont les bienvenues! N'hésitez pas à soumettre des pull requests ou à signaler des problèmes.

## Contact
Pour toute question ou assistance, veuillez contacter [VOTRE_CONTACT].
