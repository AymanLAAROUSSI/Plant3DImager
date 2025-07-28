#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script principal pour le système de ciblage de feuilles (adapté pour l'architecture modulaire)
"""

import os
import sys
import argparse
import numpy as np
import time

# Importations des modules de la nouvelle architecture
from core.hardware.cnc_controller import CNCController
from core.hardware.camera_controller import CameraController
from core.hardware.gimbal_controller import GimbalController
from core.data.storage_manager import StorageManager
from core.utils import config

# Importations des modules spécifiques au ciblage
from targeting.modules.data_manager import load_and_scale_pointcloud, compute_cropped_alpha_shape, save_leaves_data
from targeting.modules.leaf_analyzer import calculate_adaptive_radius, build_connectivity_graph
from targeting.modules.leaf_analyzer import detect_communities_louvain_multiple, extract_leaf_data_from_communities
from targeting.modules.interactive_selector import select_leaf_with_matplotlib
from targeting.modules.path_planner import plan_safe_path, plan_complete_path
from targeting.modules.robot_controller import RobotController
from targeting.modules.visualization import visualize_path, visualize_complete_path

class LeafTargeting:
    """Classe principale pour le système de ciblage de feuilles"""
    
    def __init__(self, args=None):
        """
        Initialise le système de ciblage de feuilles
        
        Args:
            args: Arguments de la ligne de commande (optionnel)
        """
        # Paramètres par défaut
        self.point_cloud_path = None
        self.scale = 0.001
        self.alpha = 0.1
        self.crop_method = 'none'
        self.crop_percentage = 0.25
        self.z_offset = 0.0
        self.arduino_port = config.ARDUINO_PORT
        self.simulate = False
        self.auto_photo = False
        self.louvain_coeff = 0.5
        self.distance = 0.1  # Distance par défaut aux feuilles cibles (10 cm)
        
        # Mettre à jour les paramètres avec les arguments de la ligne de commande
        if args:
            self.update_from_args(args)
        
        # Contrôleurs matériels
        self.cnc = None
        self.camera = None
        self.gimbal = None
        self.robot = None
        
        # Gestionnaire de stockage
        self.storage = None
        self.session_dirs = None
        
        # Données
        self.pcd = None
        self.points = None
        self.alpha_pcd = None
        self.alpha_points = None
        self.leaves_data = []
        self.selected_leaves = []
        
        # État
        self.initialized = False
    
    def update_from_args(self, args):
        """Met à jour les paramètres depuis les arguments de la ligne de commande"""
        if hasattr(args, 'point_cloud') and args.point_cloud is not None:
            self.point_cloud_path = args.point_cloud
        
        if hasattr(args, 'scale') and args.scale is not None:
            self.scale = args.scale
        
        if hasattr(args, 'alpha') and args.alpha is not None:
            self.alpha = args.alpha
        
        if hasattr(args, 'crop_method') and args.crop_method is not None:
            self.crop_method = args.crop_method
        
        if hasattr(args, 'crop_percentage') and args.crop_percentage is not None:
            self.crop_percentage = args.crop_percentage
        
        if hasattr(args, 'z_offset') and args.z_offset is not None:
            self.z_offset = args.z_offset
        
        if hasattr(args, 'arduino_port') and args.arduino_port is not None:
            self.arduino_port = args.arduino_port
        
        if hasattr(args, 'simulate') and args.simulate is not None:
            self.simulate = args.simulate
        
        if hasattr(args, 'auto_photo') and args.auto_photo is not None:
            self.auto_photo = args.auto_photo
        
        if hasattr(args, 'louvain_coeff') and args.louvain_coeff is not None:
            self.louvain_coeff = args.louvain_coeff
            
        if hasattr(args, 'distance') and args.distance is not None:
            self.distance = args.distance
    
    def initialize(self):
        """Initialise les composants et les répertoires"""
        if self.initialized:
            return True
        
        try:
            print("\n=== Initialisation du système de ciblage de feuilles ===")
            
            # Vérifier le chemin du nuage de points
            if not self.point_cloud_path:
                print("ERREUR: Chemin du nuage de points non spécifié")
                return False
            
            if not os.path.exists(self.point_cloud_path):
                print(f"ERREUR: Le fichier {self.point_cloud_path} n'existe pas")
                return False
            
            # Créer le gestionnaire de stockage
            self.storage = StorageManager(mode="targeting")
            self.session_dirs = self.storage.create_directory_structure()
            
            print("\nRépertoires créés:")
            for key, path in self.session_dirs.items():
                print(f"- {key}: {path}")
            
            # Initialiser les contrôleurs matériels (uniquement si pas en mode simulation)
            if not self.simulate:
                self.cnc = CNCController(config.CNC_SPEED)
                self.cnc.connect()
                
                self.camera = CameraController()
                self.camera.connect()
                self.camera.set_output_directory(self.session_dirs["images"])
                
                self.gimbal = GimbalController(self.arduino_port)
                self.gimbal.connect()
                
                # Initialiser le contrôleur robot
                self.robot = RobotController(
                    cnc=self.cnc,
                    camera=self.camera,
                    gimbal=self.gimbal,
                    output_dirs=self.session_dirs
                )
            
            # Afficher les paramètres
            print(f"\nParamètres de ciblage:")
            print(f"- Nuage de points: {self.point_cloud_path}")
            print(f"- Facteur d'échelle: {self.scale}")
            print(f"- Valeur alpha: {self.alpha}")
            print(f"- Méthode de cropping: {self.crop_method}")
            print(f"- Distance aux feuilles: {self.distance} m")
            print(f"- Mode simulation: {'Activé' if self.simulate else 'Désactivé'}")
            
            self.initialized = True
            return True
            
        except Exception as e:
            print(f"Erreur d'initialisation: {e}")
            self.shutdown()
            return False
    
    def run_targeting(self):
        """Exécute le processus de ciblage complet"""
        if not self.initialize():
            return False
        
        try:
            # 1. Charger le nuage de points
            print("\n=== 1. Chargement du nuage de points ===")
            self.pcd, self.points = load_and_scale_pointcloud(self.point_cloud_path, self.scale)
            
            # 2. Calculer l'Alpha Shape pour extraire les surfaces
            print("\n=== 2. Calcul de l'Alpha Shape ===")
            self.alpha_pcd, self.alpha_points = compute_cropped_alpha_shape(
                self.pcd, self.points, self.alpha, self.crop_method, self.crop_percentage, 
                self.z_offset, self.session_dirs["analysis"]
            )
            
            # 3. Calculer le rayon de connectivité
            print("\n=== 3. Calcul du rayon de connectivité ===")
            radius = calculate_adaptive_radius(self.alpha_points)
            
            # 4. Coefficient Louvain fourni par l'utilisateur
            print(f"\n=== 4. Coefficient Louvain: {self.louvain_coeff} ===")
            coeff = self.louvain_coeff
            
            # 5. Construire le graphe de connectivité
            print("\n=== 5. Construction du graphe de connectivité ===")
            graph = build_connectivity_graph(self.alpha_points, radius)
            
            # 6. Déterminer la taille minimale des communautés
            min_size = max(10, len(self.alpha_points) // 30)
            print(f"\n=== 6. Taille minimale des communautés: {min_size} points ===")
            
            # 7. Détecter les communautés avec Louvain
            print("\n=== 7. Détection des communautés ===")
            communities = detect_communities_louvain_multiple(graph, coeff, min_size, n_iterations=5)
            
            # 8. Extraire les données des feuilles
            print("\n=== 8. Extraction des données des feuilles ===")
            self.leaves_data = extract_leaf_data_from_communities(communities, self.alpha_points)
            
            # Sauvegarder les données
            leaves_json = os.path.join(self.session_dirs["analysis"], "leaves_data.json")
            save_leaves_data(self.leaves_data, leaves_json)
            
            # 9. Sélection interactive des feuilles
            print("\n=== 9. Sélection interactive des feuilles ===")
            self.selected_leaves = select_leaf_with_matplotlib(
                self.leaves_data, self.points, self.session_dirs["visualizations"]
            )
            
            if not self.selected_leaves:
                print("Aucune feuille sélectionnée. Fin du programme.")
                return True
            
            # 10. Planifier la trajectoire complète
            print("\n=== 10. Planification de la trajectoire complète ===")
            current_position = [0, 0, 0]  # Position actuelle (à remplacer par la position réelle du robot)
            
            # Si en mode non-simulation, obtenir la position réelle
            if not self.simulate and self.cnc:
                pos = self.cnc.get_position()
                current_position = [pos['x'], pos['y'], pos['z']]
            
            # Extraire les points cibles
            target_points = [leaf["target_point"] for leaf in self.selected_leaves]
            
            # Planifier la trajectoire complète avec la distance personnalisée
            complete_path = plan_complete_path(
                current_position, target_points, config.CENTER_POINT, config.CIRCLE_RADIUS, 
                config.NUM_POSITIONS, leaf_distance=self.distance
            )
            
            # 11. Visualiser la trajectoire complète
            print("\n=== 11. Visualisation de la trajectoire complète ===")
            
            # Préparer les données des feuilles sélectionnées pour la visualisation
            leaf_points_list = []
            leaf_normals_list = []
            
            for leaf in self.selected_leaves:
                if 'points' in leaf:
                    leaf_points_list.append(np.array(leaf['points']))
                else:
                    leaf_points_list.append(np.array([leaf['centroid']]))
                
                if 'normal' in leaf:
                    leaf_normals_list.append(np.array(leaf['normal']))
                else:
                    leaf_normals_list.append(np.array([0, 0, 1]))
            
            # Visualiser la trajectoire complète
            visualize_complete_path(
                complete_path, self.points, leaf_points_list, leaf_normals_list, 
                self.session_dirs["visualizations"]
            )
            
            # En mode simulation, s'arrêter ici
            if self.simulate:
                print("\nMode simulation: Fin du programme.")
                return True
            
            # 12. Exécuter la trajectoire
            print("\n=== 12. Exécution de la trajectoire ===")
            
            # Récupérer les centroïdes des feuilles et leurs IDs
            leaf_centroids = [leaf['centroid'] for leaf in self.selected_leaves]
            leaf_ids = [leaf['id'] for leaf in self.selected_leaves]
            
            # Exécuter la trajectoire complète
            success = self.robot.execute_path(
                complete_path,
                leaf_centroids=leaf_centroids,
                leaf_ids=leaf_ids,
                auto_photo=self.auto_photo,
                stabilization_time=config.STABILIZATION_TIME
            )
            
            if success:
                print("\nTrajectoire terminée avec succès.")
            else:
                print("\nErreur lors de l'exécution de la trajectoire.")
            
            return success
            
        except KeyboardInterrupt:
            print("\nProgramme interrompu par l'utilisateur.")
            return False
        except Exception as e:
            print(f"\nUne erreur est survenue: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Arrête proprement le système"""
        print("\nArrêt du système de ciblage...")
        
        # Arrêter les contrôleurs dans l'ordre inverse d'initialisation
        if hasattr(self, 'robot') and self.robot and not self.simulate:
            self.robot.shutdown()
        elif not self.simulate:
            if hasattr(self, 'gimbal') and self.gimbal:
                self.gimbal.shutdown()
            
            if hasattr(self, 'camera') and self.camera:
                self.camera.shutdown()
            
            if hasattr(self, 'cnc') and self.cnc:
                self.cnc.shutdown()
        
        self.initialized = False
        print("Système de ciblage arrêté.")


def parse_arguments():
    """Parse les arguments de la ligne de commande"""
    parser = argparse.ArgumentParser(description='Système de ciblage de feuilles')
    
    parser.add_argument('point_cloud', help='Fichier de nuage de points (PLY/PCD)')
    parser.add_argument('--scale', type=float, default=0.001, help='Facteur d\'échelle pour le nuage de points (défaut: 0.001 = mm->m)')
    parser.add_argument('--alpha', type=float, default=0.1, help='Valeur alpha pour Alpha Shape (défaut: 0.1)')
    parser.add_argument('--crop_method', choices=['none', 'top_percentage', 'single_furthest'], 
                      default='none', help='Méthode de cropping (défaut: none)')
    parser.add_argument('--crop_percentage', type=float, default=0.25, help='Pourcentage pour top_percentage (défaut: 0.25)')
    parser.add_argument('--z_offset', type=float, default=0.0, help='Décalage Z pour le cropping (défaut: 0.0)')
    parser.add_argument('--arduino_port', default=config.ARDUINO_PORT, help=f'Port série Arduino (défaut: {config.ARDUINO_PORT})')
    parser.add_argument('--simulate', action='store_true', help='Mode simulation (sans contrôle robot)')
    parser.add_argument('--auto_photo', action='store_true', help='Prendre automatiquement des photos à chaque cible')
    parser.add_argument('--louvain_coeff', type=float, default=0.5, help='Coefficient pour la détection Louvain (défaut: 0.5)')
    parser.add_argument('--distance', type=float, default=0.1, help='Distance aux feuilles cibles en mètres (défaut: 0.1 m)')
    
    return parser.parse_args()

def main():
    """Fonction principale compatible avec l'implémentation originale"""
    args = parse_arguments()
    targeting = LeafTargeting(args)
    success = targeting.run_targeting()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())