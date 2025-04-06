# cogs/invites.py
import json
import discord
from discord.ext import commands
import datetime
import sqlite3
import json
from typing import Dict, List, Optional

from config import MODERATION_SERVER_ID

class InviteTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        from utils.db_handler import DatabaseHandler
        self.db_handler = DatabaseHandler()  # Instance unique
        self.invites: Dict[int, Dict[str, discord.Invite]] = {}
        # Structure: {guild_id: {invite_code: invite_obj}}

    def cog_unload(self):
        """Ferme la connexion à la base de données lors du déchargement du cog"""
        if hasattr(self, 'db_handler'):
            self.db_handler.close()
        
    def setup_database(self):
        """Configure la base de données pour les invitations"""
        self.conn = sqlite3.connect('data/database.db')
        self.cursor = self.conn.cursor()
        
        # Table pour suivre qui a invité qui
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS invite_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER NOT NULL,
            inviter_id INTEGER NOT NULL,
            invited_id INTEGER NOT NULL,
            invite_code TEXT NOT NULL,
            join_time DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Table pour les statistiques d'invitation par utilisateur
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS invite_stats (
            user_id INTEGER NOT NULL,
            server_id INTEGER NOT NULL,
            invites_regular INTEGER DEFAULT 0,
            invites_left INTEGER DEFAULT 0,
            invites_fake INTEGER DEFAULT 0,
            invites_bonus INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, server_id)
        )
        ''')
        
        self.conn.commit()
    
    async def fetch_invites(self):
        """Récupère toutes les invitations pour tous les serveurs"""
        for guild in self.bot.guilds:
            try:
                # Vérifier les permissions
                if guild.me.guild_permissions.manage_guild:
                    # Récupérer les invitations
                    guild_invites = await guild.invites()
                    self.invites[guild.id] = {invite.code: invite for invite in guild_invites}
            except discord.Forbidden:
                print(f"Impossible de récupérer les invitations pour le serveur {guild.name} (ID: {guild.id})")
            except Exception as e:
                print(f"Erreur lors de la récupération des invitations pour {guild.name}: {e}")
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Charge les invitations au démarrage"""
        await self.fetch_invites()
        print(f"Invitations chargées pour {len(self.invites)} serveurs")
    
    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """Charge les invitations pour un nouveau serveur"""
        try:
            if guild.me.guild_permissions.manage_guild:
                guild_invites = await guild.invites()
                self.invites[guild.id] = {invite.code: invite for invite in guild_invites}
                print(f"Invitations chargées pour le nouveau serveur {guild.name}")
        except Exception as e:
            print(f"Erreur lors du chargement des invitations pour {guild.name}: {e}")
    
    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        """Met à jour la cache lorsqu'une invitation est créée"""
        try:
            if invite.guild.id not in self.invites:
                self.invites[invite.guild.id] = {}
            self.invites[invite.guild.id][invite.code] = invite
            print(f"Nouvelle invitation créée: {invite.code} par {invite.inviter.name}")
        except Exception as e:
            print(f"Erreur lors de la mise à jour d'une nouvelle invitation: {e}")
    
    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        """Met à jour la cache lorsqu'une invitation est supprimée"""
        try:
            if invite.guild.id in self.invites and invite.code in self.invites[invite.guild.id]:
                del self.invites[invite.guild.id][invite.code]
                print(f"Invitation supprimée: {invite.code}")
        except Exception as e:
            print(f"Erreur lors de la suppression d'une invitation: {e}")
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Détermine quelle invitation a été utilisée lorsqu'un membre rejoint"""
        guild = member.guild
        
        # Ignorer les bots
        if member.bot:
            return
        
        try:
            # Vérifier les permissions
            if not guild.me.guild_permissions.manage_guild:
                return
                
            # Récupérer les anciennes invitations
            old_invites = self.invites.get(guild.id, {})
            
            # Récupérer les nouvelles invitations
            new_invites = await guild.invites()
            new_invites_dict = {invite.code: invite for invite in new_invites}
            
            # Mettre à jour le cache
            self.invites[guild.id] = new_invites_dict
            
            # Trouver l'invitation utilisée
            inviter = None
            invite_code = None
            
            for invite_code, invite in new_invites_dict.items():
                if invite_code in old_invites:
                    old_invite = old_invites[invite_code]
                    if invite.uses > old_invite.uses:
                        inviter = invite.inviter
                        invite_code = invite.code
                        break
            
            # Si l'invitation n'a pas été trouvée (peut arriver si c'est une invitation temporaire ou nouvelle)
            if not inviter and len(new_invites) > 0:
                # Chercher une nouvelle invitation avec au moins 1 utilisation
                for invite in new_invites:
                    if invite.uses == 1 and invite.created_at.timestamp() > (datetime.datetime.now() - datetime.timedelta(minutes=5)).timestamp():
                        inviter = invite.inviter
                        invite_code = invite.code
                        break
            
            # Si nous avons trouvé l'invitation
            if inviter and invite_code:
                # Enregistrer l'invitation dans la base de données
                self.cursor.execute('''
                INSERT INTO invite_tracking (server_id, inviter_id, invited_id, invite_code)
                VALUES (?, ?, ?, ?)
                ''', (guild.id, inviter.id, member.id, invite_code))
                
                # Mettre à jour les statistiques de l'inviteur
                self.cursor.execute('''
                INSERT INTO invite_stats (user_id, server_id, invites_regular)
                VALUES (?, ?, 1)
                ON CONFLICT(user_id, server_id) DO UPDATE SET
                invites_regular = invites_regular + 1
                ''', (inviter.id, guild.id))
                
                self.conn.commit()
                
                print(f"{member.name} a rejoint via l'invitation de {inviter.name} (code: {invite_code})")
                
                # Envoyer un message de bienvenue
                welcome_channel_id = self.get_welcome_channel_id(guild.id)
                if welcome_channel_id:
                    welcome_channel = guild.get_channel(welcome_channel_id)
                    if welcome_channel:
                        # Format du message personnalisable
                        message = f"🎉 Bienvenue {member.mention} sur **{guild.name}** !\n"
                        message += f"Invité par : {inviter.mention}\n"
                        
                        # Récupérer les stats d'invitation de l'inviteur
                        invite_count = self.get_invite_count(inviter.id, guild.id)
                        message += f"C'est sa {invite_count}e invitation !"
                        
                        await welcome_channel.send(message)
                
                # Envoyer au serveur de modération
                await self.send_to_mod_server(
                    member=member,
                    inviter=inviter,
                    invite_code=invite_code
                )
            else:
                print(f"{member.name} a rejoint, mais l'invitation n'a pas pu être déterminée.")
        
        except Exception as e:
            print(f"Erreur lors du suivi de l'invitation pour {member.name}: {e}")
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Met à jour les statistiques quand un membre quitte"""
        guild = member.guild
        
        # Ignorer les bots
        if member.bot:
            return
        
        try:
            # Trouver qui l'a invité
            self.cursor.execute('''
            SELECT inviter_id FROM invite_tracking
            WHERE server_id = ? AND invited_id = ?
            ORDER BY join_time DESC LIMIT 1
            ''', (guild.id, member.id))
            
            row = self.cursor.fetchone()
            if row:
                inviter_id = row[0]
                
                # Mettre à jour les statistiques de l'inviteur
                self.cursor.execute('''
                UPDATE invite_stats
                SET invites_left = invites_left + 1
                WHERE user_id = ? AND server_id = ?
                ''', (inviter_id, guild.id))
                
                self.conn.commit()
                
                print(f"{member.name} a quitté, réduisant les invitations actives de l'utilisateur {inviter_id}")
        
        except Exception as e:
            print(f"Erreur lors de la mise à jour des statistiques de départ pour {member.name}: {e}")
    
    def get_welcome_channel_id(self, guild_id):
        """Récupère l'ID du canal de bienvenue à partir de la configuration"""
        try:
            self.cursor.execute('''
            SELECT config_json FROM server_configs
            WHERE server_id = ?
            ''', (guild_id,))
            
            row = self.cursor.fetchone()
            if row:
                config = json.loads(row[0])
                return int(config.get('welcome_channel_id', 0))
        except:
            pass
        return None
    
    def get_invite_count(self, user_id, guild_id):
        """Récupère le nombre total d'invitations d'un utilisateur"""
        try:
            self.cursor.execute('''
            SELECT invites_regular, invites_bonus, invites_fake, invites_left
            FROM invite_stats
            WHERE user_id = ? AND server_id = ?
            ''', (user_id, guild_id))
            
            row = self.cursor.fetchone()
            if row:
                regular, bonus, fake, left = row
                return (regular + bonus) - (fake + left)
            return 0
        except:
            return 0
    
    async def send_to_mod_server(self, member, inviter, invite_code):
        """Envoie un rapport d'invitation au serveur de modération"""
        try:
            # Récupérer le serveur de modération
            mod_server = self.bot.get_guild(MODERATION_SERVER_ID)
            if not mod_server:
                return
                
            # Récupérer le canal des logs (utiliser MOD_LOGS_CHANNEL_ID de config.py)
            from config import MOD_LOGS_CHANNEL_ID
            mod_channel = mod_server.get_channel(MOD_LOGS_CHANNEL_ID)
            if not mod_channel:
                return
            
            # Créer l'embed
            embed = discord.Embed(
                title="Nouveau membre rejoint",
                description=f"{member.mention} a rejoint {member.guild.name}",
                color=discord.Color.green(),
                timestamp=datetime.datetime.now()
            )
            
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="Membre", value=f"{member.name} (ID: {member.id})", inline=True)
            embed.add_field(name="Invité par", value=f"{inviter.name} (ID: {inviter.id})", inline=True)
            embed.add_field(name="Code d'invitation", value=invite_code, inline=True)
            
            # Compte d'invitations de l'inviteur
            invite_count = self.get_invite_count(inviter.id, member.guild.id)
            embed.add_field(name="Total d'invitations", value=invite_count, inline=True)
            
            # Âge du compte
            account_age = (datetime.datetime.now() - member.created_at).days
            embed.add_field(name="Âge du compte", value=f"{account_age} jours", inline=True)
            
            # Vérifier si le compte est récent (moins de 7 jours)
            if account_age < 7:
                embed.add_field(name="⚠️ Attention", value="Compte récemment créé", inline=False)
            
            await mod_channel.send(embed=embed)
            
        except Exception as e:
            print(f"Erreur lors de l'envoi du rapport d'invitation: {e}")
    
    @commands.hybrid_command(name="invites", description="Affiche vos statistiques d'invitation ou celles d'un utilisateur")
    async def invites(self, ctx, member: Optional[discord.Member] = None):
        """Affiche les statistiques d'invitation d'un utilisateur"""
        member = member or ctx.author
        
        try:
            self.cursor.execute('''
            SELECT invites_regular, invites_bonus, invites_fake, invites_left
            FROM invite_stats
            WHERE user_id = ? AND server_id = ?
            ''', (member.id, ctx.guild.id))
            
            row = self.cursor.fetchone()
            if row:
                regular, bonus, fake, left = row
                total = (regular + bonus) - (fake + left)
                
                embed = discord.Embed(
                    title=f"Statistiques d'invitation de {member.display_name}",
                    color=member.color,
                    timestamp=datetime.datetime.now()
                )
                
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.add_field(name="Total", value=total, inline=False)
                embed.add_field(name="Régulières", value=regular, inline=True)
                embed.add_field(name="Bonus", value=bonus, inline=True)
                embed.add_field(name="Parties", value=left, inline=True)
                embed.add_field(name="Fausses", value=fake, inline=True)
                
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"{member.mention} n'a pas encore invité de membres.")
        
        except Exception as e:
            await ctx.send(f"Erreur lors de la récupération des statistiques d'invitation: {e}")
    
    @commands.hybrid_command(name="add_invites", description="Ajoute des invitations bonus à un utilisateur")
    @commands.has_permissions(administrator=True)
    async def add_invites(self, ctx, member: discord.Member, amount: int, *, reason: str = "Pas de raison spécifiée"):
        """Ajoute des invitations bonus à un utilisateur"""
        if amount <= 0:
            return await ctx.send("Le nombre d'invitations doit être supérieur à 0.")
        
        try:
            # Vérifier si l'utilisateur a déjà des stats
            self.cursor.execute('''
            SELECT COUNT(*) FROM invite_stats
            WHERE user_id = ? AND server_id = ?
            ''', (member.id, ctx.guild.id))
            
            if self.cursor.fetchone()[0] == 0:
                # Créer une nouvelle entrée
                self.cursor.execute('''
                INSERT INTO invite_stats (user_id, server_id, invites_bonus)
                VALUES (?, ?, ?)
                ''', (member.id, ctx.guild.id, amount))
            else:
                # Mettre à jour l'entrée existante
                self.cursor.execute('''
                UPDATE invite_stats
                SET invites_bonus = invites_bonus + ?
                WHERE user_id = ? AND server_id = ?
                ''', (amount, member.id, ctx.guild.id))
            
            self.conn.commit()
            
            await ctx.send(f"✅ {amount} invitation(s) bonus ont été ajoutées à {member.mention}.")
            
            # Récupérer le nouveau total
            total = self.get_invite_count(member.id, ctx.guild.id)
            
            # Envoyer un message privé à l'utilisateur
            try:
                embed = discord.Embed(
                    title="Invitations bonus reçues",
                    description=f"Vous avez reçu {amount} invitation(s) bonus sur {ctx.guild.name}",
                    color=discord.Color.gold(),
                    timestamp=datetime.datetime.now()
                )
                
                embed.add_field(name="Raison", value=reason, inline=False)
                embed.add_field(name="Total actuel", value=total, inline=True)
                embed.add_field(name="Administrateur", value=ctx.author.name, inline=True)
                
                await member.send(embed=embed)
            except:
                await ctx.send("Je n'ai pas pu envoyer un message privé à l'utilisateur.")
        
        except Exception as e:
            await ctx.send(f"Erreur lors de l'ajout des invitations: {e}")
    
    @commands.hybrid_command(name="remove_invites", description="Retire des invitations à un utilisateur")
    @commands.has_permissions(administrator=True)
    async def remove_invites(self, ctx, member: discord.Member, amount: int, *, reason: str = "Pas de raison spécifiée"):
        """Retire des invitations à un utilisateur"""
        if amount <= 0:
            return await ctx.send("Le nombre d'invitations doit être supérieur à 0.")
        
        try:
            # Vérifier si l'utilisateur a déjà des stats
            self.cursor.execute('''
            SELECT invites_regular, invites_bonus FROM invite_stats
            WHERE user_id = ? AND server_id = ?
            ''', (member.id, ctx.guild.id))
            
            row = self.cursor.fetchone()
            if row:
                regular, bonus = row
                
                # Si les invitations bonus sont suffisantes
                if bonus >= amount:
                    self.cursor.execute('''
                    UPDATE invite_stats
                    SET invites_bonus = invites_bonus - ?
                    WHERE user_id = ? AND server_id = ?
                    ''', (amount, member.id, ctx.guild.id))
                # Sinon, augmenter les fausses invitations
                else:
                    self.cursor.execute('''
                    UPDATE invite_stats
                    SET invites_fake = invites_fake + ?
                    WHERE user_id = ? AND server_id = ?
                    ''', (amount, member.id, ctx.guild.id))
                
                self.conn.commit()
                
                await ctx.send(f"✅ {amount} invitation(s) ont été retirées à {member.mention}.")
                
                # Récupérer le nouveau total
                total = self.get_invite_count(member.id, ctx.guild.id)
                
                # Envoyer un message privé à l'utilisateur
                try:
                    embed = discord.Embed(
                        title="Invitations retirées",
                        description=f"Vous avez perdu {amount} invitation(s) sur {ctx.guild.name}",
                        color=discord.Color.red(),
                        timestamp=datetime.datetime.now()
                    )
                    
                    embed.add_field(name="Raison", value=reason, inline=False)
                    embed.add_field(name="Total actuel", value=total, inline=True)
                    embed.add_field(name="Administrateur", value=ctx.author.name, inline=True)
                    
                    await member.send(embed=embed)
                except:
                    await ctx.send("Je n'ai pas pu envoyer un message privé à l'utilisateur.")
            else:
                # L'utilisateur n'a pas encore d'invitations
                await ctx.send(f"{member.mention} n'a pas encore d'invitations à retirer.")
        
        except Exception as e:
            await ctx.send(f"Erreur lors du retrait des invitations: {e}")
    
    @commands.hybrid_command(name="invitestop", description="Affiche le classement des membres ayant le plus d'invitations")
    async def invitestop(self, ctx, count: int = 10):
        """Affiche le classement des membres par nombre d'invitations"""
        if count < 1 or count > 25:
            return await ctx.send("Le nombre doit être entre 1 et 25.")
        
        try:
            self.cursor.execute('''
            SELECT user_id, invites_regular, invites_bonus, invites_fake, invites_left
            FROM invite_stats
            WHERE server_id = ?
            ''', (ctx.guild.id,))
            
            rows = self.cursor.fetchall()
            
            # Calculer le total pour chaque membre
            invite_totals = []
            for user_id, regular, bonus, fake, left in rows:
                total = (regular + bonus) - (fake + left)
                invite_totals.append((user_id, total))
            
            # Trier par nombre total d'invitations
            invite_totals.sort(key=lambda x: x[1], reverse=True)
            
            # Créer l'embed
            embed = discord.Embed(
                title=f"Top {min(count, len(invite_totals))} des inviteurs",
                description=f"Classement des membres par invitations sur {ctx.guild.name}",
                color=discord.Color.gold(),
                timestamp=datetime.datetime.now()
            )
            
            # Ajouter les membres au classement
            for i, (user_id, total) in enumerate(invite_totals[:count], 1):
                member = ctx.guild.get_member(user_id)
                member_name = member.display_name if member else f"Utilisateur {user_id}"
                embed.add_field(name=f"{i}. {member_name}", value=f"{total} invitation(s)", inline=False)
            
            await ctx.send(embed=embed)
        
        except Exception as e:
            await ctx.send(f"Erreur lors de la récupération du classement: {e}")
    
    @commands.hybrid_command(name="inviter", description="Affiche qui a invité un membre")
    async def inviter(self, ctx, member: discord.Member):
        """Affiche qui a invité un membre spécifique"""
        try:
            self.cursor.execute('''
            SELECT inviter_id, invite_code, join_time FROM invite_tracking
            WHERE server_id = ? AND invited_id = ?
            ORDER BY join_time DESC LIMIT 1
            ''', (ctx.guild.id, member.id))
            
            row = self.cursor.fetchone()
            if row:
                inviter_id, invite_code, join_time = row
                inviter = ctx.guild.get_member(inviter_id)
                
                embed = discord.Embed(
                    title=f"Information d'invitation pour {member.display_name}",
                    color=member.color,
                    timestamp=datetime.datetime.now()
                )
                
                embed.set_thumbnail(url=member.display_avatar.url)
                
                if inviter:
                    embed.add_field(name="Invité par", value=f"{inviter.mention} ({inviter.name})", inline=True)
                else:
                    embed.add_field(name="Invité par", value=f"Utilisateur inconnu (ID: {inviter_id})", inline=True)
                
                embed.add_field(name="Code d'invitation", value=invite_code, inline=True)
                embed.add_field(name="Date d'arrivée", value=join_time, inline=False)
                
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"Je ne sais pas qui a invité {member.mention}.")
        
        except Exception as e:
            await ctx.send(f"Erreur lors de la récupération de l'inviteur: {e}")
    
    def cog_unload(self):
        """Ferme la connexion à la base de données lors du déchargement du cog"""
        self.conn.close()

async def setup(bot):
    await bot.add_cog(InviteTracker(bot))
