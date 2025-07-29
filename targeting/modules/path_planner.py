#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module de planification de trajectoire pour le ciblage de feuilles
"""

import numpy as np
import math
import os
from core.geometry.path_calculator import calculate_circle_positions, find_closest_point_index
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

def plan_safe_path(circle_position, target_point, leaf_position):
    """
    Planifie une trajectoire sûre entre un point sur le cercle et une feuille
    
    Args:
        circle_position: Position sur le cercle [x, y, z]
        target_point: Position cible près de la feuille [x, y, z] (déjà calculée avec la distance appropriée)
        leaf_position: Position de la feuille (centroïde) [x, y, z]
    
    Returns:
        Liste de dictionnaires décrivant la trajectoire
    """
    # Convertir les positions en numpy arrays pour faciliter les calculs
    circle_pos = np.array(circle_position)
    leaf_pos = np.array(leaf_position)
    target_pos = np.array(target_point)
    
    # Calculer la distance réelle entre la feuille et le point cible
    real_distance = np.linalg.norm(target_pos - leaf_pos)
    print(f"DEBUG: Distance calculée entre le point cible et la feuille: {real_distance:.3f} m")
    
    # Créer la trajectoire
    path = []
    
    # Point de départ sur le cercle
    path.append({
        "position": circle_pos.tolist(),
        "type": "via_point",
        "comment": "Position sur le cercle"
    })
    
    # Point intermédiaire pour l'approche de la feuille
    # (à mi-chemin entre le cercle et la feuille)
    middle_pos = circle_pos + 0.5 * (target_pos - circle_pos)
    path.append({
        "position": middle_pos.tolist(),
        "type": "via_point",
        "comment": "Approche de la feuille"
    })
    
    # Point cible près de la feuille (utilise directement le point précalculé)
    path.append({
        "position": target_pos.tolist(),
        "type": "target",
        "comment": f"Point cible près de la feuille (distance: {real_distance:.3f} m)"
    })
    
    # Chemin de retour (le même que l'aller mais en sens inverse)
    path.append({
        "position": middle_pos.tolist(),
        "type": "via_point",
        "comment": "Retour au cercle"
    })
    
    return path

def plan_complete_path(start_position, target_points, center_point, circle_radius, 
                      num_circle_points, leaf_distance=None):
    """
    Planifie une trajectoire complète incluant le cercle et les approches des feuilles
    
    Args:
        start_position: Position de départ [x, y, z]
        target_points: Liste des points cibles (feuilles) [[x, y, z], ...]
        center_point: Centre du cercle [x, y, z]
        circle_radius: Rayon du cercle
        num_circle_points: Nombre de points sur le cercle
        leaf_distance: Paramètre ignoré, conservé pour compatibilité (distance déjà prise en compte)
    
    Returns:
        Liste de dictionnaires décrivant la trajectoire complète
    """
    if leaf_distance is not None:
        print(f"Note: Le paramètre 'leaf_distance' est ignoré car la distance est déjà prise en compte dans les points cibles")
    
    if not target_points:
        return []
    
    # Calculer les positions sur le cercle
    circle_positions = calculate_circle_positions(center_point, circle_radius, num_circle_points)
    
    # Initialiser le chemin avec la position de départ
    path = [{
        "position": start_position,
        "type": "via_point",
        "comment": "Position de départ"
    }]
    
    # Trouver le point le plus proche sur le cercle de la position de départ
    start_pos_index = find_closest_point_index(circle_positions, start_position)
    current_pos = circle_positions[start_pos_index]
    
    # Ajouter le point d'entrée sur le cercle
    path.append({
        "position": current_pos,
        "type": "via_point",
        "comment": "Point d'entrée sur le cercle"
    })
    
    # Pour chaque point cible (feuille)
    for i, target_point in enumerate(target_points):
        # Trouver le point le plus proche sur le cercle par rapport à la feuille
        leaf_pos_index = find_closest_point_index(circle_positions, target_point)
        leaf_circle_pos = circle_positions[leaf_pos_index]
        
        # Ajouter le chemin sur le cercle jusqu'au point le plus proche
        # Déterminer s'il faut aller dans le sens horaire ou anti-horaire (le plus court)
        clockwise_distance = (leaf_pos_index - start_pos_index) % len(circle_positions)
        counterclockwise_distance = (start_pos_index - leaf_pos_index) % len(circle_positions)
        
        if clockwise_distance <= counterclockwise_distance:
            # Sens horaire
            for j in range(1, clockwise_distance + 1):
                pos_index = (start_pos_index + j) % len(circle_positions)
                path.append({
                    "position": circle_positions[pos_index],
                    "type": "via_point",
                    "comment": f"Position {pos_index} sur le cercle (vers feuille {i+1})"
                })
        else:
            # Sens anti-horaire
            for j in range(1, counterclockwise_distance + 1):
                pos_index = (start_pos_index - j) % len(circle_positions)
                path.append({
                    "position": circle_positions[pos_index],
                    "type": "via_point",
                    "comment": f"Position {pos_index} sur le cercle (vers feuille {i+1})"
                })
        
        # Utiliser le target_point précalculé directement (déjà à la bonne distance)
        # Pour cela, nous avons besoin de la position de la feuille (centroïde)
        leaf_position = target_point  # Pour maintenir la compatibilité avec plan_safe_path
        
        # Planifier le chemin d'approche vers la feuille
        approach_path = plan_safe_path(leaf_circle_pos, target_point, leaf_position)
        
        # Ajouter le chemin d'approche (ignorer le premier point qui est déjà sur le cercle)
        path.extend(approach_path[1:])
        
        # Mettre à jour le point de départ pour la prochaine feuille
        start_pos_index = leaf_pos_index
    
    # ===== NOUVELLE PARTIE: RETOUR SÉCURISÉ À LA POSITION INITIALE =====
    # Trouver le point le plus proche sur le cercle par rapport à la position de départ
    end_pos_index = find_closest_point_index(circle_positions, start_position)
    
    # Déterminer le chemin le plus court sur le cercle pour revenir au point proche de la position de départ
    clockwise_distance = (end_pos_index - start_pos_index) % len(circle_positions)
    counterclockwise_distance = (start_pos_index - end_pos_index) % len(circle_positions)
    
    print(f"Planification du retour via le cercle: position actuelle {start_pos_index}, point cible {end_pos_index}")
    
    if clockwise_distance <= counterclockwise_distance:
        # Sens horaire
        print(f"Retour dans le sens horaire: {clockwise_distance} points")
        for j in range(1, clockwise_distance + 1):
            pos_index = (start_pos_index + j) % len(circle_positions)
            path.append({
                "position": circle_positions[pos_index],
                "type": "via_point",
                "comment": f"Position {pos_index} sur le cercle (retour)"
            })
    else:
        # Sens anti-horaire
        print(f"Retour dans le sens anti-horaire: {counterclockwise_distance} points")
        for j in range(1, counterclockwise_distance + 1):
            pos_index = (start_pos_index - j) % len(circle_positions)
            path.append({
                "position": circle_positions[pos_index],
                "type": "via_point",
                "comment": f"Position {pos_index} sur le cercle (retour)"
            })
    
    # Seulement maintenant, ajouter le retour à la position de départ
    path.append({
        "position": start_position,
        "type": "end",
        "comment": "Retour à la position de départ"
    })
    
    return path

def visualize_path(path, points=None, target_point=None, save_path=None):
    """
    Visualise une trajectoire en 3D
    
    Args:
        path: Liste de dictionnaires décrivant la trajectoire
        points: Nuage de points à afficher (optionnel)
        target_point: Point cible à afficher (optionnel)
        save_path: Chemin pour sauvegarder l'image (optionnel)
    """
    # Créer la figure
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    # Extraire les positions du chemin
    positions = [p["position"] for p in path]
    x = [p[0] for p in positions]
    y = [p[1] for p in positions]
    z = [p[2] for p in positions]
    
    # Afficher le chemin
    ax.plot(x, y, z, 'b-', linewidth=2, label="Chemin")
    
    # Afficher les points du chemin
    for i, point in enumerate(path):
        pos = point["position"]
        if point["type"] == "via_point":
            ax.scatter(pos[0], pos[1], pos[2], color='green', s=30)
        elif point["type"] == "target":
            ax.scatter(pos[0], pos[1], pos[2], color='red', s=50)
            ax.text(pos[0], pos[1], pos[2], f"Target {i}", color='red')
        elif point["type"] == "end":
            ax.scatter(pos[0], pos[1], pos[2], color='purple', s=50)
            ax.text(pos[0], pos[1], pos[2], "End", color='purple')
    
    # Afficher le nuage de points si fourni
    if points is not None:
        ax.scatter(points[:, 0], points[:, 1], points[:, 2], color='gray', s=1, alpha=0.5)
    
    # Afficher le point cible si fourni
    if target_point is not None:
        ax.scatter(target_point[0], target_point[1], target_point[2], color='orange', s=100)
    
    # Configurer les axes
    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_zlabel('Z (m)')
    ax.set_title('Visualisation de la trajectoire')
    
    # Ajuster les limites des axes
    max_range = max([
        max(x) - min(x),
        max(y) - min(y),
        max(z) - min(z)
    ])
    mid_x = (max(x) + min(x)) / 2
    mid_y = (max(y) + min(y)) / 2
    mid_z = (max(z) + min(z)) / 2
    ax.set_xlim(mid_x - max_range/2, mid_x + max_range/2)
    ax.set_ylim(mid_y - max_range/2, mid_y + max_range/2)
    ax.set_zlim(mid_z - max_range/2, mid_z + max_range/2)
    
    # Ajouter une légende
    ax.legend()
    
    # Afficher ou sauvegarder la figure
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Figure sauvegardée: {save_path}")
    else:
        plt.show()
    
    plt.close(fig)

def visualize_complete_path(path, points, leaf_points_list=None, leaf_normals_list=None, save_dir=None):
    """
    Visualise une trajectoire complète avec les feuilles
    
    Args:
        path: Liste de dictionnaires décrivant la trajectoire
        points: Nuage de points global
        leaf_points_list: Liste des points des feuilles (optionnel)
        leaf_normals_list: Liste des normales des feuilles (optionnel)
        save_dir: Répertoire pour sauvegarder les images (optionnel)
    """
    # Créer la figure
    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(111, projection='3d')
    
    # Extraire les positions du chemin
    positions = [p["position"] for p in path]
    x = [p[0] for p in positions]
    y = [p[1] for p in positions]
    z = [p[2] for p in positions]
    
    # Afficher le chemin
    ax.plot(x, y, z, 'b-', linewidth=2, label="Chemin complet")
    
    # Afficher les points du chemin
    for i, point in enumerate(path):
        pos = point["position"]
        if point["type"] == "via_point":
            ax.scatter(pos[0], pos[1], pos[2], color='green', s=20)
        elif point["type"] == "target":
            ax.scatter(pos[0], pos[1], pos[2], color='red', s=50)
            ax.text(pos[0], pos[1], pos[2], f"T{i}", color='red')
        elif point["type"] == "end":
            ax.scatter(pos[0], pos[1], pos[2], color='purple', s=50)
            ax.text(pos[0], pos[1], pos[2], "Fin", color='purple')
    
    # Afficher le nuage de points global (sous-échantillonné pour la performance)
    if len(points) > 5000:
        # Sous-échantillonner pour des raisons de performance
        indices = np.random.choice(len(points), 5000, replace=False)
        sampled_points = points[indices]
        ax.scatter(sampled_points[:, 0], sampled_points[:, 1], sampled_points[:, 2], 
                  color='gray', s=1, alpha=0.3, label="Nuage de points")
    else:
        ax.scatter(points[:, 0], points[:, 1], points[:, 2], 
                  color='gray', s=1, alpha=0.3, label="Nuage de points")
    
    # Afficher les points des feuilles si fournis
    if leaf_points_list is not None:
        for i, leaf_points in enumerate(leaf_points_list):
            if isinstance(leaf_points, list) and len(leaf_points) == 3:
                # C'est un seul point (centroïde)
                ax.scatter(leaf_points[0], leaf_points[1], leaf_points[2], 
                          color='orange', s=100, label=f"Feuille {i+1}" if i == 0 else "")
            else:
                # C'est un ensemble de points
                ax.scatter(leaf_points[:, 0], leaf_points[:, 1], leaf_points[:, 2], 
                          color='orange', s=10, alpha=0.7, label=f"Feuille {i+1}" if i == 0 else "")
    
    # Afficher les normales des feuilles si fournies
    if leaf_normals_list is not None and leaf_points_list is not None:
        for i, (leaf_points, leaf_normal) in enumerate(zip(leaf_points_list, leaf_normals_list)):
            if isinstance(leaf_points, list) and len(leaf_points) == 3:
                # C'est un seul point (centroïde)
                centroid = leaf_points
            else:
                # Calculer le centroïde
                centroid = np.mean(leaf_points, axis=0)
            
            # Normaliser la normale
            normal = leaf_normal / np.linalg.norm(leaf_normal)
            
            # Dessiner la normale
            ax.quiver(centroid[0], centroid[1], centroid[2], 
                     normal[0], normal[1], normal[2], 
                     color='red', length=0.05, arrow_length_ratio=0.3)
    
    # Configurer les axes
    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_zlabel('Z (m)')
    ax.set_title('Trajectoire complète avec feuilles cibles')
    
    # Ajouter une légende
    handles, labels = ax.get_legend_handles_labels()
    # Supprimer les doublons
    unique = [(h, l) for i, (h, l) in enumerate(zip(handles, labels)) if l not in labels[:i]]
    ax.legend(*zip(*unique))
    
    # Ajuster la vue
    ax.view_init(elev=30, azim=45)
    
    # Afficher ou sauvegarder la figure
    if save_dir:
        save_path = os.path.join(save_dir, "complete_path.png")
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Figure sauvegardée: {save_path}")
        
        # Enregistrer également une vue de dessus
        ax.view_init(elev=90, azim=0)
        save_path = os.path.join(save_dir, "complete_path_top_view.png")
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Vue de dessus sauvegardée: {save_path}")
    else:
        plt.show()
    
    plt.close(fig)