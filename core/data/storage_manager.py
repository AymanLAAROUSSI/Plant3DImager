#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Storage manager for files and directories
"""

import os
import json
import time
from datetime import datetime
from core.utils import config

class StorageManager:
    def __init__(self, parent_dir=None, mode="acquisition"):
        """Initialize the storage manager"""
        # Determine parent directory
        if parent_dir is None:
            # First create results directory if it doesn't exist
            os.makedirs(config.RESULTS_DIR, exist_ok=True)
            
            if mode == "acquisition":
                self.parent_dir = os.path.join(config.RESULTS_DIR, config.ACQUISITION_DIR)
            else:  # targeting
                self.parent_dir = os.path.join(config.RESULTS_DIR, config.TARGETING_DIR)
        else:
            self.parent_dir = parent_dir
        
        self.mode = mode
        self.dirs = None
    
    def create_directory_structure(self, suffix=None):
        """
        Create a complete directory structure for the current execution
        
        Args:
            suffix: Optional suffix for directory name
            
        Returns:
            Dictionary of created paths
        """
        # Create parent directory if it doesn't exist
        os.makedirs(self.parent_dir, exist_ok=True)
        
        # Generate timestamp for directory name
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        
        # Create main directory name
        if suffix:
            dir_name = f"{suffix}_{timestamp}"
        else:
            if self.mode == "acquisition":
                dir_name = f"circular_scan_{timestamp}"  # More descriptive name
            else:  # targeting
                dir_name = f"leaf_analysis_{timestamp}"  # More descriptive name
        
        # Full path to main directory
        main_dir = os.path.join(self.parent_dir, dir_name)
        
        # Create subdirectories based on mode
        if self.mode == "acquisition":
            # Structure for acquisition
            images_dir = os.path.join(main_dir, "images")
            metadata_dir = os.path.join(main_dir, "metadata")
            metadata_images_dir = os.path.join(metadata_dir, "images")
            
            # Create directories
            os.makedirs(main_dir, exist_ok=True)
            os.makedirs(images_dir, exist_ok=True)
            os.makedirs(metadata_dir, exist_ok=True)
            os.makedirs(metadata_images_dir, exist_ok=True)
            
            # Store paths
            self.dirs = {
                "main": main_dir,
                "images": images_dir,
                "metadata": metadata_dir,
                "metadata_images": metadata_images_dir
            }
            
            print(f"Directory created for photos: {main_dir}")
            print(f"Subdirectories created: images/, metadata/, metadata/images/")
            
        else:  # targeting
            # Structure for targeting
            images_dir = os.path.join(main_dir, "images")
            analysis_dir = os.path.join(main_dir, "analysis")
            visualization_dir = os.path.join(main_dir, "visualizations")
            
            # Create directories
            os.makedirs(main_dir, exist_ok=True)
            os.makedirs(images_dir, exist_ok=True)
            os.makedirs(analysis_dir, exist_ok=True)
            os.makedirs(visualization_dir, exist_ok=True)
            
            # Store paths
            self.dirs = {
                "main": main_dir,
                "images": images_dir,
                "analysis": analysis_dir,
                "visualizations": visualization_dir
            }
            
            print(f"Directory created for results: {main_dir}")
            print(f"Subdirectories created: images/, analysis/, visualizations/")
        
        return self.dirs
    
    def save_json(self, data, filename, subdirectory=None):
        """Save data as JSON"""
        if self.dirs is None:
            raise RuntimeError("Directory structure not initialized")
        
        try:
            # Determine full path
            if subdirectory and subdirectory in self.dirs:
                filepath = os.path.join(self.dirs[subdirectory], filename)
            else:
                filepath = os.path.join(self.dirs["main"], filename)
            
            # Create parent directory if needed
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Save data
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=4)
                
            print(f"JSON file saved: {filepath}")
            return filepath
        
        except Exception as e:
            print(f"Error saving JSON file: {e}")
            return None
    
    def save_toml(self, content, filename):
        """Save content as TOML"""
        if self.dirs is None:
            raise RuntimeError("Directory structure not initialized")
        
        try:
            # Determine full path
            filepath = os.path.join(self.dirs["main"], filename)
            
            # Create parent directory if needed
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Save content
            with open(filepath, 'w') as f:
                f.write(content)
                
            print(f"TOML file saved: {filepath}")
            return filepath
        
        except Exception as e:
            print(f"Error saving TOML file: {e}")
            return None