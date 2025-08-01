# targeting/modules/robot_controller.py
import time
import math
import numpy as np
import os
from datetime import datetime

class RobotController:
    def __init__(self, cnc=None, camera=None, gimbal=None, output_dirs=None, speed=0.1, update_interval=0.1):
        """
        Initialize robot controller
        
        Args:
            cnc: CNCController instance
            camera: CameraController instance
            gimbal: GimbalController instance
            output_dirs: Dictionary of output directories
            speed: Movement speed (m/s)
            update_interval: Update interval during movement (s)
        """
        self.cnc = cnc
        self.camera = camera
        self.gimbal = gimbal
        self.speed = speed
        self.update_interval = update_interval
        
        # Photos directory
        self.photos_dir = None
        if output_dirs and 'images' in output_dirs:
            self.photos_dir = output_dirs['images']
        
        # State
        self.initialized = cnc is not None and camera is not None and gimbal is not None
        
        if self.initialized:
            print("Robot controller successfully initialized.")
        else:
            print("Robot controller partially initialized - some components missing.")
    
    def execute_path(self, path, leaf_centroids=None, leaf_ids=None, auto_photo=True, stabilization_time=3.0):
        """
        Execute a complete trajectory
        
        Args:
            path: List of dictionaries describing the trajectory
            leaf_centroids: List of leaf centroid positions
            leaf_ids: List of leaf IDs corresponding to centroids
            auto_photo: Take photos automatically at target points
            stabilization_time: Wait time for stabilization before photo (in seconds)
        
        Returns:
            True if execution is successful, False otherwise
        """
        if not self.initialized:
            print("Error: Robot not fully initialized.")
            return False
        
        try:
            # Variables to track leaves
            current_leaf_index = 0
            photos_taken = []
            
            # Identify target points and last intermediate points before each target
            target_indices = []
            for i, point_info in enumerate(path):
                if point_info["type"] == "target":
                    target_indices.append(i)
            
            # Follow path
            for i, point_info in enumerate(path):
                position = point_info["position"]
                point_type = point_info["type"]
                comment = point_info.get("comment", "")
                
                print(f"\n--- Step {i+1}/{len(path)}: {point_type} ---")
                if comment:
                    print(f"Info: {comment}")
                
                # Move to this point
                success = self.cnc.move_to(
                    position[0], position[1], position[2], wait=True
                )
                
                if not success:
                    print(f"Error during movement to step {i+1}")
                    continue
                
                # Check if we're at last intermediate point before a target point
                # i.e., a via_point directly followed by a target
                if point_type == "via_point" and i+1 < len(path) and path[i+1]["type"] == "target":
                    # Find index of next leaf
                    next_target_index = i + 1
                    next_leaf_index = target_indices.index(next_target_index)
                    
                    if leaf_centroids is not None and next_leaf_index < len(leaf_centroids):
                        print(f"\n--- Orienting toward leaf at last intermediate point ---")
                        
                        # Get current position
                        final_pos = self.cnc.get_position()
                        
                        # Get next leaf centroid
                        next_leaf_centroid = leaf_centroids[next_leaf_index]
                        
                        print(f"DEBUG: Orienting toward centroid: {next_leaf_centroid}")
                        
                        # Orient camera toward next leaf centroid
                        success = self.gimbal.aim_at_target(final_pos, next_leaf_centroid, wait=True, invert_tilt=True)
                        
                        if not success:
                            print("Error orienting toward leaf")
                        else:
                            print("Camera successfully oriented toward leaf")
                
                # If it's a target point and we have leaf centroids
                if point_type == "target" and leaf_centroids is not None and current_leaf_index < len(leaf_centroids):
                    # Get current leaf information
                    leaf_centroid = leaf_centroids[current_leaf_index]
                    leaf_id = leaf_ids[current_leaf_index] if leaf_ids and current_leaf_index < len(leaf_ids) else None
                    
                    print(f"\n--- Orienting toward leaf {leaf_id if leaf_id is not None else ''} ---")
                    
                    # Get final position
                    final_pos = self.cnc.get_position()
                    
                    # Display debug info about original centroid
                    print(f"DEBUG: Fine adjustment toward centroid: {leaf_centroid}")
                    
                    # Orient camera toward leaf with tilt inversion
                    # We use original centroid without modification,
                    # and invert tilt in aim_at_target method
                    success = self.gimbal.aim_at_target(final_pos, leaf_centroid, wait=True, invert_tilt=True)
                    
                    if not success:
                        print("Error orienting toward leaf")
                        current_leaf_index += 1
                        continue
                    
                    # Pause for stabilization
                    print(f"Stabilizing for {stabilization_time} seconds...")
                    time.sleep(stabilization_time)
                    
                    # Take photo automatically if requested
                    if auto_photo:
                        timestamp = time.strftime("%Y%m%d-%H%M%S")
                        if leaf_id is not None:
                            filename = f"leaf_{leaf_id}_{timestamp}.jpg"
                        else:
                            filename = f"leaf_target_{current_leaf_index+1}_{timestamp}.jpg"
                        
                        # Create dictionary with camera pose information
                        camera_pose = {
                            'x': final_pos['x'],
                            'y': final_pos['y'],
                            'z': final_pos['z'],
                            'pan_angle': self.gimbal.current_pan,
                            'tilt_angle': self.gimbal.current_tilt
                        }
                        
                        photo_path, _ = self.camera.take_photo(filename, camera_pose)
                        
                        if photo_path:
                            photos_taken.append((photo_path, leaf_id))
                            print(f"Photo taken: {photo_path}")
                    else:
                        # Offer to take photo manually
                        take_photo = input("\nTake a photo? (y/n): ").lower()
                        if take_photo == 'y':
                            timestamp = time.strftime("%Y%m%d-%H%M%S")
                            if leaf_id is not None:
                                filename = f"leaf_{leaf_id}_{timestamp}.jpg"
                            else:
                                filename = f"leaf_target_{current_leaf_index+1}_{timestamp}.jpg"
                            
                            # Create dictionary with camera pose information
                            camera_pose = {
                                'x': final_pos['x'],
                                'y': final_pos['y'],
                                'z': final_pos['z'],
                                'pan_angle': self.gimbal.current_pan,
                                'tilt_angle': self.gimbal.current_tilt
                            }
                            
                            photo_path, _ = self.camera.take_photo(filename, camera_pose)
                            
                            if photo_path:
                                photos_taken.append((photo_path, leaf_id))
                                print(f"Photo taken: {photo_path}")
                    
                    # Increment leaf index
                    current_leaf_index += 1
            
            # Photos summary
            if photos_taken:
                print("\n=== PHOTOS SUMMARY ===")
                for i, (path, leaf_id) in enumerate(photos_taken):
                    print(f"{i+1}. Leaf {leaf_id if leaf_id is not None else '?'}: {path}")
            
            return True
            
        except Exception as e:
            print(f"Error executing trajectory: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def normalize_angle_difference(self, delta):
        """Normalize angle difference to take shortest path"""
        if delta > 180:
            delta -= 360
        elif delta < -180:
            delta += 360
        return delta
    
    def shutdown(self):
        """Properly shut down the robot"""
        print("Shutting down robot...")
        
        # Perform same operations as in old version
        if self.cnc is not None:
            try:
                print("Moving to position (0, 0, 0)...")
                self.cnc.move_to(0, 0, 0, wait=True)
                
                print("Returning to home position (homing)...")
                self.cnc.home()  # Explicit homing here
                
                # We don't do power_down here as it will be done by main controller
            except Exception as e:
                print(f"Error during homing: {e}")
        
        # Camera reset
        if self.gimbal is not None:
            try:
                print("Resetting camera to initial position (0,0)...")
                self.gimbal.reset_position()
            except Exception as e:
                print(f"Error resetting camera: {e}")
        
        return True