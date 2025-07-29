# modules/leaf_analyzer.py
import numpy as np
import open3d as o3d
from scipy.spatial import cKDTree
import networkx as nx
import random
import time

try:
    import community as community_louvain
    LOUVAIN_AVAILABLE = True
except ImportError:
    LOUVAIN_AVAILABLE = False
    print("ERREUR: Le package 'python-louvain' n'est pas installé.")
    print("Pour l'installer: pip install python-louvain")

def calculate_adaptive_radius(points):
    """
    Calcule un rayon de connectivité adaptatif
    """
    if len(points) < 10:
        return 0.01
    
    # Échantillonner pour accélérer le calcul
    sample_size = min(1000, len(points))
    sample_indices = np.random.choice(len(points), sample_size, replace=False)
    sample_points = points[sample_indices]
    
    # Créer un KDTree sur TOUS les points originaux
    full_tree = cKDTree(points)
    
    # Pour chaque point échantillonné, trouver son plus proche voisin
    all_distances = []
    for point in sample_points:
        # Chercher les 2 plus proches voisins (le premier étant le point lui-même)
        distances, _ = full_tree.query(point, k=2)
        # Ignorer la distance à soi-même (première distance = 0)
        neighbor_distance = distances[1]
        all_distances.append(neighbor_distance)
    
    # Calculer la distance moyenne au premier voisin le plus proche
    avg_1nn = np.mean(all_distances)
    
    # Rayon adaptatif: 5x distance moyenne au plus proche voisin
    adaptive_radius = avg_1nn * 5.0
    
    print(f"Distance 1er voisin: {avg_1nn*1000:.2f} mm")
    print(f"Rayon adaptatif: {adaptive_radius*1000:.2f} mm")
    
    return adaptive_radius

def calculate_auto_louvain_coefficient(points):
    """
    Calcule le coefficient Louvain automatique basé sur la densité
    Adapté de alpha_louvain_interactive.py
    """
    # Calculer le volume de la bounding box
    min_bound = np.min(points, axis=0)
    max_bound = np.max(points, axis=0)
    dimensions = max_bound - min_bound
    volume = np.prod(dimensions)
    
    # Calculer la densité (points par m³)
    density = len(points) / volume if volume > 0 else 1
    
    # Coefficient basé sur log10 de la densité divisé par 2
    auto_coeff = max(0.1, np.log10(density) / 2)
    
    print(f"Points: {len(points)}")
    print(f"Volume: {volume:.6f} m³")
    print(f"Densité: {density:.2f} points/m³")
    print(f"Coefficient auto: {auto_coeff:.2f}")
    
    return auto_coeff

def build_connectivity_graph(points, radius):
    """
    Construit le graphe de connectivité
    Adapté de alpha_louvain_interactive.py
    """
    start_time = time.time()
    
    # Créer un graphe vide
    graph = nx.Graph()
    
    # Ajouter les nœuds (un par point)
    for i in range(len(points)):
        graph.add_node(i)
    
    # Utiliser un KDTree pour la recherche efficace des voisins
    tree = cKDTree(points)
    
    # Pour chaque point, trouver ses voisins dans le rayon spécifié
    for i in range(len(points)):
        # Trouver les indices des voisins
        indices = tree.query_ball_point(points[i], radius)
        
        # Ajouter des arêtes vers les voisins
        for j in indices:
            if i < j:  # Pour éviter les doublons
                # Calculer la distance euclidienne
                dist = np.linalg.norm(points[i] - points[j])
                
                # Le poids est l'inverse de la distance
                weight = 1.0 / max(dist, 1e-6)
                
                graph.add_edge(i, j, weight=weight)
        
        # Afficher la progression
        if i % 5000 == 0 or i == len(points) - 1:
            print(f"  Progression: {i+1}/{len(points)} points")
    
    print(f"Graphe: {graph.number_of_nodes()} nœuds, {graph.number_of_edges()} arêtes")
    print(f"Temps: {time.time() - start_time:.2f}s")
    
    return graph

def detect_communities_louvain_multiple(graph, resolution, min_size, n_iterations=5):
    """
    Détecte les communautés avec Louvain randomisé
    Adapté de alpha_louvain_interactive.py
    """
    if not LOUVAIN_AVAILABLE:
        print("Erreur: Module python-louvain non disponible")
        return []
        
    if n_iterations <= 0:
        print("ERREUR: Le nombre d'itérations doit être positif.")
        return []
    
    best_partition = None
    best_modularity = -1
    best_communities = []
    
    print(f"Exécution de Louvain {n_iterations} fois avec ordre aléatoire...")
    
    # Créer une copie du graphe pour ne pas le modifier
    graph_copy = graph.copy()
    
    for i in range(n_iterations):
        start_time = time.time()
        
        # Réordonner aléatoirement les nœuds
        shuffled_nodes = list(graph_copy.nodes())
        random.shuffle(shuffled_nodes)
        
        # Créer un dictionnaire de correspondance
        node_map = {old: new for new, old in enumerate(shuffled_nodes)}
        reverse_map = {new: old for new, old in enumerate(shuffled_nodes)}
        
        # Créer un nouveau graphe avec les nœuds réordonnés
        shuffled_graph = nx.Graph()
        for old_u, old_v, data in graph_copy.edges(data=True):
            new_u, new_v = node_map[old_u], node_map[old_v]
            shuffled_graph.add_edge(new_u, new_v, **data)
        
        # Exécuter Louvain sur le graphe réordonné
        partition = community_louvain.best_partition(shuffled_graph, resolution=resolution)
        
        # Calculer la modularité de cette partition
        modularity = community_louvain.modularity(partition, shuffled_graph)
        
        # Mapper la partition aux nœuds originaux
        original_partition = {reverse_map[node]: comm for node, comm in partition.items()}
        
        # Si c'est la meilleure modularité jusqu'à présent, on la garde
        if modularity > best_modularity:
            best_modularity = modularity
            best_partition = original_partition
        
        print(f"  Itération {i+1}/{n_iterations}: Modularité = {modularity:.4f}, Temps = {time.time() - start_time:.2f}s")
    
    print(f"Meilleure modularité: {best_modularity:.4f}")
    
    # Regrouper les nœuds par communauté
    communities = {}
    for node, community_id in best_partition.items():
        if community_id not in communities:
            communities[community_id] = set()
        communities[community_id].add(node)
    
    # Filtrer les communautés trop petites
    filtered_communities = [comm for comm in communities.values() if len(comm) >= min_size]
    
    # Trier par taille décroissante
    sorted_communities = sorted(filtered_communities, key=len, reverse=True)
    
    print(f"Communautés totales: {len(communities)}")
    print(f"Communautés >= {min_size} points: {len(filtered_communities)}")
    
    # Afficher des statistiques sur les communautés
    if sorted_communities:
        print("Top 5 communautés:")
        for i, comm in enumerate(sorted_communities[:5]):
            print(f"  {i+1}: {len(comm)} points")
    
    return sorted_communities

def fit_plane_to_points(points, all_points=None, distance_threshold=0.005, ransac_n=3, num_iterations=1000):
    """
    Ajuste un plan à un ensemble de points via RANSAC et oriente la normale vers l'extérieur
    
    Args:
        points: Points de la communauté (feuille)
        all_points: Tous les points du nuage (pour calculer le centre de la plante)
        distance_threshold: Seuil de distance pour RANSAC
        ransac_n: Nombre de points pour RANSAC
        num_iterations: Nombre d'itérations pour RANSAC
        
    Returns:
        Dictionnaire avec les informations du plan
    """
    if len(points) < 3:
        print("Pas assez de points pour ajuster un plan")
        return {
            'normal': np.array([0, 0, 1]),
            'centroid': np.mean(points, axis=0) if len(points) > 0 else np.array([0, 0, 0]),
            'equation': [0, 0, 1, 0],
            'inlier_ratio': 0,
            'inliers': []
        }
    
    # Déterminer le centre de la plante (centroïde de tous les points)
    if all_points is None:
        # Si all_points n'est pas fourni, utiliser le centroïde des points XY comme référence
        # mais avec une hauteur Z minimale
        xy_centroid = np.mean(points[:, :2], axis=0)
        min_z = np.min(points[:, 2])
        plant_center = np.array([xy_centroid[0], xy_centroid[1], min_z])
    else:
        # Utiliser le centroïde de tous les points comme centre de la plante
        plant_center = np.mean(all_points, axis=0)
    
    # Créer un nuage de points Open3D
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)
    
    # Estimer les normales
    pcd.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.02, max_nn=30))
    
    # Ajuster un plan avec RANSAC
    try:
        plane_model, inliers = pcd.segment_plane(distance_threshold=distance_threshold,
                                               ransac_n=ransac_n,
                                               num_iterations=num_iterations)
        
        # Extraire les paramètres du plan: ax + by + cz + d = 0
        [a, b, c, d] = plane_model
        
        # Normaliser le vecteur normal
        normal = np.array([a, b, c])
        normal_length = np.linalg.norm(normal)
        if normal_length > 0:
            normal = normal / normal_length
        
        # Calculer le pourcentage d'inliers
        inlier_ratio = len(inliers) / len(points) if len(points) > 0 else 0
        
        # Calculer le barycentre
        centroid = np.mean(points, axis=0)
        
        # Vérifier l'orientation de la normale (pour qu'elle pointe "vers l'extérieur")
        direction_to_center = plant_center - centroid
        
        # Si la normale pointe vers le centre, l'inverser
        # Utiliser une marge pour éviter les cas limites
        dot_product = np.dot(normal, direction_to_center)
        if dot_product > 0.1 * np.linalg.norm(direction_to_center):
            normal = -normal
            a, b, c = -a, -b, -c
            d = -d
        
        # Créer le dictionnaire de résultats
        plane_info = {
            'normal': normal,
            'centroid': centroid,
            'equation': [a, b, c, d],
            'inlier_ratio': inlier_ratio,
            'inliers': inliers
        }
        
        return plane_info
        
    except Exception as e:
        print(f"Erreur lors de l'ajustement du plan: {e}")
        # Retourner une normale par défaut (vers le haut)
        return {
            'normal': np.array([0, 0, 1]),
            'centroid': np.mean(points, axis=0),
            'equation': [0, 0, 1, 0],
            'inlier_ratio': 0,
            'inliers': []
        }

def calculate_target_point(leaf_data, distance=0.10):
    """
    Calcule le point cible à une distance donnée du plan de la feuille
    
    Args:
        leaf_data: Dictionnaire contenant les données de la feuille
        distance: Distance souhaitée du plan (en mètres)
    
    Returns:
        Coordonnées du point cible [x, y, z]
    """
    centroid = np.array(leaf_data['centroid'])
    normal = np.array(leaf_data['normal'])
    
    # Calculer le point cible en suivant la normale
    target_point = centroid + normal * distance
    
    return target_point.tolist()

def extract_leaf_data_from_communities(communities, points, min_inlier_ratio=0.7, distance=0.1):
    """
    Extrait les données des feuilles à partir des communautés détectées
    
    Args:
        communities: Liste des communautés (ensemble d'indices)
        points: Nuage de points complet
        min_inlier_ratio: Ratio minimum d'inliers pour considérer une surface comme valide
        distance: Distance aux feuilles en mètres pour le calcul des points cibles
    
    Returns:
        Liste des données de feuilles au format standardisé
    """
    leaves_data = []
    
    # Calculer le centre approximatif de la plante
    plant_center = np.mean(points, axis=0)
    # Utiliser une hauteur minimale pour le centre (base de la plante)
    plant_center[2] = np.min(points[:, 2])
    
    print(f"\nUtilisation d'une distance de {distance*100:.1f} cm pour calculer les points cibles")
    
    for i, community in enumerate(communities):
        # Extraire les points de cette communauté
        comm_indices = list(community)
        comm_points = points[comm_indices]
        
        # Calculer le centroïde
        centroid = np.mean(comm_points, axis=0)
        
        # Ajuster un plan à la communauté en passant tous les points
        plane_info = fit_plane_to_points(comm_points, points)
        
        # Vérifier si le plan est de bonne qualité
        if plane_info['inlier_ratio'] < min_inlier_ratio:
            print(f"Communauté {i+1}: Ratio d'inliers trop faible ({plane_info['inlier_ratio']:.2f})")
            continue
        
        # Double vérification de l'orientation de la normale vers l'extérieur
        direction_to_center = plant_center - centroid
        dot_product = np.dot(plane_info['normal'], direction_to_center)
        if dot_product > 0:
            # La normale pointe encore vers le centre - l'inverser
            normal = -np.array(plane_info['normal'])
            plane_info['normal'] = normal
            # Inverser aussi l'équation du plan
            a, b, c, d = plane_info['equation']
            plane_info['equation'] = [-a, -b, -c, -d]
            print(f"Communauté {i+1}: Normale réorientée vers l'extérieur")
        
        # Calculer le point cible à la distance spécifiée de la feuille
        target_point = calculate_target_point(plane_info, distance=distance)
        
        # Créer l'entrée pour cette feuille
        leaf_data = {
            "id": i + 1,  # ID commençant à 1
            "centroid": centroid.tolist(),
            "normal": plane_info["normal"].tolist(),
            "plane_equation": plane_info["equation"],
            "inlier_ratio": plane_info["inlier_ratio"],
            "points_indices": comm_indices,
            "points": comm_points.tolist(),
            "target_point": target_point
        }
        
        leaves_data.append(leaf_data)
    
    print(f"Feuilles extraites: {len(leaves_data)}")
    return leaves_data