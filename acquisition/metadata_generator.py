#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Générateur de métadonnées pour les images d'acquisition
"""

import os
import json
from datetime import datetime

class MetadataGenerator:
    def __init__(self, storage_manager):
        """
        Initialise le générateur de métadonnées
        
        Args:
            storage_manager: Instance de StorageManager
        """
        self.storage = storage_manager
        self.dirs = storage_manager.dirs
    
    def create_image_metadata(self, image_id, camera_pose, output_dir=None):
        """
        Crée les métadonnées au format JSON pour une image donnée
        
        Args:
            image_id: Identifiant de l'image (ex: "00059_rgb")
            camera_pose: Dictionnaire contenant la pose de la caméra
            output_dir: Répertoire de sortie pour le fichier JSON (optionnel)
            
        Returns:
            Chemin vers le fichier JSON créé
        """
        try:
            # Extraire les valeurs de pose
            x, y, z = camera_pose['x'], camera_pose['y'], camera_pose['z']
            
            # Récupérer les angles pan et tilt
            pan_angle = camera_pose.get('pan_angle', 0)
            tilt_angle = camera_pose.get('tilt_angle', 0)
            
            # Formater l'ID pour le shot_id (retirer "rgb")
            shot_id = image_id.split('_')[0]
            
            # Créer le dictionnaire de métadonnées
            metadata = {
                "approximate_pose": [
                    x * 1000,  # Conversion en mm selon les exemples
                    y * 1000,
                    z * 1000,
                    pan_angle,
                    0  # Dernier élément du tableau, à 0 selon les exemples
                ],
                "channel": "rgb",
                "shot_id": shot_id
            }
            
            # Déterminer le répertoire de sortie
            if output_dir is None:
                if self.dirs and "metadata_images" in self.dirs:
                    output_dir = self.dirs["metadata_images"]
                else:
                    raise ValueError("Répertoire de sortie non spécifié et non disponible dans self.dirs")
            
            # Chemin complet pour le fichier JSON
            json_path = os.path.join(output_dir, f"{image_id}.json")
            
            # Créer le répertoire si nécessaire
            os.makedirs(os.path.dirname(json_path), exist_ok=True)
            
            # Sauvegarder le fichier JSON
            with open(json_path, 'w') as f:
                json.dump(metadata, f, indent=4)
                
            print(f"Métadonnées sauvegardées: {json_path}")
            return json_path
            
        except Exception as e:
            print(f"Erreur lors de la création des métadonnées: {e}")
            return None
    
    def create_images_json(self, workspace):
        """
        Crée le fichier images.json dans le répertoire metadata
        
        Args:
            workspace: Valeurs pour la section workspace du fichier
            
        Returns:
            Chemin vers le fichier JSON créé
        """
        try:
            # Vérifier que le répertoire metadata existe
            if not self.dirs or "metadata" not in self.dirs:
                raise ValueError("Répertoire metadata non défini dans self.dirs")
            
            # Créer le dictionnaire images.json
            images_json = {
                "channels": [
                    "rgb"
                ],
                "hardware": {
                    "X_motor": "X-Carve NEMA23",
                    "Y_motor": "X-Carve NEMA23",
                    "Z_motor": "X-Carve NEMA23",
                    "frame": "30profile v1",
                    "pan_motor": "iPower Motor GM4108H-120T Brushless Gimbal Motor",
                    "sensor": "RX0",
                    "tilt_motor": "None"
                },
                "object": {
                    "DAG": 40,
                    "dataset_id": "3dt",
                    "experiment_id": "3dt_" + datetime.now().strftime("%d-%m-%Y"),
                    "growth_conditions": "SD+LD",
                    "growth_environment": "Lyon-indoor",
                    "plant_id": "3dt_chenoA",
                    "sample": "main_stem",
                    "seed_stock": "Col-0",
                    "species": "chenopodium album",
                    "treatment": "None"
                },
                "task_name": "ImagesFilesetExists",
                "task_params": {
                    "fileset_id": "images",
                    "scan_id": "Col_A_" + datetime.now().strftime("%Y-%m-%d")
                },
                "workspace": workspace
            }
            
            # Chemin pour le fichier JSON
            json_path = os.path.join(self.dirs["metadata"], "images.json")
            
            # Créer le répertoire si nécessaire
            os.makedirs(os.path.dirname(json_path), exist_ok=True)
            
            # Sauvegarder le fichier
            with open(json_path, 'w') as f:
                json.dump(images_json, f, indent=4)
            
            print(f"Fichier images.json créé: {json_path}")
            return json_path
            
        except Exception as e:
            print(f"Erreur lors de la création du fichier images.json: {e}")
            return None
    
    def create_files_json(self, photo_files):
        """
        Crée le fichier files.json à la racine du répertoire principal
        
        Args:
            photo_files: Liste des noms de fichiers des photos prises
            
        Returns:
            Chemin vers le fichier JSON créé
        """
        try:
            # Vérifier que le répertoire principal existe
            if not self.dirs or "main" not in self.dirs:
                raise ValueError("Répertoire principal non défini dans self.dirs")
            
            # Structure de base
            files_json = {
                "filesets": [
                    {
                        "files": [],
                        "id": "images"
                    }
                ]
            }
            
            # Ajouter chaque photo à la liste des fichiers
            for photo_file in photo_files:
                # S'assurer que nous avons juste le nom du fichier sans le chemin
                filename = os.path.basename(photo_file)
                file_id = os.path.splitext(filename)[0]
                
                # Ajouter à la liste
                files_json["filesets"][0]["files"].append({
                    "file": filename,
                    "id": file_id
                })
            
            # Chemin pour le fichier JSON
            json_path = os.path.join(self.dirs["main"], "files.json")
            
            # Créer le répertoire si nécessaire
            os.makedirs(os.path.dirname(json_path), exist_ok=True)
            
            # Sauvegarder le fichier
            with open(json_path, 'w') as f:
                json.dump(files_json, f, indent=4)
            
            print(f"Fichier files.json créé: {json_path}")
            return json_path
            
        except Exception as e:
            print(f"Erreur lors de la création du fichier files.json: {e}")
            return None
    
    def create_scan_toml(self, num_positions, num_circles, radius, z_offset):
        """
        Crée le fichier scan.toml à la racine du répertoire principal
        
        Args:
            num_positions: Nombre de positions par cercle
            num_circles: Nombre de cercles
            radius: Rayon des cercles en mètres
            z_offset: Décalage en Z entre les cercles en mètres
            
        Returns:
            Chemin vers le fichier TOML créé
        """
        try:
            # Vérifier que le répertoire principal existe
            if not self.dirs or "main" not in self.dirs:
                raise ValueError("Répertoire principal non défini dans self.dirs")
            
            # Contenu du fichier TOML
            scan_toml_content = f"""[ScanPath]
class_name = "Circle"

[retcode]
already_running = 10
missing_data = 20
not_run = 25
task_failed = 30
scheduling_error = 35
unhandled_exception = 40

[ScanPath.kwargs]
center_x = 375
center_y = 350
z = 80
tilt = 0
radius = {int(radius * 1000)}
n_points = {num_positions * num_circles}

[Scan.scanner.camera]
module = "romiscanner.sony"

[Scan.scanner.gimbal]
module = "romiscanner.blgimbal"

[Scan.scanner.cnc]
module = "romiscanner.grbl"

[Scan.metadata.workspace]
x = [ 200, 600,]
y = [ 200, 600,]
z = [ -100, 300,]

[Scan.metadata.object]
species = "chenopodium album"
seed_stock = "Col-0"
plant_id = "3dt_chenoA"
growth_environment = "Lyon-indoor"
growth_conditions = "SD+LD"
treatment = "None"
DAG = 40
sample = "main_stem"
experiment_id = "3dt_{datetime.now().strftime("%d-%m-%Y")}"
dataset_id = "3dt"

[Scan.metadata.hardware]
frame = "30profile v1"
X_motor = "X-Carve NEMA23"
Y_motor = "X-Carve NEMA23"
Z_motor = "X-Carve NEMA23"
pan_motor = "iPower Motor GM4108H-120T Brushless Gimbal Motor"
tilt_motor = "None"
sensor = "RX0"

[Scan.scanner.camera.kwargs]
device_ip = "192.168.122.1"
api_port = "10000"
postview = true
use_flashair = false
rotation = 270

[Scan.scanner.gimbal.kwargs]
port = "/dev/ttyACM1"
has_tilt = false
zero_pan = 0
invert_rotation = true

[Scan.scanner.cnc.kwargs]
homing = true
port = "/dev/ttyACM0"
"""
            
            # Chemin pour le fichier TOML
            toml_path = os.path.join(self.dirs["main"], "scan.toml")
            
            # Créer le répertoire si nécessaire
            os.makedirs(os.path.dirname(toml_path), exist_ok=True)
            
            # Sauvegarder le fichier
            with open(toml_path, 'w') as f:
                f.write(scan_toml_content)
            
            print(f"Fichier scan.toml créé: {toml_path}")
            return toml_path
            
        except Exception as e:
            print(f"Erreur lors de la création du fichier scan.toml: {e}")
            return None