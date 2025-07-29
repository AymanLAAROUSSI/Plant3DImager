#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de synchronisation Raspberry Pi - Serveur pour ROMI
Ce script automatise le transfert de données d'acquisition de plantes 3D
et le lancement des traitements sur le serveur.
"""

import paramiko
import os
import time
import datetime
from pathlib import Path
import glob
import re
import logging
import sys

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("sync")

# Configuration SSH
SSH_HOST = "10.0.7.22"
SSH_USER = "ayman"
KEY_PATH = "/home/romi/.ssh/id_rsa"

# Répertoires
REMOTE_BASE = "/mnt/diskSustainability/Scanner_Data/scanner_lyon/3dt_colA/Col_A_2021-01-29/"  # Notez le slash final
REMOTE_TARGET = REMOTE_BASE  # Les deux pointent maintenant vers le même répertoire
LOCAL_BASE = "/home/romi/ayman/results/plant_acquisition"
LOCAL_PLY_TARGET = "/home/romi/ayman/PointClouds"

# Mode simulation
DRY_RUN = False  # Mettre à False pour exécuter réellement

# Délai d'attente pour les opérations SSH (secondes)
SSH_TIMEOUT = 60

class SSHManager:
    """Gestionnaire de connexion SSH avec gestion des erreurs améliorée"""
    
    def __init__(self, host, username, key_path, dry_run=False):
        self.host = host
        self.username = username
        self.key_path = key_path
        self.dry_run = dry_run
        self.ssh = None
        self.sftp = None
        
    def connect(self):
        """Établit la connexion SSH et SFTP"""
        if self.dry_run:
            logger.info("[DRY RUN] Connexion SSH simulée à %s@%s", self.username, self.host)
            return True
            
        try:
            logger.info("Connexion à %s@%s...", self.username, self.host)
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(
                self.host, 
                username=self.username, 
                key_filename=self.key_path,
                timeout=SSH_TIMEOUT
            )
            
            # Vérifier que la connexion fonctionne avec une commande simple
            _, stdout, _ = self.ssh.exec_command("echo 'SSH connection test'")
            result = stdout.read().decode().strip()
            if not result:
                logger.error("Test de connexion SSH échoué")
                return False
                
            self.sftp = self.ssh.open_sftp()
            logger.info("Connexion établie avec succès")
            return True
        except Exception as e:
            logger.error("Erreur de connexion SSH: %s", str(e))
            return False
    
    def exec_command(self, command, interactive=True):
        """
        Exécute une commande SSH avec affichage en temps réel
        
        Args:
            command: Commande à exécuter
            interactive: Si True, exécute dans un environnement interactif (sourçant .bashrc)
        
        Returns:
            Tuple (success, output)
        """
        logger.info("▶️ Exécution: %s", command)
        
        if self.dry_run:
            logger.info("[DRY RUN] Commande non exécutée")
            return True, "[DRY RUN] Output simulée"
        
        if not self.ssh:
            logger.error("Aucune connexion SSH active")
            return False, "Erreur: Aucune connexion SSH active"
            
        try:
            # Préparer la commande pour s'exécuter dans un environnement correct
            if interactive:
                # Définir les variables d'environnement nécessaires et utiliser un shell login
                full_command = f"export ROMI_DB=/data/ROMI/DB && bash -l -c '{command}'"
            else:
                full_command = command
                
            stdin, stdout, stderr = self.ssh.exec_command(full_command, timeout=SSH_TIMEOUT)
            
            # Collecter la sortie en temps réel
            output = []
            for line in iter(stdout.readline, ""):
                line = line.rstrip()
                output.append(line)
                print(line)
                
            # Vérifier les erreurs
            errors = stderr.read().decode().strip()
            if errors:
                logger.warning("STDERR:\n%s", errors)
                
            exit_status = stdout.channel.recv_exit_status()
            success = (exit_status == 0)
            
            if not success:
                logger.error("La commande a échoué avec le code %d", exit_status)
            
            return success, "\n".join(output)
            
        except Exception as e:
            logger.error("Erreur lors de l'exécution de la commande: %s", str(e))
            return False, str(e)
    
    def upload_path(self, local_path, remote_path):
        """
        Upload récursif d'un fichier ou répertoire
        
        Args:
            local_path: Chemin local (fichier ou répertoire)
            remote_path: Chemin distant
        
        Returns:
            True si réussi, False sinon
        """
        if self.dry_run:
            logger.info("[DRY RUN] Upload %s → %s", local_path, remote_path)
            return True
            
        if not self.sftp:
            logger.error("Aucune connexion SFTP active")
            return False
            
        try:
            local_path = Path(local_path)
            
            # Cas fichier: simple upload
            if local_path.is_file():
                logger.debug("Upload fichier %s → %s", local_path, remote_path)
                self.sftp.put(str(local_path), remote_path)
                return True
                
            # Cas répertoire: upload récursif
            if local_path.is_dir():
                # Créer le répertoire distant
                try:
                    self.exec_command(f"mkdir -p '{remote_path}'", interactive=False)
                except:
                    pass  # Le répertoire existe peut-être déjà
                
                success = True
                # Parcourir et uploader tout le contenu
                for item in local_path.glob('**/*'):
                    if item.is_file():
                        # Calculer le chemin relatif et le chemin distant
                        rel_path = item.relative_to(local_path)
                        remote_item_path = f"{remote_path}/{rel_path}"
                        remote_dir = os.path.dirname(remote_item_path)
                        
                        # Créer le répertoire parent distant si nécessaire
                        try:
                            self.exec_command(f"mkdir -p '{remote_dir}'", interactive=False)
                        except:
                            pass
                            
                        # Upload du fichier
                        try:
                            logger.debug("Upload %s → %s", item, remote_item_path)
                            self.sftp.put(str(item), remote_item_path)
                        except Exception as e:
                            logger.error("Erreur lors de l'upload de %s: %s", item, str(e))
                            success = False
                            
                return success
                
            logger.error("Le chemin local n'existe pas: %s", local_path)
            return False
            
        except Exception as e:
            logger.error("Erreur lors de l'upload: %s", str(e))
            return False
    
    def download_file(self, remote_path, local_path):
        """Télécharge un fichier du serveur vers le local"""
        if self.dry_run:
            logger.info("[DRY RUN] Download %s → %s", remote_path, local_path)
            return True
            
        if not self.sftp:
            logger.error("Aucune connexion SFTP active")
            return False
            
        try:
            # Créer le répertoire parent local si nécessaire
            local_dir = os.path.dirname(local_path)
            os.makedirs(local_dir, exist_ok=True)
            
            # Télécharger le fichier
            logger.info("Téléchargement %s → %s", remote_path, local_path)
            self.sftp.get(remote_path, local_path)
            return True
        except Exception as e:
            logger.error("Erreur lors du téléchargement: %s", str(e))
            return False
    
    def close(self):
        """Ferme les connexions SSH et SFTP"""
        if self.sftp:
            self.sftp.close()
        if self.ssh:
            self.ssh.close()
        logger.debug("Connexions fermées")


def find_latest_directory(base_path, pattern):
    """Trouve le répertoire le plus récent correspondant au pattern"""
    base_path = Path(base_path)
    candidates = sorted(base_path.glob(pattern), key=os.path.getmtime)
    
    if not candidates:
        logger.error(f"❌ Aucun répertoire correspondant à '{pattern}' trouvé dans {base_path}")
        return None
        
    latest = candidates[-1]
    logger.info(f"✅ Dernier répertoire trouvé: {latest.name}")
    return latest


def main():
    """Fonction principale du script"""
    try:
        # 1. Connexion SSH
        ssh_manager = SSHManager(SSH_HOST, SSH_USER, KEY_PATH, dry_run=DRY_RUN)
        if not ssh_manager.connect():
            return 1
            
        # 2. Lancer la task Clean en utilisant une méthode d'exécution directe
        # Utiliser une connexion SSH directe pour exécuter la commande exactement comme en interactif
        logger.info("Lancement de la tâche Clean...")
        channel = ssh_manager.ssh.get_transport().open_session()
        channel.get_pty()  # Demander un terminal PTY pour avoir l'environnement complet
        channel.exec_command('bash -l -c "cd ~ && romi_run_task Clean /mnt/diskSustainability/Scanner_Data/scanner_lyon/3dt_colA/Col_A_2021-01-29/ --config ~/plant-3d-vision/configs/geom_pipe_real.toml"')
        
        # Afficher la sortie standard et les erreurs en temps réel
        while True:
            if channel.recv_ready():
                data = channel.recv(1024).decode('utf-8')
                print(data, end='')
            if channel.recv_stderr_ready():
                data = channel.recv_stderr(1024).decode('utf-8')
                print(f"STDERR: {data}", end='')
            if channel.exit_status_ready():
                break
        
        exit_status = channel.recv_exit_status()
        if exit_status != 0:
            logger.error(f"❌ Échec de la tâche Clean avec le code {exit_status}")
            return 1
            
        # 3. Supprimer anciens fichiers
        cleanup_parent = "/mnt/diskSustainability/Scanner_Data/scanner_lyon/3dt_colA"
        cleanup_cmd = (
            f"rm -rf {cleanup_parent}/images {cleanup_parent}/metadata "
            f"{cleanup_parent}/files.json {cleanup_parent}/scan.toml"
        )
        success, _ = ssh_manager.exec_command(cleanup_cmd)
        if not success:
            logger.error("❌ Échec du nettoyage des anciens fichiers")
            return 1
            
        # 4. Trouver le dossier circular_scan_* le plus récent
        latest_dir = find_latest_directory(LOCAL_BASE, "circular_scan_*")
        if not latest_dir:
            return 1
            
        # Extraire le timestamp pour usage ultérieur
        timestamp = latest_dir.name.replace("circular_scan_", "")
        
        # Copier les fichiers/dossiers vers le serveur
        upload_parent = "/mnt/diskSustainability/Scanner_Data/scanner_lyon/3dt_colA"
        to_copy = ["images", "metadata", "files.json", "scan.toml"]
        for item in to_copy:
            src = latest_dir / item
            dst = f"{upload_parent}/{item}"
            
            if not src.exists():
                logger.warning(f"⚠️ Item manquant, ignoré: {src}")
                continue
                
            logger.info(f"Copie de {src.name} vers le serveur...")
            if not ssh_manager.upload_path(src, dst):
                logger.error(f"❌ Échec de la copie de {src}")
                return 1
                
        # 5. Lancer la task PointCloud en utilisant une méthode d'exécution directe
        logger.info("Lancement de la tâche PointCloud...")
        channel = ssh_manager.ssh.get_transport().open_session()
        channel.get_pty()  # Demander un terminal PTY pour avoir l'environnement complet
        channel.exec_command('bash -l -c "cd ~ && romi_run_task PointCloud /mnt/diskSustainability/Scanner_Data/scanner_lyon/3dt_colA/Col_A_2021-01-29/ --config ~/plant-3d-vision/configs/geom_pipe_real.toml"')
        
        # Afficher la sortie standard et les erreurs en temps réel
        while True:
            if channel.recv_ready():
                data = channel.recv(1024).decode('utf-8')
                print(data, end='')
            if channel.recv_stderr_ready():
                data = channel.recv_stderr(1024).decode('utf-8')
                print(f"STDERR: {data}", end='')
            if channel.exit_status_ready():
                break
        
        exit_status = channel.recv_exit_status()
        if exit_status != 0:
            logger.error(f"❌ Échec de la tâche PointCloud avec le code {exit_status}")
            return 1
            
        # 6. Récupérer le bon dossier PointCloud*
        logger.info("Recherche du répertoire PointCloud le plus récent...")
        success, output = ssh_manager.exec_command(
            f"ls -td {REMOTE_BASE}PointCloud*/ | head -n1",  # Suppression du slash avant PointCloud
            interactive=False
        )
        
        if not success or not output.strip():
            logger.error("❌ Impossible de trouver le répertoire PointCloud")
            return 1
            
        pointcloud_dir = output.strip()
        pointcloud_file = f"{pointcloud_dir}/PointCloud.ply"
        local_ply_path = f"{LOCAL_PLY_TARGET}/PointCloud_{timestamp}.ply"
        
        # Télécharger le fichier PLY
        logger.info(f"Téléchargement du nuage de points: {pointcloud_file}")
        if not ssh_manager.download_file(pointcloud_file, local_ply_path):
            logger.error("❌ Échec du téléchargement du fichier PLY")
            return 1
            
        logger.info(f"✅ Fichier récupéré: {local_ply_path}")
        
        # Terminer proprement
        ssh_manager.close()
        logger.info("✅ Synchronisation terminée avec succès")
        return 0
        
    except KeyboardInterrupt:
        logger.info("🛑 Interruption utilisateur")
        return 130
    except Exception as e:
        logger.error(f"❌ Erreur inattendue: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())