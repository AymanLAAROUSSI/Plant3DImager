#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script pour exécuter le workflow complet d'acquisition, synchronisation et ciblage
"""

import os
import sys
import argparse
import time
import logging
from datetime import datetime

# Ajouter le répertoire parent au chemin de recherche Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importer les modules nécessaires
from acquisition.circle_acquisition import CircleAcquisition
from sync.server_sync import ServerSync
from targeting.leaf_targeting import LeafTargeting
from core.utils import config

class WorkflowManager:
    def __init__(self, args):
        """
        Initialise le gestionnaire de workflow
        
        Args:
            args: Arguments de la ligne de commande
        """
        # Configuration du logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        self.logger = logging.getLogger("workflow")
        
        # Stockage des arguments
        self.args = args
        
        # Résultats de chaque étape
        self.acquisition_result = None
        self.sync_result = None
        self.targeting_result = None
        
        # Chemins des données
        self.latest_acquisition_dir = None
        self.latest_ply_path = None
        
        # États pour le suivi du workflow
        self.acquisition_completed = False
        self.sync_completed = False
        self.targeting_completed = False
    
    def run_acquisition(self):
        """Exécute l'étape d'acquisition d'images"""
        self.logger.info("=== ÉTAPE 1: ACQUISITION D'IMAGES ===")
        
        # Vérifier si on doit sauter cette étape
        if self.args.skip_acquisition:
            self.logger.info("Étape d'acquisition ignorée (--skip-acquisition)")
            self.acquisition_completed = True
            return True
        
        try:
            # Créer et initialiser l'acquisition
            acquisition = CircleAcquisition(self.args)
            
            # Exécuter l'acquisition
            self.logger.info("Démarrage de l'acquisition d'images...")
            self.acquisition_result = acquisition.run_acquisition()
            
            if not self.acquisition_result:
                self.logger.error("L'acquisition a échoué")
                return False
            
            self.logger.info("Acquisition d'images terminée avec succès")
            self.acquisition_completed = True
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur pendant l'acquisition: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_sync(self):
        """Exécute l'étape de synchronisation avec le serveur"""
        self.logger.info("\n=== ÉTAPE 2: SYNCHRONISATION AVEC LE SERVEUR ===")
        
        # Vérifier si on doit sauter cette étape
        if self.args.skip_sync:
            self.logger.info("Étape de synchronisation ignorée (--skip-sync)")
            
            # Si on saute la synchro, on doit quand même définir le chemin du PLY
            if self.args.point_cloud:
                self.latest_ply_path = self.args.point_cloud
                self.logger.info(f"Utilisation du nuage de points spécifié: {self.latest_ply_path}")
                self.sync_completed = True
                return True
            else:
                self.logger.error("Aucun nuage de points spécifié avec --point-cloud alors que --skip-sync est activé")
                return False
        
        try:
            # Créer et initialiser la synchronisation
            sync = ServerSync(self.args)
            
            # Exécuter la synchronisation
            self.logger.info("Démarrage de la synchronisation...")
            self.sync_result = sync.run_sync()
            
            if not self.sync_result:
                self.logger.error("La synchronisation a échoué")
                return False
            
            # Obtenir le chemin du dernier PLY
            self.latest_ply_path = self._find_latest_ply()
            
            if not self.latest_ply_path:
                self.logger.error("Impossible de trouver le nuage de points généré")
                return False
            
            self.logger.info(f"Nuage de points trouvé: {self.latest_ply_path}")
            self.sync_completed = True
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur pendant la synchronisation: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_targeting(self):
        """Exécute l'étape de ciblage des feuilles"""
        self.logger.info("\n=== ÉTAPE 3: CIBLAGE DES FEUILLES ===")
        
        # Vérifier si on doit sauter cette étape
        if self.args.skip_targeting:
            self.logger.info("Étape de ciblage ignorée (--skip-targeting)")
            self.targeting_completed = True
            return True
        
        # Vérifier qu'on a bien un fichier PLY
        if not self.latest_ply_path:
            if self.args.point_cloud:
                self.latest_ply_path = self.args.point_cloud
                self.logger.info(f"Utilisation du nuage de points spécifié: {self.latest_ply_path}")
            else:
                self.logger.error("Aucun nuage de points disponible pour le ciblage")
                return False
        
        try:
            # Créer un dictionnaire d'arguments pour le targeting
            targeting_args = argparse.Namespace(
                point_cloud=self.latest_ply_path,
                scale=self.args.scale,
                alpha=self.args.alpha,
                crop_method=self.args.crop_method,
                crop_percentage=self.args.crop_percentage,
                z_offset=self.args.z_offset,
                arduino_port=self.args.arduino_port,
                simulate=self.args.simulate,
                auto_photo=self.args.auto_photo,
                louvain_coeff=self.args.louvain_coeff,
                distance=self.args.distance
            )
            
            # Créer et initialiser le ciblage
            targeting = LeafTargeting(targeting_args)
            
            # Exécuter le ciblage
            self.logger.info("Démarrage du ciblage des feuilles...")
            self.targeting_result = targeting.run_targeting()
            
            if not self.targeting_result:
                self.logger.error("Le ciblage a échoué")
                return False
            
            self.logger.info("Ciblage des feuilles terminé avec succès")
            self.targeting_completed = True
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur pendant le ciblage: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _find_latest_ply(self):
        """Trouve le dernier fichier PLY dans le répertoire des nuages de points"""
        ply_dir = config.LOCAL_PLY_TARGET
        
        if not os.path.exists(ply_dir):
            self.logger.error(f"Répertoire de nuages de points introuvable: {ply_dir}")
            return None
        
        # Trouver tous les fichiers PLY
        ply_files = [f for f in os.listdir(ply_dir) if f.lower().endswith('.ply')]
        
        if not ply_files:
            self.logger.error(f"Aucun fichier PLY trouvé dans {ply_dir}")
            return None
        
        # Trier par date de modification (le plus récent en premier)
        ply_files.sort(key=lambda f: os.path.getmtime(os.path.join(ply_dir, f)), reverse=True)
        
        # Retourner le chemin complet du fichier le plus récent
        latest_ply = os.path.join(ply_dir, ply_files[0])
        return latest_ply
    
    def run_workflow(self):
        """Exécute le workflow complet"""
        start_time = time.time()
        self.logger.info("=== DÉMARRAGE DU WORKFLOW COMPLET ===")
        
        # Étape 1: Acquisition
        if not self.run_acquisition():
            self.logger.error("Le workflow a été interrompu à l'étape d'acquisition")
            return False
        
        # Étape 2: Synchronisation
        if not self.run_sync():
            self.logger.error("Le workflow a été interrompu à l'étape de synchronisation")
            return False
        
        # Étape 3: Ciblage
        if not self.run_targeting():
            self.logger.error("Le workflow a été interrompu à l'étape de ciblage")
            return False
        
        # Workflow complet terminé
        elapsed_time = time.time() - start_time
        hours, remainder = divmod(elapsed_time, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        self.logger.info("\n=== WORKFLOW COMPLET TERMINÉ AVEC SUCCÈS ===")
        self.logger.info(f"Temps total: {int(hours):02}h {int(minutes):02}m {int(seconds):02}s")
        
        return True

def parse_arguments():
    """Parse les arguments de la ligne de commande"""
    parser = argparse.ArgumentParser(description="Workflow complet d'acquisition, synchronisation et ciblage")
    
    # Options générales du workflow
    workflow_group = parser.add_argument_group('Options du workflow')
    workflow_group.add_argument("--skip-acquisition", action="store_true", 
                             help="Sauter l'étape d'acquisition")
    workflow_group.add_argument("--skip-sync", action="store_true", 
                             help="Sauter l'étape de synchronisation")
    workflow_group.add_argument("--skip-targeting", action="store_true", 
                             help="Sauter l'étape de ciblage")
    workflow_group.add_argument("--point-cloud", type=str, 
                             help="Chemin vers un nuage de points existant (si --skip-sync)")
    
    # Options d'acquisition
    acq_group = parser.add_argument_group('Options d\'acquisition')
    acq_group.add_argument("--circles", "-c", type=int, choices=[1, 2], default=1,
                      help=f"Nombre de cercles à photographier (1 ou 2, défaut: 1)")
    
    acq_group.add_argument("--positions", "-p", type=int, default=config.NUM_POSITIONS, 
                      help=f"Nombre de positions par cercle (défaut: {config.NUM_POSITIONS})")
    
    acq_group.add_argument("--radius", "-r", type=float, default=config.CIRCLE_RADIUS,
                      help=f"Rayon du cercle en mètres (défaut: {config.CIRCLE_RADIUS})")
    
    acq_group.add_argument("--z-offset", "-z", type=float, default=config.Z_OFFSET,
                      help=f"Décalage en Z entre les deux cercles en mètres (défaut: {config.Z_OFFSET})")
    
    # Options de ciblage
    target_group = parser.add_argument_group('Options de ciblage')
    target_group.add_argument("--scale", type=float, default=0.001, 
                         help="Facteur d'échelle pour le nuage de points (défaut: 0.001 = mm->m)")
    
    target_group.add_argument("--alpha", type=float, default=0.1, 
                         help="Valeur alpha pour Alpha Shape (défaut: 0.1)")
    
    target_group.add_argument("--crop_method", choices=['none', 'top_percentage', 'single_furthest'], 
                         default='none', help="Méthode de cropping (défaut: none)")
    
    target_group.add_argument("--crop_percentage", type=float, default=0.25, 
                         help="Pourcentage pour top_percentage (défaut: 0.25)")
    
    target_group.add_argument("--louvain_coeff", type=float, default=0.5, 
                         help="Coefficient pour la détection Louvain (défaut: 0.5)")
    
    target_group.add_argument("--distance", type=float, default=0.4, 
                         help="Distance aux feuilles cibles en mètres (défaut: 0.4 m)")
    
    target_group.add_argument("--simulate", action="store_true", 
                         help="Mode simulation (sans contrôle robot)")
    
    target_group.add_argument("--auto_photo", action="store_true", 
                         help="Prendre automatiquement des photos à chaque cible")
    
    # Options matérielles
    hw_group = parser.add_argument_group('Options matérielles')
    hw_group.add_argument("--arduino-port", "-a", type=str, default=config.ARDUINO_PORT,
                      help=f"Port Arduino (défaut: {config.ARDUINO_PORT})")
    
    hw_group.add_argument("--speed", "-s", type=float, default=config.CNC_SPEED,
                      help=f"Vitesse de déplacement de la CNC en m/s (défaut: {config.CNC_SPEED})")
    
    # Options de synchronisation
    sync_group = parser.add_argument_group('Options de synchronisation')
    sync_group.add_argument("--ssh-host", type=str, default=config.SSH_HOST,
                       help=f"Adresse du serveur SSH (défaut: {config.SSH_HOST})")
    
    sync_group.add_argument("--ssh-user", type=str, default=config.SSH_USER,
                       help=f"Nom d'utilisateur SSH (défaut: {config.SSH_USER})")
    
    sync_group.add_argument("--key-path", type=str, default=config.KEY_PATH,
                       help=f"Chemin vers la clé SSH (défaut: {config.KEY_PATH})")
    
    sync_group.add_argument("--remote-path", type=str, default=config.REMOTE_WORK_PATH,
                       help=f"Chemin du répertoire de travail distant (défaut: {config.REMOTE_WORK_PATH})")
    
    sync_group.add_argument("--local-acq", type=str, default=config.LOCAL_ACQUISITION_BASE,
                       help=f"Répertoire d'acquisition local (défaut: {config.LOCAL_ACQUISITION_BASE})")
    
    sync_group.add_argument("--ply-target", type=str, default=config.LOCAL_PLY_TARGET,
                       help=f"Répertoire cible pour les fichiers PLY (défaut: {config.LOCAL_PLY_TARGET})")
    
    sync_group.add_argument("--dry-run", action="store_true",
                       help="Mode simulation pour la synchronisation (pas d'exécution réelle)")
    
    return parser.parse_args()

def main():
    """Fonction principale"""
    print("=== Workflow Complet: Acquisition, Synchronisation et Ciblage ===")
    
    # Parser les arguments
    args = parse_arguments()
    
    # Créer et exécuter le workflow
    workflow = WorkflowManager(args)
    success = workflow.run_workflow()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
