#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Fonctions de calcul d'angles pour la caméra et la gimbal
"""

import math
import numpy as np

def normalize_angle_difference(delta):
    """
    Normalise la différence d'angle pour prendre le chemin le plus court
    
    Args:
        delta: Différence d'angle en degrés
        
    Returns:
        Différence normalisée entre -180 et +180 degrés
    """
    if delta > 180:
        delta -= 360
    elif delta < -180:
        delta += 360
    return delta

def calculate_camera_angles(camera_position, target_position):
    """
    Calcule les angles pan et tilt nécessaires pour que la caméra 
    pointe vers la cible depuis sa position actuelle
    
    Args:
        camera_position: Position de la caméra (x, y, z) ou {"x": x, "y": y, "z": z}
        target_position: Position de la cible (x, y, z) ou {"x": x, "y": y, "z": z}
        
    Returns:
        Tuple (pan_angle, tilt_angle) en degrés
    """
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
    # Note: On inverse le signe pour que la rotation se fasse dans le bon sens
    # Un angle négatif tourne vers la droite, un angle positif vers la gauche
    pan_angle = -math.degrees(math.atan2(dx, dy))
    
    # Calcul de la distance horizontale entre la caméra et la cible
    horizontal_distance = math.sqrt(dx**2 + dy**2)
    
    # Calcul de l'angle tilt (angle vertical par rapport au plan horizontal)
    tilt_angle = math.degrees(math.atan2(dz, horizontal_distance))
    
    return (pan_angle, tilt_angle)