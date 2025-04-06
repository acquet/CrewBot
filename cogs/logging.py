# cogs/logging.py
import discord
from discord.ext import commands
import datetime
from config import MOD_LOGS_CHANNEL_ID, MODERATION_SERVER_ID

class Logging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    async def log_to_mod_server(self, log_type, embed):
        """Envoie un log au serveur de modération"""
        try:
            # Récupérer le serveur de modération
            mod_server = self.bot.get_guild(MODERATION_SERVER_ID)
            if not mod_server:
                return False, "Serveur de modération introuvable"
            
            # Récupérer le canal des logs
            mod_channel = mod_server.get_channel(MOD_LOGS_CHANNEL_ID)
            if not mod_channel:
                return False, "Canal de logs introuvable sur le serveur de modération"

            # Ajouter un identifiant pour le type de log
            if not embed.title.startswith(("📝", "⚠️", "🔨", "🔄", "🚫")):
                if log_type == "info":
                    embed.title = f"📝 {embed.title}"
                elif log_type == "warning":
                    embed.title = f"⚠️ {embed.title}"
                elif log_type == "moderation":
                    embed.title = f"🔨 {embed.title}"
                elif log_type == "change":
                    embed.title = f"🔄 {embed.title}"
                elif log_type == "deletion":
                    embed.title = f"🚫 {embed.title}"
            
            # Envoyer l'embed
            await mod_channel.send(embed=embed)
            return True, "Log envoyé avec succès"
            
        except Exception as e:
            print(f"Erreur lors de l'envoi du log: {e}")
            return False, str(e)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        # Créer un embed pour le nouveau membre
        embed = discord.Embed(
            title="Nouveau membre",
            description=f"{member.mention} a rejoint le serveur.",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now()
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="ID", value=member.id, inline=True)
        embed.add_field(name="Compte créé le", value=member.created_at.strftime("%d/%m/%Y"), inline=True)
        
        # Âge du compte
        account_age = (datetime.datetime.now() - member.created_at).days
        embed.add_field(name="Âge du compte", value=f"{account_age} jours", inline=True)
        
        # Vérifier si le compte est récent (moins de 7 jours)
        if account_age < 7:
            embed.add_field(name="⚠️ Attention", value="Compte récemment créé", inline=False)
        
        # Envoyer au serveur de modération
        await self.log_to_mod_server("info", embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        # Créer un embed pour le membre qui a quitté
        embed = discord.Embed(
            title="Membre parti",
            description=f"{member.mention} a quitté le serveur.",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="ID", value=member.id, inline=True)
        embed.add_field(name="A rejoint le", value=member.joined_at.strftime("%d/%m/%Y") if member.joined_at else "Inconnu", inline=True)
        
        # Durée de présence sur le serveur
        if member.joined_at:
            duration = (datetime.datetime.now() - member.joined_at).days
            embed.add_field(name="Durée de présence", value=f"{duration} jours", inline=True)
        
        # Nombre de rôles
        roles = [role.name for role in member.roles if role.name != "@everyone"]
        embed.add_field(name="Rôles", value=", ".join(roles) if roles else "Aucun", inline=False)
        
        # Envoyer au serveur de modération
        await self.log_to_mod_server("info", embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        # Ignorer les messages du bot
        if message.author.bot:
            return
            
        # Créer un embed pour le message supprimé
        embed = discord.Embed(
            title="Message supprimé",
            description=f"Un message a été supprimé dans {message.channel.mention}",
            color=discord.Color.orange(),
            timestamp=datetime.datetime.now()
        )
        
        embed.set_author(name=f"{message.author.name}#{message.author.discriminator}", icon_url=message.author.display_avatar.url)
        
        # Contenu du message
        if message.content:
            if len(message.content) > 1024:
                content = message.content[:1021] + "..."
            else:
                content = message.content
            embed.add_field(name="Contenu", value=content, inline=False)
        
        # Pièces jointes
        if message.attachments:
            attachments = "\n".join([f"[{attachment.filename}]({attachment.url})" for attachment in message.attachments])
            embed.add_field(name="Pièces jointes", value=attachments, inline=False)
        
        # Ajouter des informations supplémentaires
        embed.add_field(name="Auteur", value=message.author.mention, inline=True)
        embed.add_field(name="ID du message", value=message.id, inline=True)
        embed.add_field(name="Canal", value=message.channel.mention, inline=True)
        
        # Envoyer au serveur de modération
        await self.log_to_mod_server("deletion", embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        # Ignorer les messages du bot et les messages sans modification de contenu
        if before.author.bot or before.content == after.content or not before.content or not after.content:
            return
            
        # Créer un embed pour le message modifié
        embed = discord.Embed(
            title="Message modifié",
            description=f"Un message a été modifié dans {before.channel.mention}",
            color=discord.Color.gold(),
            timestamp=datetime.datetime.now()
        )
        
        embed.set_author(name=f"{before.author.name}#{before.author.discriminator}", icon_url=before.author.display_avatar.url)
        
        # Contenu avant/après
        if len(before.content) > 1024:
            before_content = before.content[:1021] + "..."
        else:
            before_content = before.content
            
        if len(after.content) > 1024:
            after_content = after.content[:1021] + "..."
        else:
            after_content = after.content
            
        embed.add_field(name="Avant", value=before_content or "*Pas de contenu*", inline=False)
        embed.add_field(name="Après", value=after_content or "*Pas de contenu*", inline=False)
        
        # Ajouter des informations supplémentaires
        embed.add_field(name="Auteur", value=before.author.mention, inline=True)
        embed.add_field(name="ID du message", value=before.id, inline=True)
        embed.add_field(name="Canal", value=before.channel.mention, inline=True)
        embed.add_field(name="Lien", value=f"[Aller au message]({after.jump_url})", inline=False)
        
        # Envoyer au serveur de modération
        await self.log_to_mod_server("change", embed)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        # Log des changements de surnom
        if before.nick != after.nick:
            embed = discord.Embed(
                title="Surnom modifié",
                description=f"Le surnom de {after.mention} a été modifié",
                color=discord.Color.blue(),
                timestamp=datetime.datetime.now()
            )
            
            embed.set_thumbnail(url=after.display_avatar.url)
            embed.add_field(name="Avant", value=before.nick or "*Pas de surnom*", inline=True)
            embed.add_field(name="Après", value=after.nick or "*Pas de surnom*", inline=True)
            
            # Envoyer au serveur de modération
            await self.log_to_mod_server("change", embed)
        
        # Log des changements de rôles
        if before.roles != after.roles:
            # Trouver les rôles ajoutés et retirés
            added_roles = [role for role in after.roles if role not in before.roles]
            removed_roles = [role for role in before.roles if role not in after.roles]
            
            if added_roles or removed_roles:
                embed = discord.Embed(
                    title="Rôles modifiés",
                    description=f"Les rôles de {after.mention} ont été modifiés",
                    color=discord.Color.blue(),
                    timestamp=datetime.datetime.now()
                )
                
                embed.set_thumbnail(url=after.display_avatar.url)
                
                if added_roles:
                    embed.add_field(name="Rôles ajoutés", value=", ".join([role.mention for role in added_roles]), inline=False)
                
                if removed_roles:
                    embed.add_field(name="Rôles retirés", value=", ".join([role.mention for role in removed_roles]), inline=False)
                
                # Envoyer au serveur de modération
                await self.log_to_mod_server("change", embed)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        # Log de la création d'un canal
        embed = discord.Embed(
            title="Canal créé",
            description=f"Un nouveau canal a été créé: {channel.mention}",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now()
        )
        
        embed.add_field(name="Nom", value=channel.name, inline=True)
        embed.add_field(name="Type", value=str(channel.type).replace("_", " ").title(), inline=True)
        embed.add_field(name="ID", value=channel.id, inline=True)
        
        if isinstance(channel, discord.CategoryChannel):
            embed.add_field(name="Type", value="Catégorie", inline=True)
        elif isinstance(channel, discord.TextChannel):
            embed.add_field(name="Type", value="Canal de texte", inline=True)
            embed.add_field(name="NSFW", value="Oui" if channel.is_nsfw() else "Non", inline=True)
            embed.add_field(name="Catégorie", value=channel.category.name if channel.category else "Aucune", inline=True)
        elif isinstance(channel, discord.VoiceChannel):
            embed.add_field(name="Type", value="Canal vocal", inline=True)
            embed.add_field(name="Bitrate", value=f"{channel.bitrate//1000} kbps", inline=True)
            embed.add_field(name="Limite d'utilisateurs", value=channel.user_limit or "Illimité", inline=True)
            embed.add_field(name="Catégorie", value=channel.category.name if channel.category else "Aucune", inline=True)
        
        # Envoyer au serveur de modération
        await self.log_to_mod_server("change", embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        # Log de la suppression d'un canal
        embed = discord.Embed(
            title="Canal supprimé",
            description=f"Un canal a été supprimé: #{channel.name}",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        
        embed.add_field(name="ID", value=channel.id, inline=True)
        
        if isinstance(channel, discord.CategoryChannel):
            embed.add_field(name="Type", value="Catégorie", inline=True)
        elif isinstance(channel, discord.TextChannel):
            embed.add_field(name="Type", value="Canal de texte", inline=True)
            embed.add_field(name="Catégorie", value=channel.category.name if channel.category else "Aucune", inline=True)
        elif isinstance(channel, discord.VoiceChannel):
            embed.add_field(name="Type", value="Canal vocal", inline=True)
            embed.add_field(name="Catégorie", value=channel.category.name if channel.category else "Aucune", inline=True)
        
        # Envoyer au serveur de modération
        await self.log_to_mod_server("deletion", embed)

    # cogs/logging.py (suite)
    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        # Log de la création d'un rôle
        embed = discord.Embed(
            title="Rôle créé",
            description=f"Un nouveau rôle a été créé: {role.mention}",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now()
        )
        
        embed.add_field(name="Nom", value=role.name, inline=True)
        embed.add_field(name="ID", value=role.id, inline=True)
        embed.add_field(name="Couleur", value=str(role.color), inline=True)
        embed.add_field(name="Position", value=role.position, inline=True)
        embed.add_field(name="Mentionnable", value="Oui" if role.mentionable else "Non", inline=True)
        embed.add_field(name="Affiché séparément", value="Oui" if role.hoist else "Non", inline=True)
        
        # Envoyer au serveur de modération
        await self.log_to_mod_server("change", embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        # Log de la suppression d'un rôle
        embed = discord.Embed(
            title="Rôle supprimé",
            description=f"Un rôle a été supprimé: {role.name}",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        
        embed.add_field(name="ID", value=role.id, inline=True)
        embed.add_field(name="Couleur", value=str(role.color), inline=True)
        embed.add_field(name="Position", value=role.position, inline=True)
        
        # Envoyer au serveur de modération
        await self.log_to_mod_server("deletion", embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # Ignorer les mises à jour sans changement de canal
        if before.channel == after.channel:
            return
            
        if before.channel is None and after.channel is not None:
            # Membre a rejoint un canal vocal
            embed = discord.Embed(
                title="Canal vocal rejoint",
                description=f"{member.mention} a rejoint un canal vocal",
                color=discord.Color.green(),
                timestamp=datetime.datetime.now()
            )
            
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="Canal", value=after.channel.name, inline=True)
            
            # Envoyer au serveur de modération
            await self.log_to_mod_server("info", embed)
            
        elif before.channel is not None and after.channel is None:
            # Membre a quitté un canal vocal
            embed = discord.Embed(
                title="Canal vocal quitté",
                description=f"{member.mention} a quitté un canal vocal",
                color=discord.Color.red(),
                timestamp=datetime.datetime.now()
            )
            
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="Canal", value=before.channel.name, inline=True)
            
            # Envoyer au serveur de modération
            await self.log_to_mod_server("info", embed)
            
        else:
            # Membre a changé de canal vocal
            embed = discord.Embed(
                title="Changement de canal vocal",
                description=f"{member.mention} a changé de canal vocal",
                color=discord.Color.blue(),
                timestamp=datetime.datetime.now()
            )
            
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="Ancien canal", value=before.channel.name, inline=True)
            embed.add_field(name="Nouveau canal", value=after.channel.name, inline=True)
            
            # Envoyer au serveur de modération
            await self.log_to_mod_server("info", embed)

async def setup(bot):
    await bot.add_cog(Logging(bot))
