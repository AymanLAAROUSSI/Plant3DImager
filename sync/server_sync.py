#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module de synchronisation Raspberry Pi - Serveur pour ROMI
Ce module automatise le transfert de données d'acquisition de plantes 3D
et le lancement des traitements sur le serveur.
"""

import time
import os
import logging
import sys
from pathlib import Path
from sync.ssh_manager import SSHManager, handle_lock_removal
from core.utils import config

class ServerSync:
    def __init__(self, args=None):
        """
        Initialise le module de synchronisation
        
        Args:
            args: Arguments de la ligne de commande (optionnel)
        """
        # Configuration du logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        self.logger = logging.getLogger("sync")
        
        # Paramètres par défaut
        self.ssh_host = config.SSH_HOST if hasattr(config, 'SSH_HOST') else "10.0.7.22"
        self.ssh_user = config.SSH_USER if hasattr(config, 'SSH_USER') else "ayman"
        self.key_path = config.KEY_PATH if hasattr(config, 'KEY_PATH') else "/home/romi/.ssh/id_rsa"
        self.remote_work_path = config.REMOTE_WORK_PATH if hasattr(config, 'REMOTE_WORK_PATH') else "/mnt/diskSustainability/Scanner_Data/scanner_lyon/3dt_colA/Col_A_2021-01-29/"
        self.local_acquisition_base = config.LOCAL_ACQUISITION_BASE if hasattr(config, 'LOCAL_ACQUISITION_BASE') else "/home/romi/ayman/results/plant_acquisition"
        self.local_ply_target = config.LOCAL_PLY_TARGET if hasattr(config, 'LOCAL_PLY_TARGET') else "/home/romi/ayman/PointClouds"
        self.romi_config = config.ROMI_CONFIG if hasattr(config, 'ROMI_CONFIG') else "~/plant-3d-vision/configs/geom_pipe_real.toml"
        self.dry_run = False  # Mode simulation
        
        # Mettre à jour les paramètres avec les arguments de la ligne de commande
        if args:
            self.update_from_args(args)
            
        # SSH Manager
        self.ssh = None
        
        # État
        self.initialized = False
    
    def update_from_args(self, args):
        """Met à jour les paramètres depuis les arguments de la ligne de commande"""
        if hasattr(args, 'ssh_host') and args.ssh_host:
            self.ssh_host = args.ssh_host
            
        if hasattr(args, 'ssh_user') and args.ssh_user:
            self.ssh_user = args.ssh_user
            
        if hasattr(args, 'key_path') and args.key_path:
            self.key_path = args.key_path
            
        if hasattr(args, 'remote_path') and args.remote_path:
            self.remote_work_path = args.remote_path
            
        if hasattr(args, 'local_acq') and args.local_acq:
            self.local_acquisition_base = args.local_acq
            
        if hasattr(args, 'ply_target') and args.ply_target:
            self.local_ply_target = args.ply_target
            
        if hasattr(args, 'dry_run') and args.dry_run:
            self.dry_run = args.dry_run
    
    def initialize(self):
        """Initialise la connexion SSH"""
        if self.initialized:
            return True
        
        try:
            self.logger.info("[DÉMARRAGE] Initialisation de la synchronisation")
            
            # Créer le gestionnaire SSH
            self.ssh = SSHManager(
                self.ssh_host, 
                self.ssh_user, 
                self.key_path, 
                dry_run=self.dry_run
            )
            
            # Connecter
            if not self.ssh.connect():
                return False
            
            # Vérifier et gérer le verrou
            self.logger.info("[VÉRIFICATION] Vérification du verrou de base de données...")
            lock_result = self.ssh.check_and_handle_lock()
            if lock_result == "exit_script":
                return False
            elif lock_result != "continue":
                self.logger.error("[ERREUR] Erreur lors de la vérification du verrou")
                return False
            
            self.initialized = True
            return True
            
        except Exception as e:
            self.logger.error("[ERREUR] Erreur d'initialisation: %s", str(e))
            return False
    
    def find_latest_acquisition(self):
        """Trouve le répertoire circular_scan_* le plus récent"""
        base_path = self.local_acquisition_base
        pattern = "circular_scan_*"
        
        try:
            base_path = Path(base_path)
            candidates = list(base_path.glob(pattern))
            
            if not candidates:
                self.logger.error("[ERREUR] Aucun répertoire '%s' trouvé dans %s", pattern, base_path)
                return None, None
                
            # Trier par date de modification
            latest = max(candidates, key=os.path.getmtime)
            
            # Extraire le timestamp du nom
            timestamp = latest.name.replace("circular_scan_", "")
            
            self.logger.info("[TROUVÉ] Dernière acquisition trouvée: %s", latest.name)
            return latest, timestamp
            
        except Exception as e:
            self.logger.error("[ERREUR] Erreur lors de la recherche: %s", str(e))
            return None, None
    
    def run_sync(self):
        """Exécute le processus de synchronisation complet"""
        if not self.initialize():
            return False
        
        try:
            # 1. Lancer Clean
            self.logger.info("[NETTOYAGE] Étape 1/6: Nettoyage initial (Clean)")
            clean_args = f"Clean {self.remote_work_path} --config {self.romi_config}"
            result = self.ssh.exec_romi_command(clean_args)
            
            if result == "lock_detected":
                self.logger.warning("[VERROU] Verrou de base de données détecté pendant Clean")
                lock_result = handle_lock_removal(self.ssh)
                if lock_result == "exit_script":
                    return False
            elif not result:
                self.logger.error("[ERREUR] Échec de la tâche Clean")
                return False
            
            # 2. Supprimer les anciens fichiers du serveur
            self.logger.info("[SUPPRESSION] Étape 2/6: Suppression des anciens fichiers")
            items_to_remove = ["images", "metadata", "files.json", "scan.toml"]
            for item in items_to_remove:
                cmd = f"rm -rf '{self.remote_work_path}{item}'"
                success, _ = self.ssh.exec_command(cmd)
                if not success:
                    self.logger.warning("[ATTENTION] Impossible de supprimer %s (peut-être absent)", item)
            
            # 3. Trouver la dernière acquisition locale
            self.logger.info("[RECHERCHE] Étape 3/6: Recherche de la dernière acquisition")
            latest_dir, timestamp = self.find_latest_acquisition()
            if not latest_dir:
                return False
            
            # 4. Copier les nouveaux fichiers vers le serveur
            self.logger.info("[ENVOI] Étape 4/6: Upload des nouvelles données")
            items_to_copy = ["images", "metadata", "files.json", "scan.toml"]
            
            for item in items_to_copy:
                src_path = latest_dir / item
                dst_path = f"{self.remote_work_path}{item}"
                
                if not src_path.exists():
                    self.logger.warning("[ATTENTION] Item manquant (ignoré): %s", src_path)
                    continue
                
                self.logger.info("[ENVOI] Copie: %s", item)
                if not self.ssh.upload_path(src_path, dst_path):
                    self.logger.error("[ERREUR] Échec de la copie de %s", item)
                    return False
            
            # 5. Lancer PointCloud
            self.logger.info("[TRAITEMENT] Étape 5/6: Génération du nuage de points (PointCloud)")
            pointcloud_args = f"PointCloud {self.remote_work_path} --config {self.romi_config}"
            result = self.ssh.exec_romi_command(pointcloud_args)
            
            if result == "lock_detected":
                self.logger.warning("[VERROU] Verrou de base de données détecté pendant PointCloud")
                lock_result = handle_lock_removal(self.ssh)
                if lock_result == "exit_script":
                    return False
            elif not result:
                self.logger.error("[ERREUR] Échec de la tâche PointCloud")
                return False
            
            # 6. Récupérer le fichier PLY
            self.logger.info("[TÉLÉCHARGEMENT] Étape 6/6: Récupération du nuage de points")
            
            # Trouver le répertoire PointCloud*
            find_cmd = f"find '{self.remote_work_path}' -name 'PointCloud*' -type d | head -1"
            success, pointcloud_dir = self.ssh.exec_command(find_cmd)
            
            if not success or not pointcloud_dir:
                self.logger.error("[ERREUR] Impossible de trouver le répertoire PointCloud")
                return False
            
            # Télécharger le fichier PLY
            remote_ply = f"{pointcloud_dir.strip()}/PointCloud.ply"
            local_ply = f"{self.local_ply_target}/PointCloud_{timestamp}.ply"
            
            if not self.ssh.download_file(remote_ply, local_ply):
                self.logger.error("[ERREUR] Échec du téléchargement du PLY")
                return False
            
            self.logger.info("[SUCCÈS] Fichier PLY récupéré: %s", local_ply)
            
            # 7. Fermeture propre
            self.ssh.close()
            self.logger.info("[TERMINÉ] Synchronisation terminée avec succès")
            return True
            
        except KeyboardInterrupt:
            self.logger.info("[ARRÊT] Interruption utilisateur")
            return False
        except Exception as e:
            self.logger.error("[ERREUR] Erreur inattendue: %s", str(e), exc_info=True)
            return False
        finally:
            if self.ssh:
                self.ssh.close()
    
    def shutdown(self):
        """Arrête proprement la connexion"""
        if self.ssh:
            self.ssh.close()
        self.initialized = False
        self.logger.info("[TERMINÉ] Module de synchronisation arrêté")