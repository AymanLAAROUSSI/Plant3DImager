#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Contrôleur CNC unifié pour les modules d'acquisition et de ciblage
"""

import time
import math
from romi.cnc import CNC

class CNCController:
    def __init__(self, speed=0.1):
        """
        Initialise le contrôleur CNC avec les paramètres spécifiés
        """
        self.speed = speed
        self.cnc = None
        self.current_position = None
        self.initialized = False
    
    def connect(self):
        """Connecte au CNC et l'initialise"""
        if self.initialized:
            return self
        
        try:
            print("Initialisation du CNC...")
            self.cnc = CNC("cnc", "cnc")
            
            # Démarrer le CNC
            print("Démarrage du CNC...")
            self.cnc.power_up()
            
            # Obtenir la position initiale
            robot_pos = self.cnc.get_position()
            
            # Convertir et stocker la position
            self.current_position = {
                'x': robot_pos['x'],
                'y': robot_pos['y'],
                'z': -robot_pos['z']  # Inverser pour l'affichage cohérent
            }
            
            print(f"Position initiale: X={self.current_position['x']:.3f}, "
                  f"Y={self.current_position['y']:.3f}, Z={self.current_position['z']:.3f}")
            
            self.initialized = True
            return self
            
        except Exception as e:
            print(f"Erreur lors de l'initialisation du CNC: {e}")
            raise
    
    def get_position(self):
        """Obtient la position actuelle du CNC"""
        if not self.initialized:
            raise RuntimeError("CNC non initialisé")
        
        robot_pos = self.cnc.get_position()
        
        # Convertir pour l'affichage cohérent
        position = {
            'x': robot_pos['x'],
            'y': robot_pos['y'],
            'z': -robot_pos['z']  # Inverser pour l'affichage
        }
        
        self.current_position = position
        return position
    
    def move_to(self, x, y, z, wait=True):
        """Déplace le CNC à la position spécifiée"""
        if not self.initialized:
            raise RuntimeError("CNC non initialisé")
        
        try:
            # IMPORTANT: Inverser le signe de Z pour le contrôle du robot
            # (nous utilisons Z positif vers le haut, le robot utilise Z positif vers le bas)
            robot_z = -z
            
            print(f"Déplacement vers X={x:.3f}, Y={y:.3f}, Z={z:.3f}... (Robot Z={robot_z:.3f})")
            
            # Effectuer le mouvement
            self.cnc.moveto(x, y, robot_z, self.speed, wait)
            
            # Mettre à jour la position si wait=True
            if wait:
                self.get_position()
                
                print(f"Position atteinte: X={self.current_position['x']:.3f}, "
                      f"Y={self.current_position['y']:.3f}, Z={self.current_position['z']:.3f}")
            
            return True
            
        except Exception as e:
            print(f"Erreur lors du déplacement: {e}")
            return False
    
    def check_movement_status(self, previous_position, tolerance=0.001):
        """Vérifie si le CNC est encore en mouvement en comparant les positions"""
        if not self.initialized:
            raise RuntimeError("CNC non initialisé")
        
        current_position = self.get_position()
        
        # Calculer la distance entre la position actuelle et la position précédente
        dx = current_position['x'] - previous_position['x']
        dy = current_position['y'] - previous_position['y']
        dz = current_position['z'] - previous_position['z']
        
        distance = math.sqrt(dx**2 + dy**2 + dz**2)
        
        # Si la distance est inférieure à la tolérance, on considère que le mouvement est terminé
        return distance > tolerance, current_position
    
    def home(self):
        """Retourne à la position d'origine"""
        if not self.initialized:
            raise RuntimeError("CNC non initialisé")
        
        try:
            print("Retour à la position d'origine (homing)...")
            self.cnc.homing()
            return True
        except Exception as e:
            print(f"Erreur lors du retour à l'origine: {e}")
            return False
    
    def shutdown(self):
        """Arrête proprement le CNC"""
        if not self.initialized:
            return True
        
        try:
            # D'abord se déplacer à (0, 0, 0)
            print("Déplacement vers la position (0, 0, 0)...")
            self.move_to(0, 0, 0, wait=True)
            
            # Puis retour à l'origine
            self.home()
            
            # Enfin, arrêt de l'alimentation
            print("Arrêt du CNC...")
            self.cnc.power_down()
            
            self.initialized = False
            return True
        except Exception as e:
            print(f"Erreur lors de l'arrêt du CNC: {e}")
            return False