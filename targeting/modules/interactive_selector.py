# modules/interactive_selector.py
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import os

def generate_distinct_colors(n):
    """Génère n couleurs distinctes"""
    colors = []
    for i in range(n):
        hue = i / n
        saturation = 0.7 + 0.3 * (i % 2)
        value = 0.8 + 0.2 * (i % 3)
        
        # Convertir HSV en RGB en utilisant colorsys (plus sûr)
        import colorsys
        r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
        
        # S'assurer que les valeurs sont dans [0, 1]
        r = max(0.0, min(1.0, r))
        g = max(0.0, min(1.0, g))
        b = max(0.0, min(1.0, b))
            
        colors.append([r, g, b])
    return colors

def select_leaf_with_matplotlib(leaves_data, cloud_points, output_dir=None):
    """
    Affiche les feuilles numérotées et permet la sélection multiple via terminal
    
    Args:
        leaves_data: Liste des données de feuilles
        cloud_points: Points du nuage complet
        output_dir: Répertoire de sortie pour les visualisations
    
    Returns:
        Liste des feuilles sélectionnées (dictionnaires) dans l'ordre spécifié
        ou liste vide si annulé
    """
    print("\nPréparation de la visualisation des feuilles...")
    
    # Créer une figure 3D
    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(111, projection='3d')
    
    # Afficher le nuage complet en noir (échantillonné pour performance)
    max_display_points = 5000
    if len(cloud_points) > max_display_points:
        sample_indices = np.random.choice(len(cloud_points), max_display_points, replace=False)
        display_points = cloud_points[sample_indices]
    else:
        display_points = cloud_points
        
    ax.scatter(display_points[:, 0], display_points[:, 1], display_points[:, 2],
              c='black', s=1, alpha=0.4, label='Nuage de points')
    
    # Générer des couleurs distinctes pour les feuilles
    colors = generate_distinct_colors(len(leaves_data))
    
    # Afficher chaque feuille avec son ID
    for i, leaf in enumerate(leaves_data):
        # Obtenir les points de cette feuille (si disponibles)
        if 'points' in leaf:
            leaf_points = np.array(leaf['points'])
            
            # Échantillonner si trop de points
            max_leaf_points = 500
            if len(leaf_points) > max_leaf_points:
                sample_indices = np.random.choice(len(leaf_points), max_leaf_points, replace=False)
                leaf_points = leaf_points[sample_indices]
            
            # Afficher les points
            ax.scatter(leaf_points[:, 0], leaf_points[:, 1], leaf_points[:, 2],
                      c=[colors[i]], s=15, label=f'Feuille {leaf["id"]}')
        
        # Afficher le centroïde
        centroid = leaf['centroid']
        ax.scatter([centroid[0]], [centroid[1]], [centroid[2]], 
                  c=[colors[i]], s=100, marker='o', edgecolors='black')
        
        # Afficher la normale (comme une flèche)
        if 'normal' in leaf:
            normal = leaf['normal']
            normal_length = 0.05  # 5 cm
            arrow_end = [
                centroid[0] + normal[0] * normal_length,
                centroid[1] + normal[1] * normal_length,
                centroid[2] + normal[2] * normal_length
            ]
            ax.quiver(centroid[0], centroid[1], centroid[2],
                     normal[0] * normal_length, normal[1] * normal_length, normal[2] * normal_length,
                     color='red', arrow_length_ratio=0.2)
        
        # Ajouter un texte avec l'ID légèrement décalé du centroïde
        # Calculer un décalage basé sur la normale pour que le texte soit visible
        offset = np.array([0, 0, 0.01])  # Décalage de base (1 cm vers le haut)
        
        # Si une normale est disponible, utiliser son orientation pour décaler perpendiculairement
        if 'normal' in leaf:
            normal = np.array(leaf['normal'])
            # Créer un vecteur perpendiculaire à la normale
            if abs(normal[0]) > 0.1 or abs(normal[1]) > 0.1:
                # Si la normale n'est pas verticale, on peut créer facilement un vecteur perpendiculaire
                perp = np.array([normal[1], -normal[0], 0])
                perp = perp / np.linalg.norm(perp) * 0.01  # Normaliser à 1 cm
                offset = perp
            else:
                # Si la normale est presque verticale, utiliser un décalage standard
                offset = np.array([0.01, 0.01, 0.01])
        
        # Position du texte
        text_pos = np.array(centroid) + offset
        
        # Ajouter le texte
        ax.text(text_pos[0], text_pos[1], text_pos[2], 
               f"{leaf['id']}", fontsize=14, color='black', weight='bold',
               horizontalalignment='center', verticalalignment='center',
               bbox=dict(facecolor='white', alpha=0.7, edgecolor='black', boxstyle='round,pad=0.3'))
    
    # Configurer les axes
    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_zlabel('Z (m)')
    ax.set_title('Feuilles identifiées', fontsize=16)
    
    # CORRECTION : Inverser les axes X et Y pour une orientation plus intuitive
    # Cela place le point (0,0) plus près de nous
    ax.invert_xaxis()
    ax.invert_yaxis()
    
    # CORRECTION : Ajuster la vue pour une meilleure orientation
    ax.view_init(elev=20, azim=60)
    
    # Afficher la légende si pas trop de feuilles
    if len(leaves_data) <= 10:
        ax.legend()
    
    # Sauvegarder l'image avant affichage
    plt.tight_layout()
    
    if output_dir:
        visualization_path = os.path.join(output_dir, 'leaves_selection.png')
        plt.savefig(visualization_path, dpi=300)
        print(f"Visualisation sauvegardée dans '{visualization_path}'")
    else:
        plt.savefig('leaves_selection.png', dpi=300)
        print("Visualisation sauvegardée dans 'leaves_selection.png'")
    
    # Afficher la figure
    plt.show()
    
    # Afficher un tableau récapitulatif dans le terminal
    print("\n=== FEUILLES IDENTIFIÉES ===")
    print("ID | Centroïde (x, y, z) | Normale (x, y, z)")
    print("-" * 65)
    
    for leaf in leaves_data:
        centroid = leaf['centroid']
        normal = leaf.get('normal', [0, 0, 0])
        print(f"{leaf['id']:2d} | ({centroid[0]:.3f}, {centroid[1]:.3f}, {centroid[2]:.3f}) | "
              f"({normal[0]:.3f}, {normal[1]:.3f}, {normal[2]:.3f})")
    
    # Demander à l'utilisateur de sélectionner plusieurs feuilles
    while True:
        try:
            selection_input = input("\nEntrez les numéros des feuilles à cibler dans l'ordre souhaité (ex: '1 4 2 8'), ou 'q' pour quitter: ")
            
            if selection_input.lower() == 'q':
                print("Sélection annulée.")
                return []
            
            # Diviser l'entrée par les espaces et convertir en entiers
            selected_ids = [int(id_str) for id_str in selection_input.split()]
            
            # Vérifier si tous les IDs sont valides
            leaf_ids = [leaf['id'] for leaf in leaves_data]
            invalid_ids = [id for id in selected_ids if id not in leaf_ids]
            
            if invalid_ids:
                print(f"Erreur: Les IDs suivants n'existent pas: {invalid_ids}. Veuillez réessayer.")
                continue
            
            # Créer la liste des feuilles sélectionnées dans l'ordre spécifié
            selected_leaves = []
            for selected_id in selected_ids:
                for leaf in leaves_data:
                    if leaf['id'] == selected_id:
                        selected_leaves.append(leaf)
                        break
            
            if not selected_leaves:
                print("Aucune feuille valide sélectionnée. Veuillez réessayer.")
                continue
                
            # Afficher les feuilles sélectionnées dans l'ordre
            print("\nFeuilles sélectionnées dans l'ordre:")
            for i, leaf in enumerate(selected_leaves):
                print(f"{i+1}. Feuille {leaf['id']}")
            
            return selected_leaves
                
        except ValueError:
            print("Erreur: Format invalide. Veuillez entrer des nombres entiers séparés par des espaces.")