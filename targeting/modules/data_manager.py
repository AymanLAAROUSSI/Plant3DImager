# modules/data_manager.py
import os
import json
import numpy as np
import open3d as o3d
import time
from datetime import datetime
from scipy.spatial import cKDTree

def load_and_scale_pointcloud(file_path, scale_factor=0.001):
    """
    Charge et met à l'échelle le nuage de points
    Adapté de alpha_louvain_interactive.py
    """
    print(f"Chargement du nuage de points depuis {file_path}...")
    
    try:
        # Vérifier l'existence du fichier
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Le fichier {file_path} n'existe pas.")
        
        # Charger le nuage avec Open3D
        pcd = o3d.io.read_point_cloud(file_path)
        points = np.asarray(pcd.points) * scale_factor
        pcd.points = o3d.utility.Vector3dVector(points)
        
        print(f"Nuage chargé: {len(points)} points, échelle: {scale_factor}")
        min_bound = np.min(points, axis=0)
        max_bound = np.max(points, axis=0)
        size = max_bound - min_bound
        print(f"Dimensions: {size[0]:.3f} x {size[1]:.3f} x {size[2]:.3f} m")
        
        return pcd, points
        
    except Exception as e:
        print(f"ERREUR: {e}")
        raise

def apply_cropping_method(points, crop_method='single_furthest', crop_percentage=0.25, z_offset=0.0):
    """
    Applique la méthode de cropping choisie
    Adapté de alpha_louvain_interactive.py
    """
    z_values = points[:, 2]
    min_z, max_z = np.min(z_values), np.max(z_values)
    
    if crop_method == 'none':
        # Pas de cropping - prendre le minimum de Z (tous les points)
        z_threshold = min_z
        
    elif crop_method == 'top_percentage':
        # Méthode par pourcentage supérieur
        z_range = max_z - min_z
        z_threshold = max_z - (z_range * (1.0 - crop_percentage))
        
    else:  # single_furthest (par défaut)
        # Méthode du point le plus éloigné unique
        xy_points = points[:, :2]
        xy_center = np.mean(xy_points, axis=0)
        distances = np.sqrt(np.sum((xy_points - xy_center)**2, axis=1))
        furthest_idx = np.argmax(distances)
        furthest_point_z = points[furthest_idx, 2]
        z_threshold = furthest_point_z - z_offset
    
    return z_threshold

def compute_cropped_alpha_shape(pcd, points, alpha_value=0.1, crop_method='single_furthest', 
                              crop_percentage=0.25, z_offset=0.0, output_dir=None):
    """
    Calcule l'alpha shape croppé
    Adapté de alpha_louvain_interactive.py
    """
    # Appliquer le cropping
    z_threshold = apply_cropping_method(points, crop_method, crop_percentage, z_offset)
    
    # Cropper les points
    mask = points[:, 2] >= z_threshold
    cropped_points = points[mask]
    n_cropped = len(cropped_points)
    
    print(f"Points après cropping: {n_cropped} ({n_cropped/len(points)*100:.1f}%)")
    print(f"Seuil Z: {z_threshold:.4f} m")
    
    # Créer le nuage croppé
    cropped_pcd = o3d.geometry.PointCloud()
    cropped_pcd.points = o3d.utility.Vector3dVector(cropped_points)
    
    # Calculer l'Alpha Shape
    print(f"Calcul Alpha Shape: alpha = {alpha_value}")
    start_time = time.time()
    
    try:
        mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_alpha_shape(cropped_pcd, alpha_value)
        alpha_points = np.asarray(mesh.vertices)
        
        print(f"Alpha Shape calculé en {time.time() - start_time:.2f}s")
        print(f"Points Alpha: {len(alpha_points)} ({len(alpha_points)/n_cropped*100:.1f}%)")
        
        # Re-cropping léger pour éliminer les résidus
        z_min, z_max = np.min(points[:, 2]), np.max(points[:, 2])
        z_range = z_max - z_min
        recrop_offset = 0.005 * z_range
        recrop_threshold = z_threshold + recrop_offset
        
        # Appliquer le re-cropping
        recrop_mask = alpha_points[:, 2] >= recrop_threshold
        alpha_points = alpha_points[recrop_mask]
        
        print(f"Re-cropping: offset de {recrop_offset:.4f} m")
        print(f"Points final: {len(alpha_points)}")
        
        # Créer le nuage de points final
        alpha_pcd = o3d.geometry.PointCloud()
        alpha_pcd.points = o3d.utility.Vector3dVector(alpha_points)
        
        # Sauvegarder l'Alpha Shape si un répertoire est spécifié
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            alpha_output = os.path.join(output_dir, f"alpha_shape_{alpha_value:.3f}.ply")
            o3d.io.write_point_cloud(alpha_output, alpha_pcd)
            print(f"Alpha Shape sauvegardé: {alpha_output}")
        
        return alpha_pcd, alpha_points
        
    except Exception as e:
        print(f"ERREUR lors du calcul de l'Alpha Shape: {e}")
        raise

def save_leaves_data(leaves_data, output_file):
    """Sauvegarde les données des feuilles au format JSON"""
    try:
        # Créer le répertoire si nécessaire
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Pour chaque feuille, filtrer les champs pour ne pas inclure les points complets
        # (qui peuvent être très volumineux)
        leaves_to_save = []
        for leaf in leaves_data:
            # Créer une copie sans les points complets
            leaf_copy = leaf.copy()
            
            # Supprimer les champs volumineux
            if 'points' in leaf_copy:
                del leaf_copy['points']
            if 'points_indices' in leaf_copy:
                del leaf_copy['points_indices']
            
            leaves_to_save.append(leaf_copy)
        
        with open(output_file, 'w') as f:
            # Formater avec indentation pour lisibilité
            json.dump({"leaves": leaves_to_save}, f, indent=2)
            
        print(f"Données sauvegardées dans {output_file}")
        return True
    except Exception as e:
        print(f"Erreur lors de la sauvegarde: {e}")
        return False

def load_leaves_data(input_file):
    """Charge les données des feuilles depuis un fichier JSON"""
    try:
        with open(input_file, 'r') as f:
            data = json.load(f)
        
        # Valider la structure
        if "leaves" not in data:
            raise ValueError("Format JSON invalide: clé 'leaves' manquante")
        
        print(f"Données chargées: {len(data['leaves'])} feuilles")
        return data["leaves"]
    except Exception as e:
        print(f"Erreur lors du chargement: {e}")
        raise

def create_output_directory():
    """Crée un répertoire de sortie daté"""
    # Répertoire parent
    parent_dir = "leaf_targeting_results"
    
    # S'assurer que le répertoire parent existe
    os.makedirs(parent_dir, exist_ok=True)
    
    # Créer un sous-répertoire avec la date et l'heure actuelles
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_dir = os.path.join(parent_dir, f"leaf_targeting_{timestamp}")
    
    # Créer l'arborescence complète
    images_dir = os.path.join(output_dir, "images")
    analysis_dir = os.path.join(output_dir, "analysis")
    visualization_dir = os.path.join(output_dir, "visualizations")
    
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(analysis_dir, exist_ok=True)
    os.makedirs(visualization_dir, exist_ok=True)
    
    print(f"Répertoire créé pour les résultats: {output_dir}")
    print(f"Sous-répertoires créés: images/, analysis/, visualizations/")
    
    return {
        "main": output_dir,
        "images": images_dir,
        "analysis": analysis_dir,
        "visualizations": visualization_dir
    }
