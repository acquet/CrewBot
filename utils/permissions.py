# utils/permissions.py
from config import MOD_ROLE_ID, ADMIN_ROLE_ID

def is_mod_or_admin(member):
    """
    Vérifie si un membre est un modérateur ou un administrateur
    """
    if member.guild_permissions.administrator:
        return True
        
    for role in member.roles:
        if role.id == MOD_ROLE_ID or role.id == ADMIN_ROLE_ID:
            return True
    
    return False

def get_permission_level(member):
    """
    Obtient le niveau de permission d'un membre
    0 = Utilisateur normal
    1 = Modérateur
    2 = Administrateur
    """
    if member.guild_permissions.administrator:
        return 2
        
    for role in member.roles:
        if role.id == ADMIN_ROLE_ID:
            return 2
        elif role.id == MOD_ROLE_ID:
            return 1
    
    return 0
