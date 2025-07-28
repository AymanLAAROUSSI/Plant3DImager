#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Fonctions de calcul de chemins pour les trajectoires circulaires et autres
"""

import math
import numpy as np
from scipy.spatial import cKDTree
from core.utils import config

def calculate_circle_positions(center=None, radius=None, num_positions=None):
    """
    Calcule les positions sur un cercle dans le plan XY
    
    Args:
        center: Tuple (x, y, z) du centre du cercle (défaut: CENTER_POINT)
        radius: Rayon du cercle (défaut: CIRCLE_RADIUS)
        num_positions: Nombre de positions sur le cercle (défaut: NUM_POSITIONS)
    
    Returns:
        Liste de tuples (x, y, z) représentant les positions sur le cercle
    """
    # Utiliser les valeurs par défaut si non spécifiées
    if center is None:
        center = config.CENTER_POINT
    
    if radius is None:
        radius = config.CIRCLE_RADIUS
    
    if num_positions is None:
        num_positions = config.NUM_POSITIONS
    
    positions = []
    for i in range(num_positions):
        # Calculer l'angle en radians
        angle = 2 * math.pi * i / num_positions
        
        # Calculer les coordonnées x et y
        x = center[0] + radius * math.cos(angle)
        y = center[1] + radius * math.sin(angle)
        z = center[2]  # Garder la même hauteur
        
        positions.append((x, y, z))
    
    return positions

def find_closest_point_index(positions, reference_point):
    """
    Trouve l'index du point le plus proche du point de référence
    
    Args:
        positions: Liste de tuples (x, y, z)
        reference_point: Point de référence (x, y, z) ou {"x": x, "y": y, "z": z}
    
    Returns:
        Index du point le plus proche
    """
    # Convertir le point de référence si nécessaire
    if isinstance(reference_point, dict):
        ref_point = (reference_point['x'], reference_point['y'], reference_point['z'])
    else:
        ref_point = reference_point
    
    # Utiliser KDTree pour une recherche efficace
    tree = cKDTree(positions)
    _, index = tree.query(ref_point)
    
    return index

def reorder_positions(positions, start_index):
    """
    Réorganise la liste des positions pour commencer par l'index spécifié
    
    Args:
        positions: Liste des positions
        start_index: Index par lequel commencer
    
    Returns:
        Liste réordonnée des positions
    """
    reordered = positions[start_index:] + positions[:start_index]
    return reordered

def plan_circle_path(center=None, radius=None, num_positions=None, start_point=None):
    """
    Planifie un chemin circulaire complet, en commençant par le point le plus proche
    du point de départ spécifié
    
    Args:
        center: Centre du cercle (défaut: CENTER_POINT)
        radius: Rayon du cercle (défaut: CIRCLE_RADIUS)
        num_positions: Nombre de positions (défaut: NUM_POSITIONS)
        start_point: Point de départ (défaut: (0, 0, 0))
        
    Returns:
        Liste de dictionnaires décrivant la trajectoire
    """
    # Utiliser les valeurs par défaut si non spécifiées
    if center is None:
        center = config.CENTER_POINT
    
    if radius is None:
        radius = config.CIRCLE_RADIUS
    
    if num_positions is None:
        num_positions = config.NUM_POSITIONS
    
    if start_point is None:
        start_point = (0, 0, 0)
    
    # Calculer les positions sur le cercle
    positions = calculate_circle_positions(center, radius, num_positions)
    
    # Trouver le point le plus proche du point de départ
    closest_index = find_closest_point_index(positions, start_point)
    
    # Réorganiser les positions pour commencer par le point le plus proche
    ordered_positions = reorder_positions(positions, closest_index)
    
    # Créer la trajectoire
    path = []
    
    # Ajouter le point de départ
    path.append({
        "position": start_point,
        "type": "start",
        "comment": "Position de départ"
    })
    
    # Ajouter le point d'entrée sur le cercle
    path.append({
        "position": ordered_positions[0],
        "type": "via_point",
        "comment": "Point d'entrée sur le cercle"
    })
    
    # Ajouter les positions sur le cercle
    for i, pos in enumerate(ordered_positions[1:], 1):
        path.append({
            "position": pos,
            "type": "via_point",
            "comment": f"Position {i}/{num_positions} sur le cercle"
        })
    
    # Ajouter le retour au point de départ
    path.append({
        "position": start_point,
        "type": "end",
        "comment": "Retour à la position de départ"
    })
    
    return path

def plan_multi_circle_path(center=None, radius=None, num_positions=None, num_circles=1, z_offset=None, start_point=None):
    """
    Planifie un chemin sur plusieurs cercles à des hauteurs différentes
    
    Args:
        center: Centre du cercle (défaut: CENTER_POINT)
        radius: Rayon du cercle (défaut: CIRCLE_RADIUS)
        num_positions: Nombre de positions par cercle (défaut: NUM_POSITIONS)
        num_circles: Nombre de cercles (défaut: 1)
        z_offset: Décalage en Z entre les cercles (défaut: Z_OFFSET)
        start_point: Point de départ (défaut: (0, 0, 0))
        
    Returns:
        Liste de dictionnaires décrivant la trajectoire
    """
    # Utiliser les valeurs par défaut si non spécifiées
    if center is None:
        center = config.CENTER_POINT
    
    if radius is None:
        radius = config.CIRCLE_RADIUS
    
    if num_positions is None:
        num_positions = config.NUM_POSITIONS
    
    if z_offset is None:
        z_offset = config.Z_OFFSET
    
    if start_point is None:
        start_point = (0, 0, 0)
    
    # Créer la trajectoire
    path = []
    
    # Ajouter le point de départ
    path.append({
        "position": start_point,
        "type": "start",
        "comment": "Position de départ"
    })
    
    # Pour chaque cercle
    for circle_num in range(num_circles):
        # Ajuster la hauteur Z pour ce cercle
        circle_center = (center[0], center[1], center[2] + (circle_num * z_offset))
        
        # Calculer les positions sur le cercle
        positions = calculate_circle_positions(circle_center, radius, num_positions)
        
        # Pour le premier cercle, commencer par le point le plus proche du point de départ
        if circle_num == 0:
            closest_index = find_closest_point_index(positions, start_point)
            positions = reorder_positions(positions, closest_index)
        
        # Ajouter un commentaire pour le début du cercle
        circle_height = circle_center[2]
        path.append({
            "position": positions[0],
            "type": "via_point",
            "comment": f"Début du cercle {circle_num+1}/{num_circles} à hauteur Z = {circle_height:.3f}"
        })
        
        # Ajouter les positions sur ce cercle
        for i, pos in enumerate(positions[1:], 1):
            # Calcul du numéro de photo global
            photo_num = (circle_num * num_positions) + i
            
            path.append({
                "position": pos,
                "type": "via_point",
                "comment": f"Position {photo_num}/{num_positions*num_circles} sur le cercle {circle_num+1}"
            })
    
    # Ajouter le retour au point de départ
    path.append({
        "position": start_point,
        "type": "end",
        "comment": "Retour à la position de départ"
    })
    
    return path