# utils/embeds.py
import discord
import datetime

def create_mod_action_embed(action_type, member, moderator, reason, warning_count=None, duration=None):
    """
    Crée un embed pour une action de modération
    """
    colors = {
        "Avertissement": discord.Color.gold(),
        "Expulsion": discord.Color.orange(),
        "Bannissement": discord.Color.red(),
        "Timeout": discord.Color.dark_orange(),
        "Suppression d'avertissement": discord.Color.green(),
        "Débannissement": discord.Color.green()
    }
    
    emojis = {
        "Avertissement": "⚠️",
        "Expulsion": "👢",
        "Bannissement": "🔨",
        "Timeout": "⏱️",
        "Suppression d'avertissement": "🔄",
        "Débannissement": "🔓"
    }
    
    color = colors.get(action_type, discord.Color.blue())
    emoji = emojis.get(action_type, "🛡️")
    
    embed = discord.Embed(
        title=f"{emoji} {action_type}",
        description=f"{member.mention} a reçu un {action_type.lower()}",
        color=color,
        timestamp=datetime.datetime.now()
    )
    
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Utilisateur", value=f"{member.name} (ID: {member.id})", inline=True)
    embed.add_field(name="Modérateur", value=moderator.mention, inline=True)
    embed.add_field(name="Raison", value=reason, inline=False)
    
    if warning_count is not None:
        embed.add_field(name="Nombre d'avertissements", value=warning_count, inline=True)
    
    if duration is not None:
        embed.add_field(name="Durée", value=duration, inline=True)
    
    return embed

def create_report_embed(action_type, user, moderator, reason, duration=None):
    """
    Crée un embed pour un rapport envoyé au serveur de modération
    """
    colors = {
        "Avertissement": discord.Color.gold(),
        "Expulsion": discord.Color.orange(),
        "Bannissement": discord.Color.red(),
        "Timeout": discord.Color.dark_orange(),
        "Suppression d'avertissement": discord.Color.green(),
        "Débannissement": discord.Color.green(),
        "Signalement": discord.Color.purple(),
        "Suppression de messages": discord.Color.light_gray()
    }
    
    emojis = {
        "Avertissement": "⚠️",
        "Expulsion": "👢",
        "Bannissement": "🔨",
        "Timeout": "⏱️",
        "Suppression d'avertissement": "🔄",
        "Débannissement": "🔓",
        "Signalement": "🚨",
        "Suppression de messages": "🗑️"
    }
    
    color = colors.get(action_type, discord.Color.blue())
    emoji = emojis.get(action_type, "🛡️")
    
    embed = discord.Embed(
        title=f"{emoji} Rapport: {action_type}",
        color=color,
        timestamp=datetime.datetime.now()
    )
    
    if user:
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Utilisateur", value=f"{user.name} (ID: {user.id})", inline=True)
    
    embed.add_field(name="Modérateur", value=f"{moderator.name} (ID: {moderator.id})", inline=True)
    embed.add_field(name="Raison", value=reason, inline=False)
    
    if duration:
        embed.add_field(name="Durée", value=duration, inline=True)
    
    embed.set_footer(text=f"Serveur: {moderator.guild.name} | ID: {moderator.guild.id}")
    
    return embed
