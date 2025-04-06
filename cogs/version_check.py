# cogs/version_check.py
from packaging import version
import discord
from discord.ext import commands
import asyncio
import datetime
from packaging import version

from config import VERSION, ADMIN_SERVER_ID, VERSION_CHANNEL_ID

class VersionCheck(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.version = VERSION
        self.up_to_date = None  # None = pas encore vérifié, True = à jour, False = obsolète
        self.last_check = None
        self.bot.loop.create_task(self.check_version_on_startup())
    
    async def check_version_on_startup(self):
        """Vérifier la version au démarrage après un délai pour s'assurer que le bot est prêt"""
        await self.bot.wait_until_ready()
        # Attendre 10 secondes supplémentaires pour s'assurer que toutes les connexions sont établies
        await asyncio.sleep(10)
        await self.check_version()
    
    async def check_version(self):
        """Vérifie si la version du bot correspond à celle indiquée dans le canal de version"""
        try:
            # Obtenir le serveur d'administration
            admin_server = self.bot.get_guild(ADMIN_SERVER_ID)
            if not admin_server:
                print(f"⚠️ Serveur d'administration (ID: {ADMIN_SERVER_ID}) non trouvé.")
                self.up_to_date = False
                return
            
            # Obtenir le canal de version
            version_channel = admin_server.get_channel(VERSION_CHANNEL_ID)
            if not version_channel:
                print(f"⚠️ Canal de version (ID: {VERSION_CHANNEL_ID}) non trouvé.")
                self.up_to_date = False
                return
            
            # Récupérer le dernier message du canal
            try:
                messages = [message async for message in version_channel.history(limit=1)]
                if not messages:
                    print(f"⚠️ Aucun message trouvé dans le canal de version.")
                    self.up_to_date = False
                    return
                
                latest_message = messages[0]
                latest_version = latest_message.content.strip()
                
                # Comparer les versions
                try:
                    current_version = version.parse(self.version)
                    server_version = version.parse(latest_version)
                    
                    if current_version >= server_version:
                        print(f"✅ Bot à jour (version {self.version})")
                        self.up_to_date = True
                    else:
                        print(f"⚠️ Bot obsolète (version {self.version}, dernière version {latest_version})")
                        self.up_to_date = False
                        
                        # Envoyer une alerte aux propriétaires du bot
                        for owner_id in self.bot.owner_ids:
                            owner = self.bot.get_user(owner_id)
                            if owner:
                                try:
                                    embed = discord.Embed(
                                        title="⚠️ Bot obsolète",
                                        description=f"Votre bot utilise la version {self.version}, mais la dernière version est {latest_version}.",
                                        color=discord.Color.red(),
                                        timestamp=datetime.datetime.now()
                                    )
                                    embed.add_field(name="Action requise", value="Veuillez mettre à jour votre bot dès que possible.", inline=False)
                                    await owner.send(embed=embed)
                                except:
                                    pass
                except:
                    print(f"⚠️ Erreur lors de la comparaison des versions: {self.version} vs {latest_version}")
                    self.up_to_date = False
            
            except Exception as e:
                print(f"⚠️ Erreur lors de la récupération des messages: {e}")
                self.up_to_date = False
            
            self.last_check = datetime.datetime.now()
        
        except Exception as e:
            print(f"⚠️ Erreur lors de la vérification de version: {e}")
            self.up_to_date = False
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Message de connexion avec information de version"""
        print(f"Bot connecté en tant que {self.bot.user.name} (version {self.version})")

    # cogs/version_check.py (suite)
    @commands.hybrid_command(name="version", description="Affiche la version actuelle du bot et vérifie les mises à jour")
    async def version_command(self, ctx):
        """Affiche la version actuelle du bot et vérifie les mises à jour"""
        # Vérifier la version en temps réel
        await self.check_version()
        
        # Créer l'embed
        embed = discord.Embed(
            title=f"{self.bot.user.name} - Informations de version",
            color=discord.Color.blue() if self.up_to_date else discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        
        embed.add_field(name="Version actuelle", value=self.version, inline=False)
        
        if self.up_to_date is True:
            embed.add_field(name="Statut", value="✅ À jour", inline=False)
        elif self.up_to_date is False:
            embed.add_field(name="Statut", value="⚠️ Une version plus récente est disponible", inline=False)
        else:
            embed.add_field(name="Statut", value="❓ Impossible de vérifier les mises à jour", inline=False)
        
        if self.last_check:
            embed.set_footer(text=f"Dernière vérification: {self.last_check.strftime('%Y-%m-%d %H:%M:%S')}")
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="changelog", description="Affiche les dernières modifications du bot")
    async def changelog(self, ctx):
        """Tente de récupérer et d'afficher le changelog à partir du serveur admin"""
        try:
            # Obtenir le serveur d'administration
            admin_server = self.bot.get_guild(ADMIN_SERVER_ID)
            if not admin_server:
                return await ctx.send("⚠️ Impossible de récupérer le changelog: serveur d'administration non trouvé.")
            
            # Chercher un canal nommé "changelog"
            changelog_channel = discord.utils.get(admin_server.text_channels, name="changelog")
            if not changelog_channel:
                return await ctx.send("⚠️ Impossible de récupérer le changelog: canal non trouvé.")
            
            # Récupérer les 5 derniers messages
            messages = [message async for message in changelog_channel.history(limit=5)]
            if not messages:
                return await ctx.send("⚠️ Aucune information de changelog trouvée.")
            
            # Créer l'embed
            embed = discord.Embed(
                title=f"{self.bot.user.name} - Dernières mises à jour",
                description="Voici les dernières modifications apportées au bot:",
                color=discord.Color.blue(),
                timestamp=datetime.datetime.now()
            )
            
            for msg in messages:
                # Extraire la version depuis le contenu (si format: "v1.0.0 - Description")
                content = msg.content
                if " - " in content and content.startswith(("v", "V")):
                    version, description = content.split(" - ", 1)
                    embed.add_field(name=version, value=description, inline=False)
                else:
                    # Ajouter comme entrée générique
                    created_at = msg.created_at.strftime("%Y-%m-%d")
                    embed.add_field(name=f"Mise à jour du {created_at}", value=content, inline=False)
            
            await ctx.send(embed=embed)
        
        except Exception as e:
            await ctx.send(f"⚠️ Erreur lors de la récupération du changelog: {e}")
    
    @commands.is_owner()
    @commands.hybrid_command(name="force_version_check", description="Force une vérification de version")
    async def force_version_check(self, ctx):
        """Force une vérification de version (réservé aux propriétaires du bot)"""
        await ctx.defer()  # Indique que la commande peut prendre du temps
        
        previous_status = self.up_to_date
        await self.check_version()
        
        if self.up_to_date is True:
            await ctx.send("✅ Vérification terminée: le bot est à jour.")
        elif self.up_to_date is False:
            await ctx.send("⚠️ Vérification terminée: le bot n'est pas à jour.")
        else:
            await ctx.send("❓ Vérification terminée: impossible de déterminer le statut de mise à jour.")
        
        if previous_status != self.up_to_date:
            await ctx.send("ℹ️ Le statut a changé depuis la dernière vérification.")

async def setup(bot):
    await bot.add_cog(VersionCheck(bot))
