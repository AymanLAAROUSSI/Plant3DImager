#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Gestionnaire de connexion SSH avec gestion des erreurs améliorée
"""

import paramiko
import os
import time
import logging
from pathlib import Path

class SSHManager:
    """Gestionnaire de connexion SSH avec gestion des erreurs améliorée"""
    
    def __init__(self, host, username, key_path, dry_run=False):
        self.host = host
        self.username = username
        self.key_path = key_path
        self.dry_run = dry_run
        self.ssh = None
        self.sftp = None
        self.logger = logging.getLogger("sync.ssh")
        
    def connect(self):
        """Établit la connexion SSH et SFTP"""
        if self.dry_run:
            self.logger.info("[DRY RUN] Connexion SSH simulée à %s@%s", self.username, self.host)
            return True
            
        try:
            self.logger.info("Connexion à %s@%s...", self.username, self.host)
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(
                self.host, 
                username=self.username, 
                key_filename=self.key_path,
                timeout=300
            )
            
            # Vérifier que la connexion fonctionne
            _, stdout, _ = self.ssh.exec_command("echo 'SSH connection test'")
            result = stdout.read().decode().strip()
            if not result:
                self.logger.error("Test de connexion SSH échoué")
                return False
                
            self.sftp = self.ssh.open_sftp()
            self.logger.info("[CONNEXION] Connexion SSH/SFTP établie avec succès")
            return True
        except Exception as e:
            self.logger.error("❌ Erreur de connexion SSH: %s", str(e))
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
            self.logger.info("[SIMULATION] romi_run_task %s", command_args)
            return True
            
        if not self.ssh:
            self.logger.error("[ERREUR] Aucune connexion SSH active")
            return False
            
        try:
            self.logger.info("[EXÉCUTION] romi_run_task %s", command_args)
            
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
                self.logger.debug("Sortie capturée pour analyse: %s", full_output[:500] + "..." if len(full_output) > 500 else full_output)
            
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
                    self.logger.warning("[VERROU] Détection du pattern de verrou: %s", pattern)
                    return "lock_detected"
            
            if exit_status == 0:
                self.logger.info("[SUCCÈS] Commande romi_run_task réussie")
                return True
            else:
                self.logger.error("[ERREUR] Commande romi_run_task échouée avec le code %d", exit_status)
                return False
                
        except Exception as e:
            self.logger.error("[ERREUR] Erreur lors de l'exécution de la commande ROMI: %s", str(e))
            return False
    
    def exec_command(self, command):
        """Exécute une commande système simple"""
        if self.dry_run:
            self.logger.info("[SIMULATION] %s", command)
            return True, "[SIMULATION] Sortie simulée"
            
        if not self.ssh:
            self.logger.error("[ERREUR] Aucune connexion SSH active")
            return False, "Aucune connexion SSH"
            
        try:
            self.logger.info("[COMMANDE] %s", command)
            stdin, stdout, stderr = self.ssh.exec_command(command, timeout=300)
            
            output = stdout.read().decode().strip()
            errors = stderr.read().decode().strip()
            exit_status = stdout.channel.recv_exit_status()
            
            if exit_status == 0:
                return True, output
            else:
                self.logger.error("[ERREUR] Commande échouée (code %d): %s", exit_status, errors)
                return False, errors
                
        except Exception as e:
            self.logger.error("[ERREUR] Erreur: %s", str(e))
            return False, str(e)
    
    def upload_path(self, local_path, remote_path):
        """Upload récursif d'un fichier ou répertoire"""
        if self.dry_run:
            self.logger.info("[SIMULATION] Upload %s → %s", local_path, remote_path)
            return True
            
        if not self.sftp:
            self.logger.error("[ERREUR] Aucune connexion SFTP active")
            return False
            
        try:
            local_path = Path(local_path)
            
            if local_path.is_file():
                # Upload simple d'un fichier
                self.logger.info("[UPLOAD] Fichier: %s → %s", local_path.name, remote_path)
                self.sftp.put(str(local_path), remote_path)
                return True
                
            elif local_path.is_dir():
                # Upload récursif d'un répertoire
                self.logger.info("[UPLOAD] Répertoire: %s → %s", local_path.name, remote_path)
                
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
                            self.logger.error("[ERREUR] Erreur upload %s: %s", item, str(e))
                            return False
                            
                return True
            else:
                self.logger.error("[ERREUR] Chemin local introuvable: %s", local_path)
                return False
                
        except Exception as e:
            self.logger.error("[ERREUR] Erreur lors de l'upload: %s", str(e))
            return False
    
    def download_file(self, remote_path, local_path):
        """Télécharge un fichier du serveur"""
        if self.dry_run:
            self.logger.info("[SIMULATION] Download %s → %s", remote_path, local_path)
            return True
            
        if not self.sftp:
            self.logger.error("[ERREUR] Aucune connexion SFTP active")
            return False
            
        try:
            # Créer le répertoire parent local
            local_dir = os.path.dirname(local_path)
            os.makedirs(local_dir, exist_ok=True)
            
            self.logger.info("[TÉLÉCHARGEMENT] %s → %s", remote_path, local_path)
            self.sftp.get(remote_path, local_path)
            return True
        except Exception as e:
            self.logger.error("[ERREUR] Erreur téléchargement: %s", str(e))
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
            self.logger.warning("🔒 Fichier de verrou détecté: %s", lock_file)
            return handle_lock_removal(self)  # Retourne "exit_script" ou autre
        else:
            # Pas de verrou, on peut continuer
            return "continue"
    
    def close(self):
        """Ferme les connexions"""
        if self.sftp:
            self.sftp.close()
        if self.ssh:
            self.ssh.close()
        self.logger.info("🔌 Connexions fermées")


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
                    print("       Commande: python scripts/run_sync.py")
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