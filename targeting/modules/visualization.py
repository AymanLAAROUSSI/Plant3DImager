# modules/visualization.py
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import os

def visualize_path(path, cloud_points=None, leaf_points=None, leaf_normal=None, output_dir=None):
    """
    Visualise la trajectoire planifiée
    
    Args:
        path: Liste de dictionnaires décrivant la trajectoire
        cloud_points: Points du nuage (optionnel)
        leaf_points: Points de la feuille (optionnel)
        leaf_normal: Normale de la feuille (optionnel)
        output_dir: Répertoire de sortie pour les visualisations
    """
    # Extraire les positions
    positions = [np.array(point_info["position"]) for point_info in path]
    
    # Créer la figure
    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(111, projection='3d')
    
    # Afficher le nuage si disponible
    if cloud_points is not None:
        # Échantillonner pour la performance
        max_display_points = 5000
        if len(cloud_points) > max_display_points:
            sample_indices = np.random.choice(len(cloud_points), max_display_points, replace=False)
            display_points = cloud_points[sample_indices]
        else:
            display_points = cloud_points
            
        ax.scatter(display_points[:, 0], display_points[:, 1], display_points[:, 2],
                  c='black', s=1, alpha=0.4, label='Nuage de points')
    
    # Afficher la feuille si disponible
    if leaf_points is not None:
        # Échantillonner si nécessaire
        max_leaf_points = 500
        if len(leaf_points) > max_leaf_points:
            sample_indices = np.random.choice(len(leaf_points), max_leaf_points, replace=False)
            display_leaf_points = leaf_points[sample_indices]
        else:
            display_leaf_points = leaf_points
            
        ax.scatter(display_leaf_points[:, 0], display_leaf_points[:, 1], display_leaf_points[:, 2],
                  c='green', s=15, label='Feuille')
    
    # Afficher la normale si disponible
    if leaf_normal is not None and leaf_points is not None:
        # Calculer le centroïde
        centroid = np.mean(leaf_points, axis=0)
        
        # Longueur de la flèche
        normal_length = 0.10  # 10 cm
        
        # Afficher la normale
        ax.quiver(centroid[0], centroid[1], centroid[2],
                 leaf_normal[0] * normal_length, 
                 leaf_normal[1] * normal_length,
                 leaf_normal[2] * normal_length,
                 color='red', arrow_length_ratio=0.2, linewidth=2,
                 label='Normale')
    
    # Afficher les points de la trajectoire avec une légende pour chaque type
    point_types = {'start': ('Départ', 'blue', 'o', 100),
                  'via_point': ('Point intermédiaire', 'orange', 's', 100),
                  'target': ('Point cible', 'red', '*', 150),
                  'end': ('Position finale', 'purple', 'D', 150)}
    
    # Garder une trace des types déjà ajoutés à la légende
    legend_added = set()
    
    for i, (position, point_info) in enumerate(zip(positions, path)):
        point_type = point_info["type"]
        
        # Obtenir les informations de style pour ce type de point
        if point_type in point_types:
            label, color, marker, size = point_types[point_type]
        else:
            # Type par défaut si non reconnu
            label, color, marker, size = ('Point', 'gray', 'o', 80)
        
        # Ajouter à la légende seulement la première fois pour ce type
        if point_type not in legend_added:
            ax.scatter([position[0]], [position[1]], [position[2]],
                      c=color, s=size, marker=marker, label=label)
            legend_added.add(point_type)
        else:
            ax.scatter([position[0]], [position[1]], [position[2]],
                      c=color, s=size, marker=marker)
    
    # Afficher la trajectoire comme une ligne
    path_array = np.array(positions)
    ax.plot(path_array[:, 0], path_array[:, 1], path_array[:, 2],
           'k--', linewidth=2, label='Trajectoire')
    
    # Configurer les axes
    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_zlabel('Z (m)')
    ax.set_title('Trajectoire planifiée', fontsize=16)
    
    # CORRECTION : Inverser les axes X et Y pour une orientation plus intuitive
    # Cela place le point (0,0) plus près de nous
    ax.invert_xaxis()
    ax.invert_yaxis()
    
    # CORRECTION : Ajuster la vue pour une meilleure orientation
    ax.view_init(elev=20, azim=60)
    
    # Légende
    ax.legend()
    
    # Sauvegarder et afficher
    plt.tight_layout()
    
    if output_dir:
        visualization_path = os.path.join(output_dir, 'planned_path.png')
        plt.savefig(visualization_path, dpi=300)
        print(f"Visualisation de la trajectoire sauvegardée dans '{visualization_path}'")
    else:
        plt.savefig('planned_path.png', dpi=300)
        print("Visualisation de la trajectoire sauvegardée dans 'planned_path.png'")
        
    plt.show()

def visualize_complete_path(path, cloud_points=None, leaves_points=None, leaves_normals=None, output_dir=None):
    """
    Visualise une trajectoire complète visitant plusieurs feuilles
    
    Args:
        path: Liste de dictionnaires décrivant la trajectoire
        cloud_points: Points du nuage (optionnel)
        leaves_points: Liste des points des feuilles (optionnel)
        leaves_normals: Liste des normales des feuilles (optionnel)
        output_dir: Répertoire de sortie pour les visualisations
    """
    # Extraire les positions
    positions = [np.array(point_info["position"]) for point_info in path]
    
    # Créer la figure
    fig = plt.figure(figsize=(14, 12))
    ax = fig.add_subplot(111, projection='3d')
    
    # Afficher le nuage si disponible
    if cloud_points is not None:
        # Échantillonner pour la performance
        max_display_points = 5000
        if len(cloud_points) > max_display_points:
            sample_indices = np.random.choice(len(cloud_points), max_display_points, replace=False)
            display_points = cloud_points[sample_indices]
        else:
            display_points = cloud_points
            
        ax.scatter(display_points[:, 0], display_points[:, 1], display_points[:, 2],
                  c='black', s=1, alpha=0.3, label='Nuage de points')
    
    # Afficher les feuilles si disponibles
    if leaves_points is not None:
        # Générer des couleurs distinctes pour les feuilles
        n_leaves = len(leaves_points)
        import colorsys
        
        colors = []
        for i in range(n_leaves):
            hue = i / n_leaves
            saturation = 0.7
            value = 0.8
            r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
            colors.append([r, g, b])
        
        for i, leaf_points in enumerate(leaves_points):
            # Échantillonner si nécessaire
            max_leaf_points = 500
            if len(leaf_points) > max_leaf_points:
                sample_indices = np.random.choice(len(leaf_points), max_leaf_points, replace=False)
                display_leaf_points = leaf_points[sample_indices]
            else:
                display_leaf_points = leaf_points
                
            ax.scatter(display_leaf_points[:, 0], display_leaf_points[:, 1], display_leaf_points[:, 2],
                      c=[colors[i]], s=15, label=f'Feuille {i+1}')
            
            # Afficher la normale si disponible
            if leaves_normals is not None and i < len(leaves_normals):
                leaf_normal = leaves_normals[i]
                # Calculer le centroïde
                centroid = np.mean(leaf_points, axis=0)
                
                # Longueur de la flèche
                normal_length = 0.10  # 10 cm
                
                # Afficher la normale
                ax.quiver(centroid[0], centroid[1], centroid[2],
                         leaf_normal[0] * normal_length, 
                         leaf_normal[1] * normal_length,
                         leaf_normal[2] * normal_length,
                         color='red', arrow_length_ratio=0.2, linewidth=2)
    
    # Afficher les points de la trajectoire avec une légende pour chaque type
    point_types = {'start': ('Départ', 'blue', 'o', 100),
                  'via_point': ('Point intermédiaire', 'orange', 's', 50),
                  'target': ('Point cible', 'red', '*', 150),
                  'end': ('Position finale', 'purple', 'D', 150)}
    
    # Garder une trace des types déjà ajoutés à la légende
    legend_added = set()
    
    # Annoter les points cibles avec leur numéro d'ordre
    target_count = 0
    
    for i, (position, point_info) in enumerate(zip(positions, path)):
        point_type = point_info["type"]
        
        # Obtenir les informations de style pour ce type de point
        if point_type in point_types:
            label, color, marker, size = point_types[point_type]
        else:
            # Type par défaut si non reconnu
            label, color, marker, size = ('Point', 'gray', 'o', 80)
        
        # Ajouter à la légende seulement la première fois pour ce type
        if point_type not in legend_added:
            ax.scatter([position[0]], [position[1]], [position[2]],
                      c=color, s=size, marker=marker, label=label)
            legend_added.add(point_type)
        else:
            ax.scatter([position[0]], [position[1]], [position[2]],
                      c=color, s=size, marker=marker)
        
        # Ajouter un numéro pour les points cibles
        if point_type == "target":
            target_count += 1
            ax.text(position[0], position[1], position[2] + 0.01,
                   f"{target_count}", fontsize=12, color='black',
                   horizontalalignment='center', verticalalignment='center',
                   bbox=dict(facecolor='white', alpha=0.7, edgecolor='black'))
    
    # Afficher la trajectoire comme une ligne
    path_array = np.array(positions)
    ax.plot(path_array[:, 0], path_array[:, 1], path_array[:, 2],
           'k--', linewidth=2, label='Trajectoire')
    
    # Configurer les axes
    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_zlabel('Z (m)')
    ax.set_title('Trajectoire complète planifiée', fontsize=16)
    
    # Inverser les axes X et Y pour une orientation plus intuitive
    ax.invert_xaxis()
    ax.invert_yaxis()
    
    # Ajuster la vue pour une meilleure orientation
    ax.view_init(elev=20, azim=60)
    
    # Légende
    ax.legend()
    
    # Sauvegarder et afficher
    plt.tight_layout()
    
    if output_dir:
        visualization_path = os.path.join(output_dir, 'complete_path.png')
        plt.savefig(visualization_path, dpi=300)
        print(f"Visualisation de la trajectoire complète sauvegardée dans '{visualization_path}'")
    else:
        plt.savefig('complete_path.png', dpi=300)
        print("Visualisation de la trajectoire complète sauvegardée dans 'complete_path.png'")
        
    plt.show()