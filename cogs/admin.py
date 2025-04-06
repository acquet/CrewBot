# cogs/admin.py
import discord
from discord.ext import commands
from discord import app_commands
import os
import sys
import asyncio
import datetime
from typing import Optional, List

from config import ADMIN_ROLE_ID

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="reload", description="Recharge une extension")
    @app_commands.describe(extension="Le nom de l'extension à recharger")
    @commands.has_permissions(administrator=True)
    async def reload(self, ctx, extension: str):
        try:
            await self.bot.reload_extension(f"cogs.{extension}")
            await ctx.send(f"✅ L'extension `{extension}` a été rechargée.")
        except Exception as e:
            await ctx.send(f"❌ Erreur lors du rechargement de l'extension `{extension}`:\n```{e}```")

    @commands.hybrid_command(name="load", description="Charge une extension")
    @app_commands.describe(extension="Le nom de l'extension à charger")
    @commands.has_permissions(administrator=True)
    async def load(self, ctx, extension: str):
        try:
            await self.bot.load_extension(f"cogs.{extension}")
            await ctx.send(f"✅ L'extension `{extension}` a été chargée.")
        except Exception as e:
            await ctx.send(f"❌ Erreur lors du chargement de l'extension `{extension}`:\n```{e}```")

    @commands.hybrid_command(name="unload", description="Décharge une extension")
    @app_commands.describe(extension="Le nom de l'extension à décharger")
    @commands.has_permissions(administrator=True)
    async def unload(self, ctx, extension: str):
        try:
            await self.bot.unload_extension(f"cogs.{extension}")
            await ctx.send(f"✅ L'extension `{extension}` a été déchargée.")
        except Exception as e:
            await ctx.send(f"❌ Erreur lors du déchargement de l'extension `{extension}`:\n```{e}```")

    @commands.hybrid_command(name="extensions", description="Liste toutes les extensions")
    @commands.has_permissions(administrator=True)
    async def extensions(self, ctx):
        extensions_list = []
        
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                extension_name = filename[:-3]
                extension_status = "Chargée" if extension_name in self.bot.extensions else "Non chargée"
                extensions_list.append(f"• `{extension_name}`: {extension_status}")
        
        embed = discord.Embed(
            title="Extensions",
            description="\n".join(extensions_list) or "Aucune extension trouvée.",
            color=discord.Color.blue()
        )
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="sync", description="Synchronise les commandes slash")
    @commands.has_permissions(administrator=True)
    async def sync(self, ctx):
        try:
            # Commencer la synchro
            message = await ctx.send("⏳ Synchronisation des commandes slash en cours...")
            
            # Synchroniser les commandes
            synced = await self.bot.tree.sync()
            
            # Mettre à jour le message
            await message.edit(content=f"✅ {len(synced)} commandes slash ont été synchronisées.")
        except Exception as e:
            await ctx.send(f"❌ Erreur lors de la synchronisation des commandes slash:\n```{e}```")

    @commands.hybrid_command(name="status", description="Change le statut du bot")
    @app_commands.describe(
        status_type="Le type de statut",
        status_text="Le texte du statut"
    )
    @app_commands.choices(status_type=[
        app_commands.Choice(name="Joue à", value="playing"),
        app_commands.Choice(name="Regarde", value="watching"),
        app_commands.Choice(name="Écoute", value="listening"),
        app_commands.Choice(name="Competing", value="competing")
    ])
    @commands.has_permissions(administrator=True)
    async def status(self, ctx, status_type: str, *, status_text: str):
        try:
            activity_types = {
                "playing": discord.ActivityType.playing,
                "watching": discord.ActivityType.watching,
                "listening": discord.ActivityType.listening,
                "competing": discord.ActivityType.competing
            }
            
            activity_type = activity_types.get(status_type.lower(), discord.ActivityType.playing)
            
            await self.bot.change_presence(activity=discord.Activity(
                type=activity_type,
                name=status_text
            ))
            
            await ctx.send(f"✅ Statut changé en: **{status_type}** {status_text}")
            
        except Exception as e:
            await ctx.send(f"❌ Erreur lors du changement de statut:\n```{e}```")

    @commands.hybrid_command(name="announce", description="Envoie une annonce dans un canal")
    @app_commands.describe(
        channel="Le canal où envoyer l'annonce",
        title="Le titre de l'annonce",
        message="Le contenu de l'annonce"
    )
    @commands.has_permissions(administrator=True)
    async def announce(self, ctx, channel: discord.TextChannel, title: str, *, message: str):
        try:
            # Créer l'embed d'annonce
            embed = discord.Embed(
                title=title,
                description=message,
                color=discord.Color.blue(),
                timestamp=datetime.datetime.now()
            )
            
            embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
            embed.set_footer(text=f"Annonce par {ctx.author.display_name}")
            
            # Envoyer l'annonce
            announcement = await channel.send(embed=embed)
            
            # Confirmation
            await ctx.send(f"✅ Annonce envoyée dans {channel.mention}!")
            
        except Exception as e:
            await ctx.send(f"❌ Erreur lors de l'envoi de l'annonce:\n```{e}```")

    # cogs/admin.py (suite)
    @commands.hybrid_command(name="purge_user", description="Supprime tous les messages d'un utilisateur dans tous les canaux")
    @app_commands.describe(
        user="L'utilisateur dont les messages doivent être supprimés",
        days="Nombre de jours en arrière à vérifier (1-7)",
        reason="Raison de la purge des messages"
    )
    @commands.has_permissions(administrator=True)
    async def purge_user(self, ctx, user: discord.User, days: int = 1, *, reason: str = "Pas de raison spécifiée"):
        if days < 1 or days > 7:
            return await ctx.send("Le nombre de jours doit être entre 1 et 7.")
        
        # Message de confirmation
        confirm_msg = await ctx.send(f"⚠️ Vous êtes sur le point de supprimer tous les messages de {user.mention} des {days} derniers jours dans tous les canaux. Cette action est irréversible.\n\nConfirmez-vous cette action? (oui/non)")
        
        try:
            # Attendre la confirmation
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ["oui", "non"]
            
            response = await self.bot.wait_for('message', check=check, timeout=30.0)
            
            if response.content.lower() != "oui":
                return await ctx.send("Action annulée.")
            
            # Obtenir la date limite
            time_limit = datetime.datetime.now() - datetime.timedelta(days=days)
            
            # Message de début
            status_msg = await ctx.send(f"⏳ Suppression des messages de {user.mention} en cours...")
            
            # Parcourir tous les canaux de texte
            total_deleted = 0
            for channel in ctx.guild.text_channels:
                try:
                    # Récupérer l'historique des messages
                    deleted_in_channel = 0
                    async for message in channel.history(limit=None, after=time_limit):
                        if message.author.id == user.id:
                            await message.delete()
                            deleted_in_channel += 1
                            total_deleted += 1
                            # Pause pour éviter le rate limiting
                            await asyncio.sleep(0.5)
                    
                    if deleted_in_channel > 0:
                        await status_msg.edit(content=f"⏳ Suppression en cours... {total_deleted} messages supprimés jusqu'à présent. Canal actuel: {channel.mention} ({deleted_in_channel} messages)")
                
                except discord.Forbidden:
                    await ctx.send(f"⚠️ Je n'ai pas les permissions nécessaires pour supprimer des messages dans {channel.mention}.")
                except Exception as e:
                    await ctx.send(f"❌ Erreur lors de la suppression des messages dans {channel.mention}:\n```{e}```")
            
            # Message final
            await status_msg.edit(content=f"✅ Terminé! {total_deleted} messages de {user.mention} ont été supprimés.")
            
            # Enregistrer l'action de modération
            try:
                from utils.db_handler import DatabaseHandler
                db = DatabaseHandler()
                db.add_mod_action("purge", user.id, ctx.guild.id, ctx.author.id, reason)
                db.close()
            except Exception as e:
                print(f"Erreur lors de l'enregistrement de l'action de purge: {e}")
            
        except asyncio.TimeoutError:
            await confirm_msg.edit(content="Action annulée (délai expiré).")
        except Exception as e:
            await ctx.send(f"❌ Erreur lors de la purge des messages:\n```{e}```")

    @commands.hybrid_command(name="lockdown", description="Verrouille ou déverrouille un canal")
    @app_commands.describe(
        channel="Le canal à verrouiller (par défaut: canal actuel)",
        reason="Raison du verrouillage"
    )
    @commands.has_permissions(manage_channels=True)
    async def lockdown(self, ctx, channel: Optional[discord.TextChannel] = None, *, reason: str = "Pas de raison spécifiée"):
        channel = channel or ctx.channel
        
        # Récupérer le rôle @everyone
        everyone_role = ctx.guild.default_role
        
        # Vérifier l'état actuel des permissions
        current_perms = channel.permissions_for(everyone_role)
        is_locked = not current_perms.send_messages
        
        if is_locked:
            # Déverrouiller le canal
            await channel.set_permissions(everyone_role, send_messages=True)
            await ctx.send(f"🔓 Le canal {channel.mention} a été déverrouillé.")
            
            # Créer l'embed d'annonce
            embed = discord.Embed(
                title="Canal déverrouillé",
                description=f"Ce canal est maintenant ouvert à tous les utilisateurs.",
                color=discord.Color.green(),
                timestamp=datetime.datetime.now()
            )
            embed.add_field(name="Modérateur", value=ctx.author.mention, inline=True)
            embed.add_field(name="Raison", value=reason, inline=True)
            
            await channel.send(embed=embed)
        else:
            # Verrouiller le canal
            await channel.set_permissions(everyone_role, send_messages=False)
            await ctx.send(f"🔒 Le canal {channel.mention} a été verrouillé.")
            
            # Créer l'embed d'annonce
            embed = discord.Embed(
                title="Canal verrouillé",
                description=f"Ce canal a été temporairement verrouillé.",
                color=discord.Color.red(),
                timestamp=datetime.datetime.now()
            )
            embed.add_field(name="Modérateur", value=ctx.author.mention, inline=True)
            embed.add_field(name="Raison", value=reason, inline=True)
            
            await channel.send(embed=embed)

    @commands.hybrid_command(name="slowmode", description="Définit le mode lent d'un canal")
    @app_commands.describe(
        seconds="Durée en secondes (0 pour désactiver, max 21600)",
        channel="Le canal (par défaut: canal actuel)",
        reason="Raison du changement"
    )
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, seconds: int, channel: Optional[discord.TextChannel] = None, *, reason: str = "Pas de raison spécifiée"):
        channel = channel or ctx.channel
        
        if seconds < 0 or seconds > 21600:
            return await ctx.send("La durée doit être entre 0 et 21600 secondes (6 heures).")
        
        await channel.edit(slowmode_delay=seconds)
        
        if seconds == 0:
            await ctx.send(f"✅ Mode lent désactivé dans {channel.mention}.")
            
            # Créer l'embed d'annonce
            embed = discord.Embed(
                title="Mode lent désactivé",
                description=f"Le mode lent a été désactivé dans ce canal.",
                color=discord.Color.green(),
                timestamp=datetime.datetime.now()
            )
            embed.add_field(name="Modérateur", value=ctx.author.mention, inline=True)
            embed.add_field(name="Raison", value=reason, inline=True)
            
            await channel.send(embed=embed)
        else:
            # Formatage du temps
            if seconds < 60:
                time_str = f"{seconds} seconde(s)"
            elif seconds < 3600:
                minutes = seconds // 60
                time_str = f"{minutes} minute(s)"
            else:
                hours = seconds // 3600
                minutes = (seconds % 3600) // 60
                time_str = f"{hours} heure(s)"
                if minutes > 0:
                    time_str += f" et {minutes} minute(s)"
            
            await ctx.send(f"✅ Mode lent défini à {time_str} dans {channel.mention}.")
            
            # Créer l'embed d'annonce
            embed = discord.Embed(
                title="Mode lent activé",
                description=f"Le mode lent a été activé dans ce canal.",
                color=discord.Color.orange(),
                timestamp=datetime.datetime.now()
            )
            embed.add_field(name="Durée", value=time_str, inline=True)
            embed.add_field(name="Modérateur", value=ctx.author.mention, inline=True)
            embed.add_field(name="Raison", value=reason, inline=True)
            
            await channel.send(embed=embed)

    @commands.hybrid_command(name="backup", description="Crée une sauvegarde de la base de données")
    @commands.has_permissions(administrator=True)
    async def backup(self, ctx):
        try:
            # Créer un dossier backups s'il n'existe pas
            if not os.path.exists('backups'):
                os.makedirs('backups')
            
            # Générer un nom de fichier avec la date
            date_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            backup_path = f"backups/database_backup_{date_str}.db"
            
            # Copier la base de données
            import shutil
            shutil.copy2('data/database.db', backup_path)
            
            await ctx.send(f"✅ Sauvegarde créée avec succès: `{backup_path}`")
            
        except Exception as e:
            await ctx.send(f"❌ Erreur lors de la création de la sauvegarde:\n```{e}```")

    @commands.hybrid_command(name="set_config", description="Définit une valeur de configuration pour le serveur")
    @app_commands.describe(
        key="La clé de configuration",
        value="La valeur à définir"
    )
    @commands.has_permissions(administrator=True)
    async def set_config(self, ctx, key: str, *, value: str):
        try:
            from utils.db_handler import DatabaseHandler
            db = DatabaseHandler()
            
            # Récupérer la configuration actuelle
            config = db.get_server_config(ctx.guild.id)
            
            # Mettre à jour la valeur
            config[key] = value
            
            # Sauvegarder la configuration
            db.update_server_config(ctx.guild.id, config)
            db.close()
            
            await ctx.send(f"✅ Configuration mise à jour: `{key}` = `{value}`")
            
        except Exception as e:
            await ctx.send(f"❌ Erreur lors de la mise à jour de la configuration:\n```{e}```")

    @commands.hybrid_command(name="get_config", description="Récupère une valeur de configuration pour le serveur")
    @app_commands.describe(
        key="La clé de configuration (facultatif, toutes les valeurs si non spécifié)"
    )
    @commands.has_permissions(administrator=True)
    async def get_config(self, ctx, key: Optional[str] = None):
        try:
            from utils.db_handler import DatabaseHandler
            db = DatabaseHandler()
            
            # Récupérer la configuration
            config = db.get_server_config(ctx.guild.id)
            db.close()
            
            if key:
                # Récupérer une valeur spécifique
                if key in config:
                    await ctx.send(f"📝 Configuration: `{key}` = `{config[key]}`")
                else:
                    await ctx.send(f"❌ La clé `{key}` n'existe pas dans la configuration.")
            else:
                # Récupérer toutes les valeurs
                if not config:
                    return await ctx.send("❌ Aucune configuration n'a été définie pour ce serveur.")
                
                # Créer un embed avec toutes les valeurs
                embed = discord.Embed(
                    title=f"Configuration de {ctx.guild.name}",
                    color=discord.Color.blue(),
                    timestamp=datetime.datetime.now()
                )
                
                for k, v in config.items():
                    embed.add_field(name=k, value=v, inline=False)
                
                await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Erreur lors de la récupération de la configuration:\n```{e}```")

async def setup(bot):
    await bot.add_cog(Admin(bot))
