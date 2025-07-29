#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module d'acquisition d'images en cercle intégré dans l'architecture modulaire
"""

import time
import os
import argparse
from core.hardware.cnc_controller import CNCController
from core.hardware.camera_controller import CameraController
from core.hardware.gimbal_controller import GimbalController
from core.geometry.path_calculator import plan_multi_circle_path
from core.data.storage_manager import StorageManager
from acquisition.metadata_generator import MetadataGenerator
from core.utils import config

class CircleAcquisition:
    def __init__(self, args=None):
        """
        Initialise le module d'acquisition en cercle
        
        Args:
            args: Arguments de la ligne de commande (optionnel)
        """
        # Paramètres par défaut
        self.num_circles = 1
        self.num_positions = config.NUM_POSITIONS
        self.circle_radius = config.CIRCLE_RADIUS
        self.z_offset = config.Z_OFFSET
        self.arduino_port = config.ARDUINO_PORT
        self.cnc_speed = config.CNC_SPEED
        self.update_interval = config.UPDATE_INTERVAL
        self.target_point = config.TARGET_POINT
        
        # Mettre à jour les paramètres avec les arguments de la ligne de commande
        if args:
            self.update_from_args(args)
        
        # Contrôleurs matériels
        self.cnc = None
        self.camera = None
        self.gimbal = None
        
        # Gestionnaire de stockage
        self.storage = None
        self.metadata_generator = None
        
        # Données de session
        self.photos_taken = []
        self.metadata_files = []
        self.session_dirs = None
        
        # État
        self.initialized = False
    
    def update_from_args(self, args):
        """Met à jour les paramètres depuis les arguments de la ligne de commande"""
        if hasattr(args, 'circles') and args.circles is not None:
            self.num_circles = args.circles
        
        if hasattr(args, 'positions') and args.positions is not None:
            self.num_positions = args.positions
        
        if hasattr(args, 'radius') and args.radius is not None:
            self.circle_radius = args.radius
        
        if hasattr(args, 'z_offset') and args.z_offset is not None:
            self.z_offset = args.z_offset
        
        if hasattr(args, 'arduino_port') and args.arduino_port is not None:
            self.arduino_port = args.arduino_port
        
        if hasattr(args, 'speed') and args.speed is not None:
            self.cnc_speed = args.speed
    
    def initialize(self):
        """Initialise les composants matériels et les répertoires"""
        if self.initialized:
            return True
        
        try:
            print("\n=== Initialisation du système d'acquisition en cercle ===")
            
            # Créer le gestionnaire de stockage
            self.storage = StorageManager(mode="acquisition")
            self.session_dirs = self.storage.create_directory_structure()
            
            # Afficher les répertoires pour débogage
            print("\nRépertoires créés:")
            for key, path in self.session_dirs.items():
                print(f"- {key}: {path}")
            
            # Créer le générateur de métadonnées
            self.metadata_generator = MetadataGenerator(self.storage)
            
            # Initialiser les contrôleurs matériels
            self.cnc = CNCController(self.cnc_speed)
            self.cnc.connect()
            
            self.camera = CameraController()
            self.camera.connect()
            self.camera.set_output_directory(self.session_dirs["images"])
            
            self.gimbal = GimbalController(self.arduino_port)
            self.gimbal.connect()
            
            # Afficher les paramètres
            print(f"\nParamètres d'acquisition:")
            print(f"- Point cible: {self.target_point}")
            print(f"- Centre du cercle: {config.CENTER_POINT}")
            print(f"- Rayon: {self.circle_radius} m")
            print(f"- Nombre de cercles: {self.num_circles}")
            print(f"- Positions par cercle: {self.num_positions}")
            print(f"- Nombre total de photos: {self.num_positions * self.num_circles}")
            if self.num_circles > 1:
                print(f"- Décalage en Z: {self.z_offset} m")
            
            self.initialized = True
            return True
            
        except Exception as e:
            print(f"Erreur d'initialisation: {e}")
            self.shutdown()
            return False
    
    def run_acquisition(self):
        """Exécute le processus d'acquisition complet"""
        if not self.initialize():
            return False
        
        try:
            # Position initiale pour le calcul du chemin
            current_pos = self.cnc.get_position()
            start_point = (current_pos['x'], current_pos['y'], current_pos['z'])
            
            # Planifier le chemin sur le(s) cercle(s)
            path = plan_multi_circle_path(
                center=config.CENTER_POINT,
                radius=self.circle_radius,
                num_positions=self.num_positions,
                num_circles=self.num_circles,
                z_offset=self.z_offset,
                start_point=start_point
            )
            
            print(f"\nChemin planifié: {len(path)} points")
            
            # Demander confirmation
            input("\nAppuyez sur Entrée pour commencer l'acquisition d'images...")
            
            # Orientation initiale de la caméra vers le point cible
            print("\nOrientation initiale de la caméra vers le point cible...")
            self.gimbal.aim_at_target(current_pos, self.target_point)
            
            # Variables pour suivre la position de la caméra
            photo_index = 0
            
            # Parcourir le chemin
            for i, point_info in enumerate(path):
                position = point_info["position"]
                point_type = point_info["type"]
                comment = point_info.get("comment", "")
                
                print(f"\n--- Point {i+1}/{len(path)}: {point_type} ---")
                if comment:
                    print(f"Info: {comment}")
                
                # Déplacement vers la position
                success = self.cnc.move_to(
                    position[0], position[1], position[2], wait=True
                )
                
                if not success:
                    print(f"Erreur lors du déplacement au point {i+1}")
                    continue
                
                # Si c'est un point de passage sur le cercle (où on prend une photo)
                if point_type == "via_point" and "Position" in comment:
                    # Obtenir la position finale
                    final_pos = self.cnc.get_position()
                    
                    # Orientation finale de la caméra
                    print("Ajustement final de la caméra...")
                    self.gimbal.aim_at_target(final_pos, self.target_point, wait=True)
                    
                    # Pause pour stabilisation
                    print(f"Stabilisation pendant {config.STABILIZATION_TIME} secondes...")
                    time.sleep(config.STABILIZATION_TIME)
                    
                    # Créer un dictionnaire avec les informations de pose de la caméra
                    camera_pose = {
                        'x': final_pos['x'],
                        'y': final_pos['y'],
                        'z': final_pos['z'],
                        'pan_angle': self.gimbal.current_pan,
                        'tilt_angle': self.gimbal.current_tilt
                    }
                    
                    # Prendre une photo
                    print(f"Prise de photo {photo_index+1}...")
                    image_id = f"{photo_index:05d}_rgb"
                    filename = f"{image_id}.jpg"
                    
                    photo_path, _ = self.camera.take_photo(filename, camera_pose)
                    
                    if photo_path:
                        # Générer les métadonnées
                        json_path = self.metadata_generator.create_image_metadata(
                            image_id, camera_pose, self.session_dirs["metadata_images"]
                        )
                        
                        # Ajouter aux listes
                        self.photos_taken.append(photo_path)
                        self.metadata_files.append(json_path)
                        
                        print(f"Photo {photo_index+1} prise avec succès")
                        photo_index += 1
                    else:
                        print(f"Échec de la prise de photo à la position {i+1}")
            
            # Génération des fichiers de métadonnées finaux
            print("\nGénération des fichiers de métadonnées...")
            
            # Vérifier que les répertoires existent
            if not self.session_dirs:
                print("ERREUR: Les répertoires de session n'ont pas été créés")
                return False
            
            # Générer workspace.json
            workspace = {
                "x": [225, 525],
                "y": [220, 520],
                "z": [200, 500]
            }
            self.metadata_generator.create_images_json(workspace)
            
            # Extraire les noms de fichiers (sans le chemin complet)
            # Même si self.photos_taken est vide, on génère quand même les fichiers
            photo_filenames = []
            if self.photos_taken:
                photo_filenames = [os.path.basename(path) for path in self.photos_taken]
            
            # Générer files.json (même si photo_filenames est vide)
            self.metadata_generator.create_files_json(photo_filenames)
            
            # Générer scan.toml (indépendamment des photos)
            self.metadata_generator.create_scan_toml(
                self.num_positions, self.num_circles, self.circle_radius, self.z_offset
            )
            
            print(f"\nMétadonnées générées:")
            print(f"- images.json: {os.path.join(self.session_dirs['metadata'], 'images.json')}")
            print(f"- files.json: {os.path.join(self.session_dirs['main'], 'files.json')}")
            print(f"- scan.toml: {os.path.join(self.session_dirs['main'], 'scan.toml')}")
            
            if not self.photos_taken:
                print("Note: files.json généré sans photos car aucune photo n'a été prise")
            
            print("\nAcquisition d'images terminée!")
            print(f"Nombre total de photos prises: {len(self.photos_taken)}/{self.num_positions*self.num_circles}")
            print(f"Photos sauvegardées dans: {self.session_dirs['images']}")
            print(f"Métadonnées sauvegardées dans: {self.session_dirs['metadata_images']}")
            
            return True
            
        except KeyboardInterrupt:
            print("\nAcquisition interrompue par l'utilisateur")
            return False
        except Exception as e:
            print(f"\nUne erreur est survenue: {e}")
            return False
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Arrête proprement le système"""
        print("\nArrêt du système d'acquisition...")
        
        # Arrêter les contrôleurs dans l'ordre inverse d'initialisation
        if hasattr(self, 'gimbal') and self.gimbal:
            self.gimbal.shutdown()
        
        if hasattr(self, 'camera') and self.camera:
            self.camera.shutdown()
        
        if hasattr(self, 'cnc') and self.cnc:
            self.cnc.shutdown()
        
        self.initialized = False
        print("Système d'acquisition arrêté.")