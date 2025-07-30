#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de synchronisation Raspberry Pi - Serveur pour ROMI
Ce script automatise le transfert de données d'acquisition de plantes 3D
et le lancement des traitements sur le serveur.

Version corrigée avec les bonnes variables d'environnement et chemins
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
REMOTE_WORK_PATH = "/mnt/diskSustainability/Scanner_Data/scanner_lyon/3dt_colA/Col_A_2021-01-29/"  # Tout se passe ici
LOCAL_ACQUISITION_BASE = "/home/romi/ayman/results/plant_acquisition"
LOCAL_PLY_TARGET = "/home/romi/ayman/PointClouds"

# Configuration ROMI
ROMI_CONFIG = "~/plant-3d-vision/configs/geom_pipe_real.toml"

# Mode simulation
DRY_RUN = False  # Mettre à True pour tester sans exécuter

# Délai d'attente pour les opérations SSH (secondes)
SSH_TIMEOUT = 300  # 5 minutes pour les tâches longues

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
            
            # Vérifier que la connexion fonctionne
            _, stdout, _ = self.ssh.exec_command("echo 'SSH connection test'")
            result = stdout.read().decode().strip()
            if not result:
                logger.error("Test de connexion SSH échoué")
                return False
                
            self.sftp = self.ssh.open_sftp()
            logger.info("[CONNEXION] Connexion SSH/SFTP établie avec succès")
            return True
        except Exception as e:
            logger.error("❌ Erreur de connexion SSH: %s", str(e))
            return False
    
    def exec_romi_command(self, command_args):
        """
        Exécute une commande romi_run_task avec l'environnement correct
        
        Args:
            command_args: Arguments pour romi_run_task (ex: "Clean /path/to/scan --config /path/to/config")
        
        Returns:
            True si succès, False sinon, "lock_detected" si verrou détecté
        """
        if self.dry_run:
            logger.info("[SIMULATION] romi_run_task %s", command_args)
            return True
            
        if not self.ssh:
            logger.error("[ERREUR] Aucune connexion SSH active")
            return False
            
        try:
            logger.info("[EXÉCUTION] romi_run_task %s", command_args)
            
            # Créer un canal avec PTY pour avoir l'environnement complet
            channel = self.ssh.get_transport().open_session()
            channel.get_pty()
            
            # Commande avec environnement correct (basé sur nos tests précédents)
            full_command = (
                "bash -l -c '"
                "export PYTHONPATH=/home/ayman/plant-3d-vision && "
                "unset ROMI_DB && "
                "cd /home/ayman/plant-3d-vision && "
                f"/home/ayman/.local/bin/romi_run_task {command_args}"
                "'"
            )
            
            channel.exec_command(full_command)
            
            # Afficher la sortie en temps réel et capturer pour détecter le verrou
            output_lines = []
            stderr_lines = []
            
            while True:
                if channel.recv_ready():
                    data = channel.recv(1024).decode('utf-8')
                    print(data, end='')
                    output_lines.append(data)
                    
                if channel.recv_stderr_ready():
                    data = channel.recv_stderr(1024).decode('utf-8')
                    print(f"STDERR: {data}", end='')
                    stderr_lines.append(data)
                    
                if channel.exit_status_ready():
                    break
                    
                time.sleep(0.1)  # Petite pause pour éviter la surcharge CPU
            
            # Après la fin, lire tout ce qui reste
            time.sleep(0.5)  # Attendre un peu plus pour être sûr
            while channel.recv_ready():
                data = channel.recv(1024).decode('utf-8')
                output_lines.append(data)
                print(data, end='')
            while channel.recv_stderr_ready():
                data = channel.recv_stderr(1024).decode('utf-8')
                stderr_lines.append(data)
                print(f"STDERR: {data}", end='')
            
            exit_status = channel.recv_exit_status()
            channel.close()
            
            # Vérifier s'il y a une erreur de verrou dans toute la sortie
            full_output = "".join(output_lines + stderr_lines)
            
            # Debug: afficher ce qu'on a capturé (en mode debug uniquement)
            if exit_status != 0:
                logger.debug("Sortie capturée pour analyse: %s", full_output[:500] + "..." if len(full_output) > 500 else full_output)
            
            # Détecter les différents patterns d'erreur de verrou
            lock_patterns = [
                "DBBusyError",
                "File lock exists", 
                "DB is busy, cannot connect",
                "File exists: '/mnt/diskSustainability/Scanner_Data/scanner_lyon/3dt_colA/lock'",
                "FileExistsError: [Errno 17] File exists:",
                "/lock'"  # Pattern plus simple pour le chemin du fichier lock
            ]
            
            for pattern in lock_patterns:
                if pattern in full_output:
                    logger.warning("[VERROU] Détection du pattern de verrou: %s", pattern)
                    return "lock_detected"
            
            if exit_status == 0:
                logger.info("[SUCCÈS] Commande romi_run_task réussie")
                return True
            else:
                logger.error("[ERREUR] Commande romi_run_task échouée avec le code %d", exit_status)
                return False
                
        except Exception as e:
            logger.error("[ERREUR] Erreur lors de l'exécution de la commande ROMI: %s", str(e))
            return False
    
    def exec_command(self, command):
        """Exécute une commande système simple"""
        if self.dry_run:
            logger.info("[SIMULATION] %s", command)
            return True, "[SIMULATION] Sortie simulée"
            
        if not self.ssh:
            logger.error("[ERREUR] Aucune connexion SSH active")
            return False, "Aucune connexion SSH"
            
        try:
            logger.info("[COMMANDE] %s", command)
            stdin, stdout, stderr = self.ssh.exec_command(command, timeout=SSH_TIMEOUT)
            
            output = stdout.read().decode().strip()
            errors = stderr.read().decode().strip()
            exit_status = stdout.channel.recv_exit_status()
            
            if exit_status == 0:
                return True, output
            else:
                logger.error("[ERREUR] Commande échouée (code %d): %s", exit_status, errors)
                return False, errors
                
        except Exception as e:
            logger.error("[ERREUR] Erreur: %s", str(e))
            return False, str(e)
    
    def upload_path(self, local_path, remote_path):
        """Upload récursif d'un fichier ou répertoire"""
        if self.dry_run:
            logger.info("[SIMULATION] Upload %s → %s", local_path, remote_path)
            return True
            
        if not self.sftp:
            logger.error("[ERREUR] Aucune connexion SFTP active")
            return False
            
        try:
            local_path = Path(local_path)
            
            if local_path.is_file():
                # Upload simple d'un fichier
                logger.info("[UPLOAD] Fichier: %s → %s", local_path.name, remote_path)
                self.sftp.put(str(local_path), remote_path)
                return True
                
            elif local_path.is_dir():
                # Upload récursif d'un répertoire
                logger.info("[UPLOAD] Répertoire: %s → %s", local_path.name, remote_path)
                
                # Créer le répertoire distant
                self.exec_command(f"mkdir -p '{remote_path}'")
                
                # Parcourir et uploader tous les fichiers
                for item in local_path.rglob('*'):
                    if item.is_file():
                        rel_path = item.relative_to(local_path)
                        remote_item = f"{remote_path}/{rel_path}".replace('\\', '/')
                        remote_dir = os.path.dirname(remote_item)
                        
                        # Créer le répertoire parent si nécessaire
                        self.exec_command(f"mkdir -p '{remote_dir}'")
                        
                        # Upload du fichier
                        try:
                            self.sftp.put(str(item), remote_item)
                        except Exception as e:
                            logger.error("[ERREUR] Erreur upload %s: %s", item, str(e))
                            return False
                            
                return True
            else:
                logger.error("[ERREUR] Chemin local introuvable: %s", local_path)
                return False
                
        except Exception as e:
            logger.error("[ERREUR] Erreur lors de l'upload: %s", str(e))
            return False
    
    def download_file(self, remote_path, local_path):
        """Télécharge un fichier du serveur"""
        if self.dry_run:
            logger.info("[SIMULATION] Download %s → %s", remote_path, local_path)
            return True
            
        if not self.sftp:
            logger.error("[ERREUR] Aucune connexion SFTP active")
            return False
            
        try:
            # Créer le répertoire parent local
            local_dir = os.path.dirname(local_path)
            os.makedirs(local_dir, exist_ok=True)
            
            logger.info("[TÉLÉCHARGEMENT] %s → %s", remote_path, local_path)
            self.sftp.get(remote_path, local_path)
            return True
        except Exception as e:
            logger.error("[ERREUR] Erreur téléchargement: %s", str(e))
            return False
    
    def check_and_handle_lock(self):
        """Vérifie s'il y a un verrou et propose de le supprimer"""
        if self.dry_run:
            return "continue"
            
        # Vérifier l'existence du fichier de verrou
        lock_file = "/mnt/diskSustainability/Scanner_Data/scanner_lyon/3dt_colA/lock"
        check_cmd = f"test -f '{lock_file}'"
        success, _ = self.exec_command(check_cmd)
        
        if success:  # Le fichier existe (test -f retourne 0 si le fichier existe)
            logger.warning("🔒 Fichier de verrou détecté: %s", lock_file)
            return handle_lock_removal(self)  # Retourne "exit_script" ou autre
        else:
            # Pas de verrou, on peut continuer
            return "continue"
        """Ferme les connexions"""
        if self.sftp:
            self.sftp.close()
        if self.ssh:
            self.ssh.close()
    def close(self):
        """Ferme les connexions"""
        if self.sftp:
            self.sftp.close()
        if self.ssh:
            self.ssh.close()
        logger.info("🔌 Connexions fermées")


def handle_lock_removal(ssh_manager):
    """Gère la suppression du verrou avec confirmation utilisateur"""
    print("\n" + "="*80)
    print("ATTENTION - VERROU DE BASE DE DONNÉES DÉTECTÉ")
    print("="*80)
    print("La présence d'un verrou peut signifier que :")
    print("  • Une tâche ROMI est actuellement en cours d'exécution")
    print("  • Une tâche précédente s'est mal terminée")
    print("  • Le système a été interrompu brutalement")
    print("\nATTENTION: Supprimer le verrou pendant qu'une tâche s'exécute peut corrompre les données !")
    print("="*80)
    
    while True:
        try:
            response = input("\nVoulez-vous supprimer le verrou ? (oui/non): ").strip().lower()
            if response in ['oui', 'o', 'yes', 'y']:
                # Supprimer le verrou
                lock_file = "/mnt/diskSustainability/Scanner_Data/scanner_lyon/3dt_colA/lock"
                unlock_cmd = f"rm -f '{lock_file}'"
                success, _ = ssh_manager.exec_command(unlock_cmd)
                
                if success:
                    print("\n[SUCCÈS] Verrou supprimé avec succès")
                    print("[INFO] Veuillez relancer le script pour continuer la synchronisation.")
                    print("       Commande: python raspberry_to_server_sync.py")
                else:
                    print("\n[ERREUR] Impossible de supprimer le verrou")
                    print("         Vérifiez les permissions ou contactez l'administrateur.")
                return "exit_script"  # Indiquer qu'il faut sortir du script
                
            elif response in ['non', 'n', 'no']:
                print("\n[ARRÊT] Opération annulée. Le verrou n'a pas été supprimé.")
                print("        La synchronisation ne peut pas continuer tant que le verrou existe.")
                return "exit_script"  # Sortir aussi dans ce cas
            else:
                print("[ERREUR] Réponse non reconnue. Veuillez taper 'oui' ou 'non'")
                
        except KeyboardInterrupt:
            print("\n\n[ARRÊT] Opération annulée par l'utilisateur")
            return "exit_script"
    """Trouve le répertoire circular_scan_* le plus récent"""
    base_path = Path(base_path)
    pattern = "circular_scan_*"
    
    try:
        candidates = list(base_path.glob(pattern))
        if not candidates:
            logger.error("❌ Aucun répertoire '%s' trouvé dans %s", pattern, base_path)
            return None, None
            
        # Trier par date de modification
        latest = max(candidates, key=os.path.getmtime)
        
        # Extraire le timestamp du nom
        timestamp = latest.name.replace("circular_scan_", "")
        
        logger.info("✅ Dernière acquisition trouvée: %s", latest.name)
        return latest, timestamp
        
    except Exception as e:
        logger.error("❌ Erreur lors de la recherche: %s", str(e))
        return None, None


def find_latest_acquisition(base_path):
    """Trouve le répertoire circular_scan_* le plus récent"""
    base_path = Path(base_path)
    pattern = "circular_scan_*"
    
    try:
        candidates = list(base_path.glob(pattern))
        if not candidates:
            logger.error("[ERREUR] Aucun répertoire '%s' trouvé dans %s", pattern, base_path)
            return None, None
            
        # Trier par date de modification
        latest = max(candidates, key=os.path.getmtime)
        
        # Extraire le timestamp du nom
        timestamp = latest.name.replace("circular_scan_", "")
        
        logger.info("[TROUVÉ] Dernière acquisition trouvée: %s", latest.name)
        return latest, timestamp
        
    except Exception as e:
        logger.error("[ERREUR] Erreur lors de la recherche: %s", str(e))
        return None, None


def main():
    """Fonction principale"""
    logger.info("[DÉMARRAGE] Début de la synchronisation Raspberry Pi vers Serveur")
    
    try:
        # 1. Connexion SSH
        ssh = SSHManager(SSH_HOST, SSH_USER, KEY_PATH, dry_run=DRY_RUN)
        if not ssh.connect():
            return 1
        
        # 1. Vérifier et gérer le verrou avant de commencer
        logger.info("[VÉRIFICATION] Vérification du verrou de base de données...")
        lock_result = ssh.check_and_handle_lock()
        if lock_result == "exit_script":
            return 0  # Sortie propre après gestion du verrou
        elif lock_result != "continue":
            logger.error("[ERREUR] Erreur lors de la vérification du verrou")
            return 1
        
        # 2. Lancer Clean
        logger.info("[NETTOYAGE] Étape 1/6: Nettoyage initial (Clean)")
        clean_args = f"Clean {REMOTE_WORK_PATH} --config {ROMI_CONFIG}"
        result = ssh.exec_romi_command(clean_args)
        
        if result == "lock_detected":
            logger.warning("[VERROU] Verrou de base de données détecté pendant Clean")
            lock_result = handle_lock_removal(ssh)
            if lock_result == "exit_script":
                return 0  # Sortie propre après gestion du verrou
        elif not result:
            logger.error("[ERREUR] Échec de la tâche Clean")
            return 1
        
        # 2. Supprimer les anciens fichiers du serveur
        logger.info("[SUPPRESSION] Étape 2/6: Suppression des anciens fichiers")
        items_to_remove = ["images", "metadata", "files.json", "scan.toml"]
        for item in items_to_remove:
            cmd = f"rm -rf '{REMOTE_WORK_PATH}{item}'"
            success, _ = ssh.exec_command(cmd)
            if not success:
                logger.warning("[ATTENTION] Impossible de supprimer %s (peut-être absent)", item)
        
        # 3. Trouver la dernière acquisition locale
        logger.info("[RECHERCHE] Étape 3/6: Recherche de la dernière acquisition")
        latest_dir, timestamp = find_latest_acquisition(LOCAL_ACQUISITION_BASE)
        if not latest_dir:
            return 1
        
        # 4. Copier les nouveaux fichiers vers le serveur
        logger.info("[ENVOI] Étape 4/6: Upload des nouvelles données")
        items_to_copy = ["images", "metadata", "files.json", "scan.toml"]
        
        for item in items_to_copy:
            src_path = latest_dir / item
            dst_path = f"{REMOTE_WORK_PATH}{item}"
            
            if not src_path.exists():
                logger.warning("[ATTENTION] Item manquant (ignoré): %s", src_path)
                continue
            
            logger.info("[ENVOI] Copie: %s", item)
            if not ssh.upload_path(src_path, dst_path):
                logger.error("[ERREUR] Échec de la copie de %s", item)
                return 1
        
        # 5. Lancer PointCloud
        logger.info("[TRAITEMENT] Étape 5/6: Génération du nuage de points (PointCloud)")
        pointcloud_args = f"PointCloud {REMOTE_WORK_PATH} --config {ROMI_CONFIG}"
        result = ssh.exec_romi_command(pointcloud_args)
        
        if result == "lock_detected":
            logger.warning("[VERROU] Verrou de base de données détecté pendant PointCloud")
            lock_result = handle_lock_removal(ssh)
            if lock_result == "exit_script":
                return 0  # Sortie propre après gestion du verrou
        elif not result:
            logger.error("[ERREUR] Échec de la tâche PointCloud")
            return 1
        
        # 6. Récupérer le fichier PLY
        logger.info("[TÉLÉCHARGEMENT] Étape 6/6: Récupération du nuage de points")
        
        # Trouver le répertoire PointCloud*
        find_cmd = f"find '{REMOTE_WORK_PATH}' -name 'PointCloud*' -type d | head -1"
        success, pointcloud_dir = ssh.exec_command(find_cmd)
        
        if not success or not pointcloud_dir:
            logger.error("[ERREUR] Impossible de trouver le répertoire PointCloud")
            return 1
        
        # Télécharger le fichier PLY
        remote_ply = f"{pointcloud_dir.strip()}/PointCloud.ply"
        local_ply = f"{LOCAL_PLY_TARGET}/PointCloud_{timestamp}.ply"
        
        if not ssh.download_file(remote_ply, local_ply):
            logger.error("[ERREUR] Échec du téléchargement du PLY")
            return 1
        
        logger.info("[SUCCÈS] Fichier PLY récupéré: %s", local_ply)
        
        # 7. Fermeture propre
        ssh.close()
        logger.info("[TERMINÉ] Synchronisation terminée avec succès")
        return 0
        
    except KeyboardInterrupt:
        logger.info("[ARRÊT] Interruption utilisateur")
        return 130
    except Exception as e:
        logger.error("[ERREUR] Erreur inattendue: %s", str(e), exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)