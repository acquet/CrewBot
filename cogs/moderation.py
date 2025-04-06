# cogs/moderation.py
import discord
from discord.ext import commands
from discord import app_commands
import datetime
import asyncio
from typing import Optional
import sqlite3
import sys
import traceback

from config import MOD_LOGS_CHANNEL_ID, MODERATION_SERVER_ID, MOD_ROLE_ID, ADMIN_ROLE_ID, WARN_THRESHOLD, MUTE_DURATION
from utils.embeds import create_mod_action_embed, create_report_embed
from utils.permissions import is_mod_or_admin

class Moderation(commands.Cog):
    # Au lieu d'ouvrir et fermer la connexion dans chaque commande
    def __init__(self, bot):
        self.bot = bot
        from utils.db_handler import DatabaseHandler
        self.db_handler = DatabaseHandler()  # Instance unique

    def cog_unload(self):
        """Ferme la connexion à la base de données lors du déchargement du cog"""
        if hasattr(self, 'db_handler'):
            self.db_handler.close()

    def setup_database(self):
        # Créer la table pour les avertissements
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS warnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            server_id INTEGER NOT NULL,
            moderator_id INTEGER NOT NULL,
            reason TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Créer la table pour les actions de modération
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS mod_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_type TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            server_id INTEGER NOT NULL,
            moderator_id INTEGER NOT NULL,
            reason TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            duration INTEGER
        )
        ''')
        self.conn.commit()

    async def send_to_mod_server(self, action_type, user, moderator, reason, duration=None):
        """Envoie un rapport au serveur de modération"""
        try:
            # Récupérer le serveur de modération
            mod_server = self.bot.get_guild(MODERATION_SERVER_ID)
            if not mod_server:
                return False, "Serveur de modération introuvable"
            
            # Récupérer le canal des logs
            mod_channel = mod_server.get_channel(MOD_LOGS_CHANNEL_ID)
            if not mod_channel:
                return False, "Canal de logs introuvable sur le serveur de modération"

            # Créer l'embed de rapport
            embed = create_report_embed(
                action_type=action_type,
                user=user,
                moderator=moderator,
                reason=reason,
                duration=duration
            )
            
            # Envoyer l'embed
            await mod_channel.send(embed=embed)
            return True, "Rapport envoyé avec succès"
            
        except Exception as e:
            print(f"Erreur lors de l'envoi du rapport: {e}")
            traceback.print_exc()
            return False, str(e)

    @commands.hybrid_command(name="warn", description="Avertir un membre")
    @app_commands.describe(
        member="Le membre à avertir",
        reason="La raison de l'avertissement"
    )
    @commands.has_any_role(MOD_ROLE_ID, ADMIN_ROLE_ID)
    async def warn(self, ctx, member: discord.Member, *, reason: str = "Aucune raison fournie"):
        # Vérification que l'utilisateur n'essaie pas d'avertir un modérateur ou un administrateur
        if is_mod_or_admin(member):
            return await ctx.send("Vous ne pouvez pas avertir un modérateur ou administrateur.")
        
        # Enregistrer l'avertissement dans la base de données
        self.cursor.execute('''
        INSERT INTO warnings (user_id, server_id, moderator_id, reason)
        VALUES (?, ?, ?, ?)
        ''', (member.id, ctx.guild.id, ctx.author.id, reason))
        
        self.cursor.execute('''
        INSERT INTO mod_actions (action_type, user_id, server_id, moderator_id, reason)
        VALUES (?, ?, ?, ?, ?)
        ''', ("warn", member.id, ctx.guild.id, ctx.author.id, reason))
        
        self.conn.commit()
        
        # Obtenir le nombre total d'avertissements
        self.cursor.execute('''
        SELECT COUNT(*) FROM warnings 
        WHERE user_id = ? AND server_id = ?
        ''', (member.id, ctx.guild.id))
        
        warning_count = self.cursor.fetchone()[0]
        
        # Envoyer un message dans le canal actuel
        embed = create_mod_action_embed(
            action_type="Avertissement",
            member=member,
            moderator=ctx.author,
            reason=reason,
            warning_count=warning_count
        )
        await ctx.send(embed=embed)
        
        # Envoyer un message privé à l'utilisateur
        try:
            user_embed = discord.Embed(
                title=f"Vous avez reçu un avertissement",
                description=f"Vous avez été averti sur {ctx.guild.name}",
                color=discord.Color.gold()
            )
            user_embed.add_field(name="Raison", value=reason)
            user_embed.add_field(name="Modérateur", value=ctx.author.name)
            user_embed.add_field(name="Nombre d'avertissements", value=warning_count)
            user_embed.set_footer(text=f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            await member.send(embed=user_embed)
        except:
            await ctx.send("Je n'ai pas pu envoyer un message à l'utilisateur.")
        
        # Envoyer le rapport au serveur de modération
        success, message = await self.send_to_mod_server(
            action_type="Avertissement",
            user=member,
            moderator=ctx.author,
            reason=reason
        )
        
        if not success:
            await ctx.send(f"⚠️ Erreur lors de l'envoi du rapport au serveur de modération: {message}")
        
        # Appliquer des actions automatiques basées sur le nombre d'avertissements
        if warning_count >= WARN_THRESHOLD:
            await self.timeout(ctx, member, duration=MUTE_DURATION, reason=f"Seuil d'avertissements atteint ({warning_count})")

    @commands.hybrid_command(name="kick", description="Expulser un membre du serveur")
    @app_commands.describe(
        member="Le membre à expulser",
        reason="La raison de l'expulsion"
    )
    @commands.has_any_role(MOD_ROLE_ID, ADMIN_ROLE_ID)
    async def kick(self, ctx, member: discord.Member, *, reason: str = "Aucune raison fournie"):
        if is_mod_or_admin(member):
            return await ctx.send("Vous ne pouvez pas expulser un modérateur ou administrateur.")
        
        # Enregistrer l'action dans la base de données
        self.cursor.execute('''
        INSERT INTO mod_actions (action_type, user_id, server_id, moderator_id, reason)
        VALUES (?, ?, ?, ?, ?)
        ''', ("kick", member.id, ctx.guild.id, ctx.author.id, reason))
        self.conn.commit()
        
        # Créer l'embed pour l'expulsion
        embed = create_mod_action_embed(
            action_type="Expulsion",
            member=member,
            moderator=ctx.author,
            reason=reason
        )
        
        # Envoyer un message privé à l'utilisateur avant de l'expulser
        try:
            user_embed = discord.Embed(
                title=f"Vous avez été expulsé",
                description=f"Vous avez été expulsé de {ctx.guild.name}",
                color=discord.Color.red()
            )
            user_embed.add_field(name="Raison", value=reason)
            user_embed.add_field(name="Modérateur", value=ctx.author.name)
            user_embed.set_footer(text=f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            await member.send(embed=user_embed)
        except:
            await ctx.send("Je n'ai pas pu envoyer un message à l'utilisateur.")
        
        # Expulser le membre
        await member.kick(reason=reason)
        await ctx.send(embed=embed)
        
        # Envoyer le rapport au serveur de modération
        await self.send_to_mod_server(
            action_type="Expulsion",
            user=member,
            moderator=ctx.author,
            reason=reason
        )

    @commands.hybrid_command(name="ban", description="Bannir un membre du serveur")
    @app_commands.describe(
        member="Le membre à bannir",
        delete_days="Nombre de jours de messages à supprimer (0-7)",
        reason="La raison du bannissement"
    )
    @commands.has_any_role(MOD_ROLE_ID, ADMIN_ROLE_ID)
    async def ban(self, ctx, member: discord.Member, delete_days: Optional[int] = 1, *, reason: str = "Aucune raison fournie"):
        if is_mod_or_admin(member):
            return await ctx.send("Vous ne pouvez pas bannir un modérateur ou administrateur.")
            
        # Vérifier que delete_days est entre 0 et 7
        delete_days = max(0, min(7, delete_days))
        
        # Enregistrer l'action dans la base de données
        self.cursor.execute('''
        INSERT INTO mod_actions (action_type, user_id, server_id, moderator_id, reason)
        VALUES (?, ?, ?, ?, ?)
        ''', ("ban", member.id, ctx.guild.id, ctx.author.id, reason))
        self.conn.commit()
        
        # Créer l'embed pour le bannissement
        embed = create_mod_action_embed(
            action_type="Bannissement",
            member=member,
            moderator=ctx.author,
            reason=reason
        )
        
        # Envoyer un message privé à l'utilisateur avant de le bannir
        try:
            user_embed = discord.Embed(
                title=f"Vous avez été banni",
                description=f"Vous avez été banni de {ctx.guild.name}",
                color=discord.Color.dark_red()
            )
            user_embed.add_field(name="Raison", value=reason)
            user_embed.add_field(name="Modérateur", value=ctx.author.name)
            user_embed.set_footer(text=f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            await member.send(embed=user_embed)
        except:
            await ctx.send("Je n'ai pas pu envoyer un message à l'utilisateur.")
        
        # Bannir le membre
        await member.ban(reason=reason, delete_message_days=delete_days)
        await ctx.send(embed=embed)
        
        # Envoyer le rapport au serveur de modération
        await self.send_to_mod_server(
            action_type="Bannissement",
            user=member,
            moderator=ctx.author,
            reason=reason
        )

    @commands.hybrid_command(name="timeout", description="Mettre un utilisateur en timeout")
    @app_commands.describe(
        member="Le membre à mettre en timeout",
        duration="Durée en minutes",
        reason="La raison du timeout"
    )
    @commands.has_any_role(MOD_ROLE_ID, ADMIN_ROLE_ID)
    async def timeout(self, ctx, member: discord.Member, duration: int = 60, *, reason: str = "Aucune raison fournie"):
        if is_mod_or_admin(member):
            return await ctx.send("Vous ne pouvez pas mettre en timeout un modérateur ou administrateur.")
        
        # Calculer la date de fin du timeout
        duration_seconds = duration * 60  # Convertir en secondes
        until = discord.utils.utcnow() + datetime.timedelta(seconds=duration_seconds)
        
        # Enregistrer l'action dans la base de données
        self.cursor.execute('''
        INSERT INTO mod_actions (action_type, user_id, server_id, moderator_id, reason, duration)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', ("timeout", member.id, ctx.guild.id, ctx.author.id, reason, duration_seconds))
        self.conn.commit()
        
        # Appliquer le timeout
        await member.timeout(until, reason=reason)
        
        # Créer l'embed pour le timeout
        embed = create_mod_action_embed(
            action_type="Timeout",
            member=member,
            moderator=ctx.author,
            reason=reason,
            duration=f"{duration} minutes"
        )
        await ctx.send(embed=embed)
        
        # Envoyer un message privé à l'utilisateur
        try:
            user_embed = discord.Embed(
                title=f"Vous avez été mis en timeout",
                description=f"Vous avez été mis en timeout sur {ctx.guild.name}",
                color=discord.Color.orange()
            )
            user_embed.add_field(name="Raison", value=reason)
            user_embed.add_field(name="Durée", value=f"{duration} minutes")
            user_embed.add_field(name="Modérateur", value=ctx.author.name)
            user_embed.set_footer(text=f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            await member.send(embed=user_embed)
        except:
            await ctx.send("Je n'ai pas pu envoyer un message à l'utilisateur.")
        
        # Envoyer le rapport au serveur de modération
        await self.send_to_mod_server(
            action_type="Timeout",
            user=member,
            moderator=ctx.author,
            reason=reason,
            duration=f"{duration} minutes"
        )

    @commands.hybrid_command(name="clear", description="Supprimer un certain nombre de messages")
    @app_commands.describe(
        amount="Nombre de messages à supprimer (1-100)",
        user="Utilisateur dont les messages doivent être supprimés (optionnel)"
    )
    @commands.has_any_role(MOD_ROLE_ID, ADMIN_ROLE_ID)
    async def clear(self, ctx, amount: int, user: Optional[discord.Member] = None):
        if amount < 1 or amount > 100:
            return await ctx.send("Le nombre de messages doit être entre 1 et 100.")
        
        # Supprimer le message de commande
        await ctx.message.delete()
        
        # Définir le filtrage des messages
        def check(msg):
            return user is None or msg.author == user
        
        # Supprimer les messages
        deleted = await ctx.channel.purge(limit=amount, check=check)
        
        # Envoyer une confirmation
        confirmation = await ctx.send(f"✅ {len(deleted)} messages ont été supprimés.")
        
        # Enregistrer l'action dans la base de données
        target_user_id = user.id if user else 0
        self.cursor.execute('''
        INSERT INTO mod_actions (action_type, user_id, server_id, moderator_id, reason)
        VALUES (?, ?, ?, ?, ?)
        ''', ("clear", target_user_id, ctx.guild.id, ctx.author.id, f"Suppression de {len(deleted)} messages"))
        self.conn.commit()
        
        # Envoyer le rapport au serveur de modération
        await self.send_to_mod_server(
            action_type="Suppression de messages",
            user=user if user else None,
            moderator=ctx.author,
            reason=f"Suppression de {len(deleted)} messages dans #{ctx.channel.name}"
        )
        
        # Supprimer le message de confirmation après 5 secondes
        await asyncio.sleep(5)
        await confirmation.delete()

    @commands.hybrid_command(name="warnings", description="Voir les avertissements d'un membre")
    @app_commands.describe(
        member="Le membre dont vous voulez voir les avertissements"
    )
    @commands.has_any_role(MOD_ROLE_ID, ADMIN_ROLE_ID)
    async def warnings(self, ctx, member: discord.Member):
        # Récupérer les avertissements de la base de données
        self.cursor.execute('''
        SELECT id, moderator_id, reason, timestamp FROM warnings 
        WHERE user_id = ? AND server_id = ?
        ORDER BY timestamp DESC
        ''', (member.id, ctx.guild.id))
        
        warnings = self.cursor.fetchall()
        
        if not warnings:
            return await ctx.send(f"{member.mention} n'a pas d'avertissements.")
        
        # Créer un embed pour afficher les avertissements
        embed = discord.Embed(
            title=f"Avertissements de {member.display_name}",
            description=f"Total: {len(warnings)} avertissement(s)",
            color=discord.Color.gold()
        )
        
        # Ajouter les 10 derniers avertissements à l'embed
        for i, (warn_id, mod_id, reason, timestamp) in enumerate(warnings[:10], 1):
            mod = ctx.guild.get_member(mod_id)
            mod_name = mod.display_name if mod else "Modérateur inconnu"
            embed.add_field(
                name=f"Avertissement #{warn_id} | {timestamp}",
                value=f"**Modérateur:** {mod_name}\n**Raison:** {reason}",
                inline=False
            )
        
        # Si plus de 10 avertissements, ajouter une note
        if len(warnings) > 10:
            embed.set_footer(text=f"Affichage des 10 derniers avertissements sur un total de {len(warnings)}")
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="clearwarnings", description="Effacer les avertissements d'un membre")
    @app_commands.describe(
        member="Le membre dont vous voulez effacer les avertissements",
        warn_id="ID spécifique de l'avertissement à effacer (optionnel, tous si non spécifié)"
    )
    @commands.has_any_role(ADMIN_ROLE_ID)
    async def clearwarnings(self, ctx, member: discord.Member, warn_id: Optional[int] = None):
        if warn_id:
            # Vérifier si l'avertissement existe
            self.cursor.execute('''
            SELECT id FROM warnings 
            WHERE id = ? AND user_id = ? AND server_id = ?
            ''', (warn_id, member.id, ctx.guild.id))
            
            if not self.cursor.fetchone():
                return await ctx.send(f"Avertissement #{warn_id} non trouvé pour {member.mention}.")
            
            # Supprimer l'avertissement spécifique
            self.cursor.execute('''
            DELETE FROM warnings 
            WHERE id = ? AND user_id = ? AND server_id = ?
            ''', (warn_id, member.id, ctx.guild.id))
            self.conn.commit()
            
            await ctx.send(f"L'avertissement #{warn_id} de {member.mention} a été supprimé.")
            
            # Envoyer le rapport au serveur de modération
            await self.send_to_mod_server(
                action_type="Suppression d'avertissement",
                user=member,
                moderator=ctx.author,
                reason=f"Suppression de l'avertissement #{warn_id}"
            )
        
        else:
            # Compter le nombre d'avertissements pour obtenir un décompte avant de les supprimer
            self.cursor.execute('''
            SELECT COUNT(*) FROM warnings 
            WHERE user_id = ? AND server_id = ?
            ''', (member.id, ctx.guild.id))
            
            count = self.cursor.fetchone()[0]
            
            if count == 0:
                return await ctx.send(f"{member.mention} n'a pas d'avertissements.")
            
            # Supprimer tous les avertissements
            self.cursor.execute('''
            DELETE FROM warnings 
            WHERE user_id = ? AND server_id = ?
            ''', (member.id, ctx.guild.id))
            self.conn.commit()
            
            await ctx.send(f"Tous les avertissements ({count}) de {member.mention} ont été supprimés.")
            
            # Envoyer le rapport au serveur de modération
            await self.send_to_mod_server(
                action_type="Suppression d'avertissements",
                user=member,
                moderator=ctx.author,
                reason=f"Suppression de tous les avertissements ({count})"
            )

    @commands.hybrid_command(name="modlogs", description="Afficher l'historique des actions de modération")
    @app_commands.describe(
        member="Le membre dont vous voulez voir l'historique de modération"
    )
    @commands.has_any_role(MOD_ROLE_ID, ADMIN_ROLE_ID)
    async def modlogs(self, ctx, member: discord.Member):
        # Récupérer l'historique des actions de modération
        self.cursor.execute('''
        SELECT action_type, moderator_id, reason, timestamp, duration
        FROM mod_actions 
        WHERE user_id = ? AND server_id = ?
        ORDER BY timestamp DESC
        LIMIT 15
        ''', (member.id, ctx.guild.id))
        
        actions = self.cursor.fetchall()
        
        if not actions:
            return await ctx.send(f"Aucune action de modération enregistrée pour {member.mention}.")
        
        # Créer un embed pour afficher l'historique
        embed = discord.Embed(
            title=f"Historique de modération de {member.display_name}",
            color=discord.Color.blue()
        )
        
        for action_type, mod_id, reason, timestamp, duration in actions:
            mod = ctx.guild.get_member(mod_id)
            mod_name = mod.display_name if mod else "Modérateur inconnu"
            
            value = f"**Modérateur:** {mod_name}\n**Raison:** {reason}"
            if duration:
                value += f"\n**Durée:** {duration} secondes"
                
            embed.add_field(
                name=f"{action_type} | {timestamp}",
                value=value,
                inline=False
            )
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="report", description="Signaler un utilisateur aux modérateurs")
    @app_commands.describe(
        member="Le membre à signaler",
        reason="La raison du signalement"
    )
    async def report(self, ctx, member: discord.Member, *, reason: str):
        if member.id == ctx.author.id:
            return await ctx.send("Vous ne pouvez pas vous signaler vous-même.")
            
        if member.bot:
            return await ctx.send("Vous ne pouvez pas signaler un bot.")
        
        # Créer l'embed du rapport
        embed = discord.Embed(
            title="Nouveau signalement",
            description=f"{ctx.author.mention} a signalé {member.mention}",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        
        embed.add_field(name="Raison", value=reason, inline=False)
        embed.add_field(name="Canal", value=ctx.channel.mention, inline=True)
        embed.add_field(name="Serveur", value=ctx.guild.name, inline=True)
        
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"ID: {member.id}")
        
        # Envoyer le rapport au serveur de modération
        success, message = await self.send_to_mod_server(
            action_type="Signalement",
            user=member,
            moderator=ctx.author,
            reason=reason
        )
        
        if success:
            # Envoyer une confirmation à l'utilisateur
            await ctx.send("✅ Votre signalement a été envoyé à l'équipe de modération. Merci de nous aider à maintenir le serveur en sécurité.")
        else:
            await ctx.send(f"⚠️ Erreur lors de l'envoi du signalement: {message}")

    def cog_unload(self):
        # Fermer la connexion à la base de données lors du déchargement du cog
        self.conn.close()

async def setup(bot):
    await bot.add_cog(Moderation(bot))
