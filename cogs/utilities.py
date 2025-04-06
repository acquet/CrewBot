# cogs/utilities.py
import discord
from discord.ext import commands
from discord import app_commands
import datetime
import time
import json
import os
import random
import asyncio
from typing import Optional

from config import MOD_ROLE_ID, ADMIN_ROLE_ID

class Utilities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.suggestion_channels = {}  # ID du canal: {"suggestion": bool, "vote": bool}
        self.load_settings()

    def load_settings(self):
        try:
            if os.path.exists('data/utility_settings.json'):
                with open('data/utility_settings.json', 'r') as f:
                    settings = json.load(f)
                    self.suggestion_channels = settings.get('suggestion_channels', {})
        except Exception as e:
            print(f"Erreur lors du chargement des paramètres: {e}")

    def save_settings(self):
        try:
            os.makedirs('data', exist_ok=True)
            with open('data/utility_settings.json', 'w') as f:
                json.dump({
                    'suggestion_channels': self.suggestion_channels
                }, f, indent=4)
        except Exception as e:
            print(f"Erreur lors de la sauvegarde des paramètres: {e}")

    @commands.hybrid_command(name="ping", description="Vérifier la latence du bot")
    async def ping(self, ctx):
        start_time = time.time()
        message = await ctx.send("Calcul de la latence...")
        end_time = time.time()
        
        api_latency = round(self.bot.latency * 1000)
        bot_latency = round((end_time - start_time) * 1000)
        
        embed = discord.Embed(
            title="🏓 Pong!",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now()
        )
        embed.add_field(name="Latence API", value=f"{api_latency} ms", inline=True)
        embed.add_field(name="Latence Bot", value=f"{bot_latency} ms", inline=True)
        
        await message.edit(content=None, embed=embed)

    @commands.hybrid_command(name="serverinfo", description="Affiche les informations du serveur")
    async def serverinfo(self, ctx):
        guild = ctx.guild
        
        # Collecter les informations
        total_members = guild.member_count
        online_members = len([m for m in guild.members if m.status != discord.Status.offline])
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        roles = len(guild.roles)
        emojis = len(guild.emojis)
        
        # Création de l'embed
        embed = discord.Embed(
            title=f"Informations sur {guild.name}",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now()
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        # Informations générales
        embed.add_field(name="ID", value=guild.id, inline=True)
        embed.add_field(name="Propriétaire", value=guild.owner.mention if guild.owner else "Non disponible", inline=True)
        embed.add_field(name="Créé le", value=guild.created_at.strftime("%d/%m/%Y"), inline=True)
        
        # Statistiques des membres
        embed.add_field(name="Membres", value=f"Total: {total_members}\nEn ligne: {online_members}", inline=True)
        
        # Statistiques des canaux
        embed.add_field(name="Canaux", value=f"Texte: {text_channels}\nVoix: {voice_channels}\nCatégories: {categories}", inline=True)
        
        # Autres statistiques
        embed.add_field(name="Rôles", value=roles, inline=True)
        embed.add_field(name="Emojis", value=emojis, inline=True)
        
        # Niveau de boost
        boost_level = guild.premium_tier
        boosts = guild.premium_subscription_count
        embed.add_field(name="Niveau de boost", value=f"Niveau {boost_level} ({boosts} boosts)", inline=True)
        
        await ctx.send(embed=embed)

   # cogs/utilities.py (suite)
    @commands.hybrid_command(name="userinfo", description="Affiche les informations d'un utilisateur")
    @app_commands.describe(member="Le membre dont vous voulez voir les informations")
    async def userinfo(self, ctx, member: Optional[discord.Member] = None):
        member = member or ctx.author
        
        # Collecter les informations
        joined_at = member.joined_at.strftime("%d/%m/%Y à %H:%M:%S") if member.joined_at else "Inconnue"
        created_at = member.created_at.strftime("%d/%m/%Y à %H:%M:%S")
        roles = [role.mention for role in reversed(member.roles) if role.name != "@everyone"]
        
        # Badges et statuts spéciaux
        badges = []
        if member.bot:
            badges.append("🤖 Bot")
        if member.guild_permissions.administrator:
            badges.append("👑 Administrateur")
        if any(role.id == MOD_ROLE_ID for role in member.roles):
            badges.append("🛡️ Modérateur")
        
        # Création de l'embed
        embed = discord.Embed(
            title=f"Informations sur {member.display_name}",
            color=member.color,
            timestamp=datetime.datetime.now()
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Informations générales
        embed.add_field(name="ID", value=member.id, inline=True)
        embed.add_field(name="Nom d'utilisateur", value=f"{member.name}#{member.discriminator}" if member.discriminator != "0" else member.name, inline=True)
        embed.add_field(name="Surnom", value=member.nick or "Aucun", inline=True)
        
        # Dates
        embed.add_field(name="Compte créé le", value=created_at, inline=True)
        embed.add_field(name="Rejoint le serveur le", value=joined_at, inline=True)
        
        # Rôles
        if roles:
            embed.add_field(name=f"Rôles ({len(roles)})", value=" ".join(roles[:10]) + ("..." if len(roles) > 10 else ""), inline=False)
        else:
            embed.add_field(name="Rôles", value="Aucun", inline=False)
        
        # Badges
        if badges:
            embed.add_field(name="Badges", value=" | ".join(badges), inline=False)
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="poll", description="Créer un sondage")
    @app_commands.describe(
        question="La question du sondage",
        choices="Les choix séparés par | (ex: Oui|Non|Peut-être)"
    )
    async def poll(self, ctx, question: str, *, choices: Optional[str] = None):
        if choices:
            # Sondage avec plusieurs choix
            options = choices.split('|')
            if len(options) > 10:
                return await ctx.send("Vous ne pouvez pas créer un sondage avec plus de 10 options.")
            
            # Liste des émojis numériques
            emoji_numbers = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
            
            # Création de l'embed
            embed = discord.Embed(
                title=f"📊 Sondage: {question}",
                description="\n".join([f"{emoji_numbers[i]} {option.strip()}" for i, option in enumerate(options)]),
                color=discord.Color.blue(),
                timestamp=datetime.datetime.now()
            )
            embed.set_footer(text=f"Créé par {ctx.author.display_name}")
            
            poll_message = await ctx.send(embed=embed)
            
            # Ajouter les réactions
            for i in range(len(options)):
                await poll_message.add_reaction(emoji_numbers[i])
                
        else:
            # Sondage simple oui/non
            embed = discord.Embed(
                title=f"📊 Sondage: {question}",
                color=discord.Color.blue(),
                timestamp=datetime.datetime.now()
            )
            embed.set_footer(text=f"Créé par {ctx.author.display_name}")
            
            poll_message = await ctx.send(embed=embed)
            
            # Ajouter les réactions oui/non
            await poll_message.add_reaction('👍')
            await poll_message.add_reaction('👎')

    @commands.hybrid_command(name="setup_suggestions", description="Configurer un canal de suggestions")
    @app_commands.describe(
        channel="Le canal où les suggestions seront envoyées",
        enable_voting="Activer les réactions de vote automatiques"
    )
    @commands.has_any_role(MOD_ROLE_ID, ADMIN_ROLE_ID)
    async def setup_suggestions(self, ctx, channel: discord.TextChannel, enable_voting: bool = True):
        channel_id = str(channel.id)
        self.suggestion_channels[channel_id] = {
            "suggestion": True,
            "vote": enable_voting
        }
        self.save_settings()
        
        await ctx.send(f"✅ Le canal {channel.mention} a été configuré comme canal de suggestions." + 
                      (" Les réactions de vote sont activées." if enable_voting else ""))

    @commands.hybrid_command(name="suggest", description="Faire une suggestion")
    @app_commands.describe(suggestion="Votre suggestion")
    async def suggest(self, ctx, *, suggestion: str):
        # Trouver un canal de suggestions dans le serveur
        suggestion_channel = None
        for channel_id, settings in self.suggestion_channels.items():
            if settings["suggestion"]:
                channel = ctx.guild.get_channel(int(channel_id))
                if channel:
                    suggestion_channel = channel
                    break
        
        if not suggestion_channel:
            return await ctx.send("Aucun canal de suggestions n'a été configuré. Les administrateurs peuvent en configurer un avec la commande `setup_suggestions`.")
        
        # Créer l'embed de suggestion
        embed = discord.Embed(
            title="💡 Nouvelle suggestion",
            description=suggestion,
            color=discord.Color.gold(),
            timestamp=datetime.datetime.now()
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text=f"ID: {ctx.author.id}")
        
        # Envoyer la suggestion
        suggestion_msg = await suggestion_channel.send(embed=embed)
        
        # Ajouter les réactions de vote si activées
        channel_id = str(suggestion_channel.id)
        if self.suggestion_channels.get(channel_id, {}).get("vote", False):
            await suggestion_msg.add_reaction('👍')
            await suggestion_msg.add_reaction('👎')
        
        # Confirmation
        await ctx.send(f"✅ Votre suggestion a été envoyée dans {suggestion_channel.mention}.")

    @commands.hybrid_command(name="giveaway", description="Créer un tirage au sort")
    @app_commands.describe(
        duration="Durée en minutes",
        winners="Nombre de gagnants",
        prize="Le prix à gagner"
    )
    @commands.has_any_role(MOD_ROLE_ID, ADMIN_ROLE_ID)
    async def giveaway(self, ctx, duration: int, winners: int, *, prize: str):
        if duration < 1:
            return await ctx.send("La durée doit être d'au moins 1 minute.")
        
        if winners < 1:
            return await ctx.send("Le nombre de gagnants doit être d'au moins 1.")
        
        # Calcul de la date de fin
        end_time = datetime.datetime.now() + datetime.timedelta(minutes=duration)
        
        # Création de l'embed
        embed = discord.Embed(
            title="🎉 GIVEAWAY 🎉",
            description=f"**{prize}**\n\nRéagissez avec 🎉 pour participer!",
            color=discord.Color.purple(),
            timestamp=end_time
        )
        
        embed.add_field(name="Fin", value=f"<t:{int(end_time.timestamp())}:R>", inline=True)
        embed.add_field(name="Gagnants", value=winners, inline=True)
        embed.add_field(name="Organisé par", value=ctx.author.mention, inline=True)
        embed.set_footer(text="Fin du tirage")
        
        # Envoyer le message de giveaway
        giveaway_msg = await ctx.send(embed=embed)
        await giveaway_msg.add_reaction('🎉')
        
        # Confirmation à l'auteur
        await ctx.send(f"✅ Giveaway créé! Il se terminera <t:{int(end_time.timestamp())}:R>.", ephemeral=True)
        
        # Attendre la fin du giveaway
        await asyncio.sleep(duration * 60)
        
        # Récupérer le message à jour
        try:
            channel = giveaway_msg.channel
            giveaway_msg = await channel.fetch_message(giveaway_msg.id)
            
            # Récupérer les participants
            reaction = discord.utils.get(giveaway_msg.reactions, emoji='🎉')
            
            if not reaction or reaction.count <= 1:
                # Pas assez de participants
                embed.description = f"**{prize}**\n\n**Tirage terminé!**\nPas assez de participants."
                await giveaway_msg.edit(embed=embed)
                return await channel.send("Le giveaway s'est terminé, mais il n'y avait pas assez de participants!")
            
            # Récupérer la liste des participants (sans le bot)
            users = await reaction.users().flatten()
            users.remove(self.bot.user)
            
            # S'assurer qu'il y a des participants
            if not users:
                embed.description = f"**{prize}**\n\n**Tirage terminé!**\nPas de participants."
                await giveaway_msg.edit(embed=embed)
                return await channel.send("Le giveaway s'est terminé, mais personne n'a participé!")
            
            # Sélectionner les gagnants
            winners_count = min(winners, len(users))
            winners_list = random.sample(users, winners_count)
            
            # Mettre à jour l'embed
            winners_mentions = ", ".join(winner.mention for winner in winners_list)
            embed.description = f"**{prize}**\n\n**Tirage terminé!**\nGagnant(s): {winners_mentions}"
            await giveaway_msg.edit(embed=embed)
            
            # Annoncer les gagnants
            await channel.send(f"🎉 Félicitations {winners_mentions}! Vous avez gagné **{prize}**!")
            
        except discord.NotFound:
            pass  # Le message a été supprimé
        except Exception as e:
            print(f"Erreur lors de la fin du giveaway: {e}")

    @commands.hybrid_command(name="avatar", description="Afficher l'avatar d'un utilisateur")
    @app_commands.describe(member="L'utilisateur dont vous voulez voir l'avatar")
    async def avatar(self, ctx, member: Optional[discord.Member] = None):
        member = member or ctx.author
        
        embed = discord.Embed(
            title=f"Avatar de {member.display_name}",
            color=member.color,
            timestamp=datetime.datetime.now()
        )
        
        embed.set_image(url=member.display_avatar.url)
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="reminder", description="Définir un rappel")
    @app_commands.describe(
        time="Durée en minutes",
        reminder="Le message de rappel"
    )
    async def reminder(self, ctx, time: int, *, reminder: str):
        if time < 1:
            return await ctx.send("Le délai doit être d'au moins 1 minute.")
        
        # Confirmation
        await ctx.send(f"✅ Je vous rappellerai de '{reminder}' dans {time} minutes.")
        
        # Attendre le délai
        await asyncio.sleep(time * 60)
        
        # Envoyer le rappel
        try:
            embed = discord.Embed(
                title="⏰ Rappel",
                description=reminder,
                color=discord.Color.blue(),
                timestamp=datetime.datetime.now()
            )
            embed.set_footer(text=f"Rappel défini il y a {time} minutes")
            
            await ctx.author.send(embed=embed)
        except discord.Forbidden:
            # Si l'utilisateur a bloqué les DMs
            await ctx.send(f"{ctx.author.mention}, voici votre rappel: {reminder}")

    @commands.hybrid_command(name="help", description="Afficher l'aide des commandes")
    @app_commands.describe(command="Commande spécifique pour laquelle afficher l'aide")
    async def help(self, ctx, command: Optional[str] = None):
        if command:
            # Afficher l'aide pour une commande spécifique
            cmd = self.bot.get_command(command)
            if not cmd:
                return await ctx.send(f"La commande `{command}` n'existe pas.")
            
            embed = discord.Embed(
                title=f"Aide: {cmd.name}",
                description=cmd.description or "Pas de description disponible.",
                color=discord.Color.blue()
            )
            
            if cmd.aliases:
                embed.add_field(name="Alias", value=", ".join(cmd.aliases), inline=False)
            
            usage = f"{ctx.prefix}{cmd.name}"
            if cmd.signature:
                usage += f" {cmd.signature}"
            embed.add_field(name="Utilisation", value=f"`{usage}`", inline=False)
            
            if isinstance(cmd, commands.Group):
                subcommands = [f"`{subcmd.name}` - {subcmd.description or 'Pas de description'}" for subcmd in cmd.commands]
                if subcommands:
                    embed.add_field(name="Sous-commandes", value="\n".join(subcommands), inline=False)
            
        else:
            # Afficher la liste des commandes par catégorie
            embed = discord.Embed(
                title="Aide du bot",
                description=f"Voici la liste des commandes disponibles. Utilisez `{ctx.prefix}help <commande>` pour plus d'informations sur une commande spécifique.",
                color=discord.Color.blue()
            )
            
            # Regrouper les commandes par cog
            cogs = {}
            for cmd in self.bot.commands:
                if cmd.hidden:
                    continue
                    
                cog_name = cmd.cog.qualified_name if cmd.cog else "Autre"
                if cog_name not in cogs:
                    cogs[cog_name] = []
                cogs[cog_name].append(cmd)
            
            # Ajouter chaque catégorie à l'embed
            for cog_name, cmds in cogs.items():
                commands_list = [f"`{cmd.name}` - {cmd.description or 'Pas de description'}" for cmd in cmds]
                if commands_list:
                    embed.add_field(name=cog_name, value="\n".join(commands_list), inline=False)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Utilities(bot))
