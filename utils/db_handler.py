# utils/db_handler.py
import sqlite3
import os
import json
from typing import List, Dict, Any, Optional, Tuple

class DatabaseHandler:
    def __init__(self, db_path: str = 'data/database.db'):
        """Initialise la connexion à la base de données"""
        # Créer le dossier si nécessaire
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.setup_database()
    
    def setup_database(self):
        """Configure les tables nécessaires"""
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
        
        # Créer la table pour les configurations du serveur
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS server_configs (
            server_id INTEGER PRIMARY KEY,
            config_json TEXT
        )
        ''')
        
        # Créer la table pour le système de niveaux
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS levels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            server_id INTEGER NOT NULL,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 0,
            last_message_time DATETIME,
            UNIQUE(user_id, server_id)
        )
        ''')
        
        # Créer la table pour les rappels
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            server_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            message TEXT,
            remind_time DATETIME NOT NULL,
            created_time DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        self.conn.commit()
    
    # Méthodes pour les avertissements
    def add_warning(self, user_id: int, server_id: int, moderator_id: int, reason: str) -> int:
        """Ajoute un avertissement et retourne l'ID de l'avertissement"""
        self.cursor.execute('''
        INSERT INTO warnings (user_id, server_id, moderator_id, reason)
        VALUES (?, ?, ?, ?)
        ''', (user_id, server_id, moderator_id, reason))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_warnings(self, user_id: int, server_id: int) -> List[Dict[str, Any]]:
        """Récupère tous les avertissements d'un utilisateur"""
        self.cursor.execute('''
        SELECT id, moderator_id, reason, timestamp FROM warnings 
        WHERE user_id = ? AND server_id = ?
        ORDER BY timestamp DESC
        ''', (user_id, server_id))
        
        return [dict(row) for row in self.cursor.fetchall()]
    
    def get_warning_count(self, user_id: int, server_id: int) -> int:
        """Récupère le nombre d'avertissements d'un utilisateur"""
        self.cursor.execute('''
        SELECT COUNT(*) FROM warnings 
        WHERE user_id = ? AND server_id = ?
        ''', (user_id, server_id))
        
        return self.cursor.fetchone()[0]
    
    def remove_warning(self, warning_id: int, user_id: int, server_id: int) -> bool:
        """Supprime un avertissement et retourne True si réussi"""
        self.cursor.execute('''
        DELETE FROM warnings 
        WHERE id = ? AND user_id = ? AND server_id = ?
        ''', (warning_id, user_id, server_id))
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def clear_warnings(self, user_id: int, server_id: int) -> int:
        """Supprime tous les avertissements d'un utilisateur et retourne le nombre supprimé"""
        self.cursor.execute('''
        DELETE FROM warnings 
        WHERE user_id = ? AND server_id = ?
        ''', (user_id, server_id))
        self.conn.commit()
        return self.cursor.rowcount
    
    # Méthodes pour les actions de modération
    def add_mod_action(self, action_type: str, user_id: int, server_id: int, moderator_id: int, reason: str, duration: Optional[int] = None) -> int:
        """Ajoute une action de modération et retourne l'ID de l'action"""
        self.cursor.execute('''
        INSERT INTO mod_actions (action_type, user_id, server_id, moderator_id, reason, duration)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (action_type, user_id, server_id, moderator_id, reason, duration))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_mod_actions(self, user_id: int, server_id: int, limit: int = 15) -> List[Dict[str, Any]]:
        """Récupère les actions de modération d'un utilisateur"""
        self.cursor.execute('''
        SELECT action_type, moderator_id, reason, timestamp, duration
        FROM mod_actions 
        WHERE user_id = ? AND server_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
        ''', (user_id, server_id, limit))
        
        return [dict(row) for row in self.cursor.fetchall()]
    
    # Méthodes pour la configuration du serveur
    def get_server_config(self, server_id: int) -> Dict[str, Any]:
        """Récupère la configuration d'un serveur"""
        self.cursor.execute('''
        SELECT config_json FROM server_configs 
        WHERE server_id = ?
        ''', (server_id,))
        
        row = self.cursor.fetchone()
        if row:
            return json.loads(row[0])
        return {}
    
    def update_server_config(self, server_id: int, config: Dict[str, Any]) -> None:
        """Met à jour la configuration d'un serveur"""
        config_json = json.dumps(config)
        self.cursor.execute('''
        INSERT OR REPLACE INTO server_configs (server_id, config_json)
        VALUES (?, ?)
        ''', (server_id, config_json))
        self.conn.commit()
    
    # Méthodes pour le système de niveaux
    def add_xp(self, user_id: int, server_id: int, xp_amount: int) -> Tuple[int, int, bool]:
        """
        Ajoute de l'XP à un utilisateur et retourne (xp_total, niveau, level_up)
        où level_up est True si l'utilisateur a gagné un niveau
        """
        # Vérifier si l'utilisateur existe déjà dans la table
        self.cursor.execute('''
        SELECT xp, level FROM levels
        WHERE user_id = ? AND server_id = ?
        ''', (user_id, server_id))
        
        row = self.cursor.fetchone()
        if row:
            current_xp = row[0]
            current_level = row[1]
        else:
            current_xp = 0
            current_level = 0
            # Créer une entrée pour l'utilisateur
            self.cursor.execute('''
            INSERT INTO levels (user_id, server_id, xp, level, last_message_time)
            VALUES (?, ?, 0, 0, CURRENT_TIMESTAMP)
            ''', (user_id, server_id))
        
        # Calculer le nouvel XP et le niveau
        new_xp = current_xp + xp_amount
        # Formule pour calculer l'XP requis pour le prochain niveau: 5 * (lvl ^ 2) + 50 * lvl + 100
        xp_required = 5 * (current_level ** 2) + 50 * current_level + 100
        
        level_up = False
        new_level = current_level
        
        # Vérifier si l'utilisateur a gagné un niveau
        while new_xp >= xp_required:
            new_level += 1
            new_xp -= xp_required
            level_up = True
            # Recalculer l'XP requis pour le prochain niveau
            xp_required = 5 * (new_level ** 2) + 50 * new_level + 100
        
        # Mettre à jour la base de données
        self.cursor.execute('''
        UPDATE levels
        SET xp = ?, level = ?, last_message_time = CURRENT_TIMESTAMP
        WHERE user_id = ? AND server_id = ?
        ''', (new_xp, new_level, user_id, server_id))
        
        self.conn.commit()
        return (new_xp, new_level, level_up)
    
    def get_level_info(self, user_id: int, server_id: int) -> Dict[str, Any]:
        """Récupère les informations de niveau d'un utilisateur"""
        self.cursor.execute('''
        SELECT xp, level, last_message_time FROM levels
        WHERE user_id = ? AND server_id = ?
        ''', (user_id, server_id))
        
        row = self.cursor.fetchone()
        if row:
            return {
                "xp": row[0],
                "level": row[1],
                "last_message_time": row[2]
            }
        
        return {
            "xp": 0,
            "level": 0,
            "last_message_time": None
        }
    
    def get_connection(self):
        """Renvoie la connexion à la base de données pour des opérations personnalisées"""
        return self.conn

    def get_cursor(self):
        """Renvoie le curseur pour des opérations personnalisées"""
        return self.curso

    def get_leaderboard(self, server_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Récupère le classement des niveaux"""
        self.cursor.execute('''
        SELECT user_id, xp, level FROM levels
        WHERE server_id = ?
        ORDER BY level DESC, xp DESC
        LIMIT ?
        ''', (server_id, limit))
        
        return [dict(row) for row in self.cursor.fetchall()]
    
    # Méthodes pour les rappels
    def add_reminder(self, user_id: int, server_id: int, channel_id: int, message: str, remind_time: str) -> int:
        """Ajoute un rappel et retourne l'ID du rappel"""
        self.cursor.execute('''
        INSERT INTO reminders (user_id, server_id, channel_id, message, remind_time)
        VALUES (?, ?, ?, ?, ?)
        ''', (user_id, server_id, channel_id, message, remind_time))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_due_reminders(self) -> List[Dict[str, Any]]:
        """Récupère les rappels dus"""
        self.cursor.execute('''
        SELECT id, user_id, server_id, channel_id, message
        FROM reminders
        WHERE remind_time <= CURRENT_TIMESTAMP
        ''')
        
        return [dict(row) for row in self.cursor.fetchall()]
    
    def remove_reminder(self, reminder_id: int) -> bool:
        """Supprime un rappel et retourne True si réussi"""
        self.cursor.execute('''
        DELETE FROM reminders 
        WHERE id = ?
        ''', (reminder_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def get_connection(self):
        """Renvoie la connexion à la base de données pour des opérations personnalisées"""
        return self.conn

    def get_cursor(self):
        """Renvoie le curseur pour des opérations personnalisées"""
        return self.cursor


    def close(self):
        """Ferme la connexion à la base de données"""
        self.conn.close()
