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
    Load and scale point cloud
    Adapted from alpha_louvain_interactive.py
    """
    print(f"Loading point cloud from {file_path}...")
    
    try:
        # Check file existence
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File {file_path} does not exist.")
        
        # Load cloud with Open3D
        pcd = o3d.io.read_point_cloud(file_path)
        points = np.asarray(pcd.points) * scale_factor
        pcd.points = o3d.utility.Vector3dVector(points)
        
        print(f"Cloud loaded: {len(points)} points, scale: {scale_factor}")
        min_bound = np.min(points, axis=0)
        max_bound = np.max(points, axis=0)
        size = max_bound - min_bound
        print(f"Dimensions: {size[0]:.3f} x {size[1]:.3f} x {size[2]:.3f} m")
        
        return pcd, points
        
    except Exception as e:
        print(f"ERROR: {e}")
        raise

def apply_cropping_method(points, crop_method='single_furthest', crop_percentage=0.25, z_offset=0.0):
    """
    Apply chosen cropping method
    Adapted from alpha_louvain_interactive.py
    """
    z_values = points[:, 2]
    min_z, max_z = np.min(z_values), np.max(z_values)
    
    if crop_method == 'none':
        # No cropping - take minimum Z (all points)
        z_threshold = min_z
        
    elif crop_method == 'top_percentage':
        # Top percentage method
        z_range = max_z - min_z
        z_threshold = max_z - (z_range * (1.0 - crop_percentage))
        
    else:  # single_furthest (default)
        # Single furthest point method
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
    Compute cropped alpha shape
    Adapted from alpha_louvain_interactive.py
    """
    # Apply cropping
    z_threshold = apply_cropping_method(points, crop_method, crop_percentage, z_offset)
    
    # Crop points
    mask = points[:, 2] >= z_threshold
    cropped_points = points[mask]
    n_cropped = len(cropped_points)
    
    print(f"Points after cropping: {n_cropped} ({n_cropped/len(points)*100:.1f}%)")
    print(f"Z threshold: {z_threshold:.4f} m")
    
    # Create cropped cloud
    cropped_pcd = o3d.geometry.PointCloud()
    cropped_pcd.points = o3d.utility.Vector3dVector(cropped_points)
    
    # Calculate Alpha Shape
    print(f"Computing Alpha Shape: alpha = {alpha_value}")
    start_time = time.time()
    
    try:
        mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_alpha_shape(cropped_pcd, alpha_value)
        alpha_points = np.asarray(mesh.vertices)
        
        print(f"Alpha Shape computed in {time.time() - start_time:.2f}s")
        print(f"Alpha Points: {len(alpha_points)} ({len(alpha_points)/n_cropped*100:.1f}%)")
        
        # Light re-cropping to eliminate residues
        z_min, z_max = np.min(points[:, 2]), np.max(points[:, 2])
        z_range = z_max - z_min
        recrop_offset = 0.005 * z_range
        recrop_threshold = z_threshold + recrop_offset
        
        # Apply re-cropping
        recrop_mask = alpha_points[:, 2] >= recrop_threshold
        alpha_points = alpha_points[recrop_mask]
        
        print(f"Re-cropping: offset of {recrop_offset:.4f} m")
        print(f"Final points: {len(alpha_points)}")
        
        # Create final point cloud
        alpha_pcd = o3d.geometry.PointCloud()
        alpha_pcd.points = o3d.utility.Vector3dVector(alpha_points)
        
        # Save Alpha Shape if directory specified
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            alpha_output = os.path.join(output_dir, f"alpha_shape_{alpha_value:.3f}.ply")
            o3d.io.write_point_cloud(alpha_output, alpha_pcd)
            print(f"Alpha Shape saved: {alpha_output}")
        
        return alpha_pcd, alpha_points
        
    except Exception as e:
        print(f"ERROR computing Alpha Shape: {e}")
        raise

def save_leaves_data(leaves_data, output_file):
    """Save leaf data in JSON format"""
    try:
        # Create directory if needed
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # For each leaf, filter fields to exclude complete points
        # (which can be very voluminous)
        leaves_to_save = []
        for leaf in leaves_data:
            # Create copy without complete points
            leaf_copy = leaf.copy()
            
            # Remove voluminous fields
            if 'points' in leaf_copy:
                del leaf_copy['points']
            if 'points_indices' in leaf_copy:
                del leaf_copy['points_indices']
            
            leaves_to_save.append(leaf_copy)
        
        with open(output_file, 'w') as f:
            # Format with indentation for readability
            json.dump({"leaves": leaves_to_save}, f, indent=2)
            
        print(f"Data saved to {output_file}")
        return True
    except Exception as e:
        print(f"Error during save: {e}")
        return False

def load_leaves_data(input_file):
    """Load leaf data from JSON file"""
    try:
        with open(input_file, 'r') as f:
            data = json.load(f)
        
        # Validate structure
        if "leaves" not in data:
            raise ValueError("Invalid JSON format: missing 'leaves' key")
        
        print(f"Data loaded: {len(data['leaves'])} leaves")
        return data["leaves"]
    except Exception as e:
        print(f"Error during loading: {e}")
        raise

def create_output_directory():
    """Create a dated output directory"""
    # Parent directory
    parent_dir = "leaf_targeting_results"
    
    # Ensure parent directory exists
    os.makedirs(parent_dir, exist_ok=True)
    
    # Create subdirectory with current date and time
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_dir = os.path.join(parent_dir, f"leaf_targeting_{timestamp}")
    
    # Create complete directory structure
    images_dir = os.path.join(output_dir, "images")
    analysis_dir = os.path.join(output_dir, "analysis")
    visualization_dir = os.path.join(output_dir, "visualizations")
    
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(analysis_dir, exist_ok=True)
    os.makedirs(visualization_dir, exist_ok=True)
    
    print(f"Directory created for results: {output_dir}")
    print(f"Subdirectories created: images/, analysis/, visualizations/")
    
    return {
        "main": output_dir,
        "images": images_dir,
        "analysis": analysis_dir,
        "visualizations": visualization_dir
    }