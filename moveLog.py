import os
import shutil

# Parcourir tous les fichiers dans le dossier logs
logs_dir = 'logs'
if os.path.exists(logs_dir):
    for filename in os.listdir(logs_dir):
        file_path = os.path.join(logs_dir, filename)
        if os.path.isfile(file_path):
            # Déplacer le fichier vers le répertoire principal
            shutil.move(file_path, '.')
            print(f"Déplacé: {filename}")
    
    # Supprimer le dossier logs une fois vide
    os.rmdir(logs_dir)
    print(f"Dossier {logs_dir} supprimé")
else:
    print(f"Le dossier {logs_dir} n'existe pas")
