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
                    
                    if deleted_