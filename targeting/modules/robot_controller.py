# targeting/modules/robot_controller.py
import time
import math
import numpy as np
import os
from datetime import datetime

class RobotController:
    def __init__(self, cnc=None, camera=None, gimbal=None, output_dirs=None, speed=0.1, update_interval=0.1):
        """
        Initialise le contrôleur du robot
        
        Args:
            cnc: Instance de CNCController
            camera: Instance de CameraController
            gimbal: Instance de GimbalController
            output_dirs: Dictionnaire des répertoires de sortie
            speed: Vitesse de déplacement (m/s)
            update_interval: Intervalle de mise à jour pendant le mouvement (s)
        """
        self.cnc = cnc
        self.camera = camera
        self.gimbal = gimbal
        self.speed = speed
        self.update_interval = update_interval
        
        # Dossier pour les photos
        self.photos_dir = None
        if output_dirs and 'images' in output_dirs:
            self.photos_dir = output_dirs['images']
        
        # État
        self.initialized = cnc is not None and camera is not None and gimbal is not None
        
        if self.initialized:
            print("Contrôleur robot initialisé avec succès.")
        else:
            print("Contrôleur robot partiellement initialisé - certains composants manquants.")
    
    def execute_path(self, path, leaf_centroids=None, leaf_ids=None, auto_photo=True, stabilization_time=3.0):
        """
        Exécute une trajectoire complète
        
        Args:
            path: Liste de dictionnaires décrivant la trajectoire
            leaf_centroids: Liste des positions des centroïdes des feuilles
            leaf_ids: Liste des IDs des feuilles correspondant aux centroïdes
            auto_photo: Prendre automatiquement des photos aux points cibles
            stabilization_time: Temps d'attente pour la stabilisation avant la photo (en secondes)
        
        Returns:
            True si l'exécution est réussie, False sinon
        """
        if not self.initialized:
            print("Erreur: Le robot n'est pas complètement initialisé.")
            return False
        
        try:
            # Variables pour suivre les feuilles
            current_leaf_index = 0
            photos_taken = []
            
            # Identifier les points cibles et les derniers points intermédiaires avant chaque cible
            target_indices = []
            for i, point_info in enumerate(path):
                if point_info["type"] == "target":
                    target_indices.append(i)
            
            # Parcourir le chemin
            for i, point_info in enumerate(path):
                position = point_info["position"]
                point_type = point_info["type"]
                comment = point_info.get("comment", "")
                
                print(f"\n--- Étape {i+1}/{len(path)}: {point_type} ---")
                if comment:
                    print(f"Info: {comment}")
                
                # Déplacement vers ce point
                success = self.cnc.move_to(
                    position[0], position[1], position[2], wait=True
                )
                
                if not success:
                    print(f"Erreur lors du déplacement à l'étape {i+1}")
                    continue
                
                # Vérifier si nous sommes au dernier point intermédiaire avant un point cible
                # c'est-à-dire un point via_point suivi directement par un point target
                if point_type == "via_point" and i+1 < len(path) and path[i+1]["type"] == "target":
                    # Trouver l'indice de la prochaine feuille
                    next_target_index = i + 1
                    next_leaf_index = target_indices.index(next_target_index)
                    
                    if leaf_centroids is not None and next_leaf_index < len(leaf_centroids):
                        print(f"\n--- Orientation vers la feuille au dernier point intermédiaire ---")
                        
                        # Obtenir la position actuelle
                        final_pos = self.cnc.get_position()
                        
                        # Obtenir le centroïde de la prochaine feuille
                        next_leaf_centroid = leaf_centroids[next_leaf_index]
                        
                        print(f"DEBUG: Orientation vers le centroïde: {next_leaf_centroid}")
                        
                        # Orienter la caméra vers le centroïde de la prochaine feuille
                        success = self.gimbal.aim_at_target(final_pos, next_leaf_centroid, wait=True, invert_tilt=True)
                        
                        if not success:
                            print("Erreur lors de l'orientation vers la feuille")
                        else:
                            print("Caméra orientée avec succès vers la feuille")
                
                # Si c'est un point cible et qu'on a des centroïdes de feuilles
                if point_type == "target" and leaf_centroids is not None and current_leaf_index < len(leaf_centroids):
                    # Récupérer les informations de la feuille actuelle
                    leaf_centroid = leaf_centroids[current_leaf_index]
                    leaf_id = leaf_ids[current_leaf_index] if leaf_ids and current_leaf_index < len(leaf_ids) else None
                    
                    print(f"\n--- Orientation vers la feuille {leaf_id if leaf_id is not None else ''} ---")
                    
                    # Obtenir la position finale
                    final_pos = self.cnc.get_position()
                    
                    # Afficher des informations de débogage sur le centroïde original
                    print(f"DEBUG: Ajustement fin vers le centroïde: {leaf_centroid}")
                    
                    # Orienter la caméra vers la feuille avec inversion du tilt
                    # Nous utilisons le centroïde original sans modification,
                    # et nous inversons le tilt dans la méthode aim_at_target
                    success = self.gimbal.aim_at_target(final_pos, leaf_centroid, wait=True, invert_tilt=True)
                    
                    if not success:
                        print("Erreur lors de l'orientation vers la feuille")
                        current_leaf_index += 1
                        continue
                    
                    # Pause pour stabilisation
                    print(f"Stabilisation pendant {stabilization_time} secondes...")
                    time.sleep(stabilization_time)
                    
                    # Prendre automatiquement une photo si demandé
                    if auto_photo:
                        timestamp = time.strftime("%Y%m%d-%H%M%S")
                        if leaf_id is not None:
                            filename = f"leaf_{leaf_id}_{timestamp}.jpg"
                        else:
                            filename = f"leaf_target_{current_leaf_index+1}_{timestamp}.jpg"
                        
                        # Créer un dictionnaire avec les informations de pose de la caméra
                        camera_pose = {
                            'x': final_pos['x'],
                            'y': final_pos['y'],
                            'z': final_pos['z'],
                            'pan_angle': self.gimbal.current_pan,
                            'tilt_angle': self.gimbal.current_tilt
                        }
                        
                        photo_path, _ = self.camera.take_photo(filename, camera_pose)
                        
                        if photo_path:
                            photos_taken.append((photo_path, leaf_id))
                            print(f"Photo prise: {photo_path}")
                    else:
                        # Proposer de prendre une photo manuellement
                        take_photo = input("\nPrendre une photo? (o/n): ").lower()
                        if take_photo == 'o':
                            timestamp = time.strftime("%Y%m%d-%H%M%S")
                            if leaf_id is not None:
                                filename = f"leaf_{leaf_id}_{timestamp}.jpg"
                            else:
                                filename = f"leaf_target_{current_leaf_index+1}_{timestamp}.jpg"
                            
                            # Créer un dictionnaire avec les informations de pose de la caméra
                            camera_pose = {
                                'x': final_pos['x'],
                                'y': final_pos['y'],
                                'z': final_pos['z'],
                                'pan_angle': self.gimbal.current_pan,
                                'tilt_angle': self.gimbal.current_tilt
                            }
                            
                            photo_path, _ = self.camera.take_photo(filename, camera_pose)
                            
                            if photo_path:
                                photos_taken.append((photo_path, leaf_id))
                                print(f"Photo prise: {photo_path}")
                    
                    # Incrémenter l'index de la feuille
                    current_leaf_index += 1
            
            # Résumé des photos prises
            if photos_taken:
                print("\n=== RÉSUMÉ DES PHOTOS PRISES ===")
                for i, (path, leaf_id) in enumerate(photos_taken):
                    print(f"{i+1}. Feuille {leaf_id if leaf_id is not None else '?'}: {path}")
            
            return True
            
        except Exception as e:
            print(f"Erreur lors de l'exécution de la trajectoire: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def normalize_angle_difference(self, delta):
        """Normalise la différence d'angle pour prendre le chemin le plus court"""
        if delta > 180:
            delta -= 360
        elif delta < -180:
            delta += 360
        return delta
    
    def shutdown(self):
        """Arrête proprement le robot"""
        print("Arrêt du robot...")
        
        # Réaliser les mêmes opérations que dans l'ancienne version
        if self.cnc is not None:
            try:
                print("Déplacement vers la position (0, 0, 0)...")
                self.cnc.move_to(0, 0, 0, wait=True)
                
                print("Retour à la position d'origine (homing)...")
                self.cnc.home()  # Exécute un homing explicite ici
                
                # Nous ne faisons pas le power_down ici car il sera fait par le contrôleur principal
            except Exception as e:
                print(f"Erreur lors du retour à l'origine: {e}")
        
        # Réinitialisation de la caméra
        if self.gimbal is not None:
            try:
                print("Remise de la caméra à la position initiale (0,0)...")
                self.gimbal.reset_position()
            except Exception as e:
                print(f"Erreur lors de la remise à zéro de la caméra: {e}")
        
        return True