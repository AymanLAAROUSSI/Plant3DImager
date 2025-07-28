#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Contrôleur de gimbal unifié pour les modules d'acquisition et de ciblage
"""

import time
import math
import serial
import numpy as np
from core.utils import config

class GimbalController:
    def __init__(self, arduino_port=None):
        """Initialise le contrôleur de gimbal"""
        self.arduino_port = arduino_port or config.ARDUINO_PORT
        self.gimbal_serial = None
        self.current_pan = 0.0
        self.current_tilt = 0.0
        self.initialized = False
    
    def connect(self):
        """Connecte à la gimbal et l'initialise"""
        if self.initialized:
            return self
        
        try:
            print(f"Connexion à l'Arduino sur le port {self.arduino_port}...")
            self.gimbal_serial = serial.Serial(self.arduino_port, 9600, timeout=1)
            time.sleep(2)  # Attendre l'initialisation
            
            # Lire et afficher les messages d'initialisation
            while self.gimbal_serial.in_waiting:
                response = self.gimbal_serial.readline().decode('utf-8', errors='replace').strip()
                print(f"Arduino: {response}")
            
            self.initialized = True
            return self
        except Exception as e:
            print(f"Erreur lors de l'initialisation de la gimbal: {e}")
            raise
    
    def normalize_angle_difference(self, delta):
        """Normalise la différence d'angle pour prendre le chemin le plus court"""
        if delta > 180:
            delta -= 360
        elif delta < -180:
            delta += 360
        return delta
    
    def send_command(self, pan_angle, tilt_angle, wait_for_goal=False):
        """Envoie les angles à la gimbal"""
        if not self.initialized or self.gimbal_serial is None:
            raise RuntimeError("Gimbal non initialisée")
        
        try:
            # Si les deux angles sont négligeables, ne pas bouger
            if abs(pan_angle) < 0.1 and abs(tilt_angle) < 0.1:
                print(f"Delta négligeable (Pan={pan_angle:.2f}°, Tilt={tilt_angle:.2f}°) - pas de mouvement")
                return True
            
            print(f"Envoi des ajustements: Delta Pan={pan_angle:.2f}°, Delta Tilt={tilt_angle:.2f}°")
            
            # Envoyer la commande
            command = f"{pan_angle} {tilt_angle}\n"
            self.gimbal_serial.write(command.encode())
            
            # Vider le buffer initial
            time.sleep(0.2)
            while self.gimbal_serial.in_waiting:
                response = self.gimbal_serial.readline().decode('utf-8', errors='replace').strip()
                print(f"Arduino: {response}")
            
            # Attendre la confirmation si demandé
            if wait_for_goal:
                print("Attente que les moteurs atteignent leur position...")
                
                # Pause pour laisser la gimbal traiter et commencer à bouger
                time.sleep(0.5)
                
                # Vérifier s'il y a des messages dans le buffer
                goal_reached = False
                
                while self.gimbal_serial.in_waiting:
                    response = self.gimbal_serial.readline().decode('utf-8', errors='replace').strip()
                    print(f"Arduino: {response}")
                    if "GOAL_REACHED" in response or "Mouvement terminé" in response:
                        goal_reached = True
                
                if goal_reached:
                    print("Position atteinte immédiatement")
                else:
                    # Attendre avec timeout
                    start_time = time.time()
                    timeout = 5  # 5 secondes
                    
                    # Réduire le timeout pour les petits mouvements
                    if abs(pan_angle) < 5 and abs(tilt_angle) < 5:
                        timeout = 2
                    
                    while time.time() - start_time < timeout:
                        if self.gimbal_serial.in_waiting:
                            response = self.gimbal_serial.readline().decode('utf-8', errors='replace').strip()
                            print(f"Arduino: {response}")
                            
                            if "GOAL_REACHED" in response or "Mouvement terminé" in response:
                                goal_reached = True
                                break
                        
                        time.sleep(0.1)
                    
                    # Pour les petits mouvements, considérer comme réussi malgré le timeout
                    if not goal_reached and abs(pan_angle) < 3 and abs(tilt_angle) < 3:
                        print("Mouvement très petit, considéré comme réussi malgré l'absence de confirmation")
                        goal_reached = True
            
            # Mettre à jour les angles actuels
            self.current_pan += pan_angle
            self.current_tilt += tilt_angle
            
            return True
            
        except Exception as e:
            print(f"Erreur lors de l'envoi de la commande à la gimbal: {e}")
            return False
    
    def calculate_angles(self, camera_position, target_position):
        """Calcule les angles nécessaires pour que la caméra vise la cible"""
        # Convertir la position caméra en coordonnées x, y, z
        if isinstance(camera_position, dict):
            cam_x, cam_y, cam_z = camera_position['x'], camera_position['y'], camera_position['z']
        else:
            cam_x, cam_y, cam_z = camera_position
        
        # Convertir la position cible en coordonnées x, y, z
        if isinstance(target_position, dict):
            target_x, target_y, target_z = target_position['x'], target_position['y'], target_position['z']
        else:
            target_x, target_y, target_z = target_position
        
        # Vecteur de la caméra à la cible
        dx = target_x - cam_x
        dy = target_y - cam_y
        dz = target_z - cam_z
        
        # Calcul de l'angle pan (angle horizontal par rapport à l'axe Y)
        pan_angle = -math.degrees(math.atan2(dx, dy))
        
        # Calcul de la distance horizontale entre la caméra et la cible
        horizontal_distance = math.sqrt(dx**2 + dy**2)
        
        # Calcul de l'angle tilt (angle vertical par rapport au plan horizontal)
        tilt_angle = math.degrees(math.atan2(dz, horizontal_distance))
        
        return (pan_angle, tilt_angle)
    
    def aim_at_target(self, camera_position, target_position, wait=True, invert_tilt=False):
        """
        Oriente la caméra pour viser un point cible
        
        Args:
            camera_position: Position actuelle de la caméra
            target_position: Position de la cible
            wait: Attendre la fin du mouvement
            invert_tilt: Inverser le signe du tilt calculé (pour s'adapter aux différents systèmes de coordonnées)
        
        Returns:
            True si l'orientation est réussie, False sinon
        """
        if not self.initialized:
            raise RuntimeError("Gimbal non initialisée")
        
        try:
            # Calculer les angles nécessaires
            target_pan, target_tilt = self.calculate_angles(camera_position, target_position)
            
            # Inverser le tilt si demandé
            if invert_tilt:
                target_tilt = -target_tilt
                print(f"DEBUG: Tilt inversé: {target_tilt:.2f}°")
            
            # Calculer les ajustements d'angle (deltas)
            delta_pan = target_pan - self.current_pan
            delta_tilt = target_tilt - self.current_tilt
            
            # Normaliser la différence d'angle
            delta_pan = self.normalize_angle_difference(delta_pan)
            
            # Envoyer la commande à la gimbal
            return self.send_command(delta_pan, delta_tilt, wait_for_goal=wait)
            
        except Exception as e:
            print(f"Erreur lors de l'orientation vers la cible: {e}")
            return False
    
    def reset_position(self):
        """Remet la caméra à la position initiale (0, 0)"""
        if not self.initialized:
            return True
        
        try:
            # Calculer les incréments nécessaires pour revenir à 0,0
            delta_pan = 0.0 - self.current_pan
            delta_pan = self.normalize_angle_difference(delta_pan)
            delta_tilt = 0.0 - self.current_tilt
            
            print(f"Remise de la caméra à la position initiale: "
                  f"Delta Pan={delta_pan:.2f}°, Delta Tilt={delta_tilt:.2f}°")
            
            # Envoyer la commande
            success = self.send_command(delta_pan, delta_tilt, wait_for_goal=True)
            
            if success:
                self.current_pan = 0.0
                self.current_tilt = 0.0
            
            return success
        except Exception as e:
            print(f"Erreur lors de la remise à zéro de la caméra: {e}")
            return False
    
    def shutdown(self):
        """Arrête proprement la gimbal"""
        if not self.initialized or self.gimbal_serial is None:
            return True
        
        try:
            # Remettre la caméra en position initiale
            self.reset_position()
            
            # Fermer la connexion série
            print("Fermeture de la connexion à l'Arduino...")
            self.gimbal_serial.close()
            
            self.initialized = False
            return True
        except Exception as e:
            print(f"Erreur lors de l'arrêt de la gimbal: {e}")
            return False