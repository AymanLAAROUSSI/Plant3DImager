#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module de contrôle manuel du robot
Permet à l'utilisateur d'envoyer des commandes directes au format "x y z pan tilt [photo]"
"""

import time
import sys
import os
from core.hardware.cnc_controller import CNCController
from core.hardware.camera_controller import CameraController
from core.hardware.gimbal_controller import GimbalController
from core.data.storage_manager import StorageManager
from core.utils import config

class ManualController:
    def __init__(self, args=None):
        """
        Initialise le contrôleur manuel
        
        Args:
            args: Arguments de la ligne de commande (optionnel)
        """
        # Paramètres par défaut
        self.arduino_port = config.ARDUINO_PORT
        self.cnc_speed = config.CNC_SPEED
        
        # Mettre à jour les paramètres avec les arguments de la ligne de commande
        if args:
            self.update_from_args(args)
        
        # Contrôleurs matériels
        self.cnc = None
        self.camera = None
        self.gimbal = None
        
        # État
        self.initialized = False
    
    def update_from_args(self, args):
        """Met à jour les paramètres depuis les arguments de la ligne de commande"""
        if hasattr(args, 'arduino_port') and args.arduino_port is not None:
            self.arduino_port = args.arduino_port
        
        if hasattr(args, 'speed') and args.speed is not None:
            self.cnc_speed = args.speed
    
    def initialize(self):
        """Initialise les composants matériels"""
        if self.initialized:
            return True
        
        try:
            print("\n=== Initialisation du contrôleur manuel ===")
            
            # Créer le répertoire pour les photos manuelles
            photos_dir = os.path.join(config.RESULTS_DIR, "manual_control")
            os.makedirs(photos_dir, exist_ok=True)
            
            # Initialiser les contrôleurs matériels
            self.cnc = CNCController(self.cnc_speed)
            self.cnc.connect()
            
            self.camera = CameraController()
            self.camera.connect()
            self.camera.set_output_directory(photos_dir)
            
            self.gimbal = GimbalController(self.arduino_port)
            self.gimbal.connect()
            
            # Afficher les paramètres
            print(f"\nParamètres de contrôle:")
            print(f"- Port Arduino: {self.arduino_port}")
            print(f"- Vitesse CNC: {self.cnc_speed} m/s")
            print(f"- Dossier photos: {photos_dir}")
            print(f"- Temps de stabilisation: {config.STABILIZATION_TIME} secondes")
            
            # Obtenir et afficher la position initiale
            position = self.cnc.get_position()
            print(f"\nPosition initiale: X={position['x']:.3f}, Y={position['y']:.3f}, Z={position['z']:.3f}")
            print(f"Angles initiaux: Pan={self.gimbal.current_pan:.3f}°, Tilt={self.gimbal.current_tilt:.3f}°")
            
            self.initialized = True
            return True
            
        except Exception as e:
            print(f"Erreur d'initialisation: {e}")
            self.shutdown()
            return False
    
    def parse_command(self, command):
        """
        Parse une commande utilisateur
        
        Args:
            command: Chaîne de commande au format "x y z [pan] [tilt] [photo]" ou "q" pour quitter
            
        Returns:
            Tuple (action, params) où action est "move", "exit" ou "help",
            et params est un dictionnaire de paramètres ou None
        """
        command = command.strip().lower()
        
        # Commande de sortie
        if command in ('q', 'quit', 'exit'):
            return ("exit", None)
        
        # Commande d'aide
        if command in ('h', 'help', '?'):
            return ("help", None)
            
        # Commande de déplacement
        parts = command.split()
        
        # Format attendu: x y z [pan] [tilt] [photo]
        if len(parts) >= 3:
            try:
                params = {
                    'x': float(parts[0]),
                    'y': float(parts[1]),
                    'z': float(parts[2]),
                    'take_photo': False  # Par défaut, pas de photo
                }
                
                # Angles optionnels
                if len(parts) >= 4:
                    params['pan'] = float(parts[3])
                
                if len(parts) >= 5:
                    params['tilt'] = float(parts[4])
                
                # Option photo (1=oui, 0=non)
                if len(parts) >= 6:
                    params['take_photo'] = parts[5] == '1'
                
                return ("move", params)
            except ValueError:
                print("Erreur: Format invalide. Utilisez des nombres pour x, y, z, pan, tilt.")
                return ("invalid", None)
        
        # Commande invalide
        print("Commande non reconnue. Tapez 'help' pour obtenir de l'aide.")
        return ("invalid", None)
    
    def show_help(self):
        """Affiche l'aide sur les commandes disponibles"""
        print("\n=== AIDE CONTRÔLE MANUEL ===")
        print("Commandes disponibles:")
        print("  x y z [pan] [tilt] [photo]  - Déplace le robot à la position (x,y,z) et oriente la caméra")
        print("                                 Photo: 1 pour prendre une photo, 0 ou omis pour ne pas en prendre")
        print("                                 Exemple: '0.3 0.4 0.1 45 20 1'")
        print("  h, help, ?                  - Affiche cette aide")
        print("  q, quit, exit               - Quitte le programme")
        print("\nNote: Toutes les positions sont en mètres, les angles en degrés.")
        print("      Les paramètres pan, tilt et photo sont optionnels.")
        print(f"      Un délai de stabilisation de {config.STABILIZATION_TIME} secondes est appliqué avant chaque photo.")
    
    def take_photo(self):
        """Prend une photo à la position actuelle"""
        if not self.initialized:
            print("Erreur: Le contrôleur n'est pas initialisé.")
            return None
        
        try:
            # Pause pour stabilisation avant la prise de photo
            print(f"Stabilisation pendant {config.STABILIZATION_TIME} secondes...")
            time.sleep(config.STABILIZATION_TIME)
            
            # Obtenir la position actuelle
            position = self.cnc.get_position()
            
            # Créer un dictionnaire avec les informations de pose de la caméra
            camera_pose = {
                'x': position['x'],
                'y': position['y'],
                'z': position['z'],
                'pan_angle': self.gimbal.current_pan,
                'tilt_angle': self.gimbal.current_tilt
            }
            
            # Générer un nom de fichier
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"manual_{timestamp}.jpg"
            
            # Prendre la photo
            print("Prise de photo en cours...")
            photo_path, _ = self.camera.take_photo(filename, camera_pose)
            
            if photo_path:
                print(f"Photo prise et sauvegardée: {photo_path}")
                return photo_path
            else:
                print("Erreur: Impossible de prendre la photo.")
                return None
                
        except Exception as e:
            print(f"Erreur lors de la prise de photo: {e}")
            return None
    
    def run_manual_control(self):
        """Exécute le mode de contrôle manuel"""
        if not self.initialize():
            return False
        
        try:
            print("\n=== MODE CONTRÔLE MANUEL ===")
            print("Entrez des commandes au format 'x y z [pan] [tilt] [photo]' ou 'q' pour quitter.")
            print("Photo: 1 pour prendre une photo, 0 ou omis pour ne pas en prendre")
            print("Tapez 'help' pour obtenir de l'aide.")
            
            while True:
                # Obtenir la commande de l'utilisateur
                command = input("\nCommande > ")
                
                # Parser la commande
                action, params = self.parse_command(command)
                
                # Exécuter l'action
                if action == "exit":
                    print("Sortie du mode de contrôle manuel...")
                    break
                
                elif action == "help":
                    self.show_help()
                
                elif action == "move":
                    try:
                        # Déplacement du robot
                        x, y, z = params['x'], params['y'], params['z']
                        print(f"Déplacement vers X={x:.3f}, Y={y:.3f}, Z={z:.3f}...")
                        
                        self.cnc.move_to(x, y, z, wait=True)
                        
                        # Orientation de la caméra si des angles sont spécifiés
                        if 'pan' in params or 'tilt' in params:
                            current_pos = self.cnc.get_position()
                            
                            # Obtenir les angles actuels
                            current_pan, current_tilt = self.gimbal.current_pan, self.gimbal.current_tilt
                            
                            # Calculer les deltas
                            delta_pan = params.get('pan', current_pan) - current_pan
                            delta_tilt = params.get('tilt', current_tilt) - current_tilt
                            
                            print(f"Orientation de la caméra: Pan={params.get('pan', current_pan):.3f}°, Tilt={params.get('tilt', current_tilt):.3f}°...")
                            
                            # Envoyer la commande à la gimbal
                            self.gimbal.send_command(delta_pan, delta_tilt, wait_for_goal=True)
                        
                        # Afficher la position finale
                        position = self.cnc.get_position()
                        print(f"Position atteinte: X={position['x']:.3f}, Y={position['y']:.3f}, Z={position['z']:.3f}")
                        print(f"Angles: Pan={self.gimbal.current_pan:.3f}°, Tilt={self.gimbal.current_tilt:.3f}°")
                        
                        # Prendre une photo si demandé
                        if params.get('take_photo', False):
                            self.take_photo()
                        
                    except Exception as e:
                        print(f"Erreur lors du déplacement: {e}")
            
            return True
            
        except KeyboardInterrupt:
            print("\nContrôle manuel interrompu par l'utilisateur")
            return False
        except Exception as e:
            print(f"\nUne erreur est survenue: {e}")
            return False
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Arrête proprement le système"""
        print("\nArrêt du système de contrôle manuel...")
        
        # Ramener le robot à la position (0, 0, 0)
        if self.cnc is not None:
            try:
                print("Déplacement vers la position (0, 0, 0)...")
                self.cnc.move_to(0, 0, 0, wait=True)
                
                print("Retour à la position d'origine (homing)...")
                self.cnc.home()
            except Exception as e:
                print(f"Erreur lors du retour à l'origine: {e}")
        
        # Remettre la caméra en position initiale
        if self.gimbal is not None:
            try:
                print("Remise de la caméra à la position initiale (0,0)...")
                self.gimbal.reset_position()
            except Exception as e:
                print(f"Erreur lors de la remise à zéro de la caméra: {e}")
        
        # Arrêter les contrôleurs dans l'ordre inverse d'initialisation
        if hasattr(self, 'gimbal') and self.gimbal:
            self.gimbal.shutdown()
        
        if hasattr(self, 'camera') and self.camera:
            self.camera.shutdown()
        
        if hasattr(self, 'cnc') and self.cnc:
            self.cnc.shutdown()
        
        self.initialized = False
        print("Système de contrôle manuel arrêté.")