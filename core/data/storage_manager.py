#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Gestionnaire de stockage pour les fichiers et répertoires
"""

import os
import json
import time
from datetime import datetime
from core.utils import config

class StorageManager:
    def __init__(self, parent_dir=None, mode="acquisition"):
        """Initialise le gestionnaire de stockage"""
        # Déterminer le répertoire parent
        if parent_dir is None:
            # Créer d'abord le répertoire results s'il n'existe pas
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
        Crée une structure de répertoires complète pour l'exécution courante
        
        Args:
            suffix: Suffixe optionnel pour le nom du répertoire
            
        Returns:
            Dictionnaire des chemins créés
        """
        # Créer le répertoire parent s'il n'existe pas
        os.makedirs(self.parent_dir, exist_ok=True)
        
        # Générer le timestamp pour le nom du répertoire
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        
        # Créer le nom du répertoire principal
        if suffix:
            dir_name = f"{suffix}_{timestamp}"
        else:
            if self.mode == "acquisition":
                dir_name = f"circular_scan_{timestamp}"  # Nom plus descriptif
            else:  # targeting
                dir_name = f"leaf_analysis_{timestamp}"  # Nom plus descriptif
        
        # Chemin complet du répertoire principal
        main_dir = os.path.join(self.parent_dir, dir_name)
        
        # Créer les sous-répertoires en fonction du mode
        if self.mode == "acquisition":
            # Structure pour l'acquisition
            images_dir = os.path.join(main_dir, "images")
            metadata_dir = os.path.join(main_dir, "metadata")
            metadata_images_dir = os.path.join(metadata_dir, "images")
            
            # Créer les répertoires
            os.makedirs(main_dir, exist_ok=True)
            os.makedirs(images_dir, exist_ok=True)
            os.makedirs(metadata_dir, exist_ok=True)
            os.makedirs(metadata_images_dir, exist_ok=True)
            
            # Stocker les chemins
            self.dirs = {
                "main": main_dir,
                "images": images_dir,
                "metadata": metadata_dir,
                "metadata_images": metadata_images_dir
            }
            
            print(f"Répertoire créé pour les photos: {main_dir}")
            print(f"Sous-répertoires créés: images/, metadata/, metadata/images/")
            
        else:  # targeting
            # Structure pour le ciblage
            images_dir = os.path.join(main_dir, "images")
            analysis_dir = os.path.join(main_dir, "analysis")
            visualization_dir = os.path.join(main_dir, "visualizations")
            
            # Créer les répertoires
            os.makedirs(main_dir, exist_ok=True)
            os.makedirs(images_dir, exist_ok=True)
            os.makedirs(analysis_dir, exist_ok=True)
            os.makedirs(visualization_dir, exist_ok=True)
            
            # Stocker les chemins
            self.dirs = {
                "main": main_dir,
                "images": images_dir,
                "analysis": analysis_dir,
                "visualizations": visualization_dir
            }
            
            print(f"Répertoire créé pour les résultats: {main_dir}")
            print(f"Sous-répertoires créés: images/, analysis/, visualizations/")
        
        return self.dirs
    
    def save_json(self, data, filename, subdirectory=None):
        """Sauvegarde des données au format JSON"""
        if self.dirs is None:
            raise RuntimeError("Structure de répertoires non initialisée")
        
        try:
            # Déterminer le chemin complet
            if subdirectory and subdirectory in self.dirs:
                filepath = os.path.join(self.dirs[subdirectory], filename)
            else:
                filepath = os.path.join(self.dirs["main"], filename)
            
            # Créer le répertoire parent si nécessaire
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Sauvegarder les données
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=4)
                
            print(f"Fichier JSON sauvegardé: {filepath}")
            return filepath
        
        except Exception as e:
            print(f"Erreur lors de la sauvegarde du fichier JSON: {e}")
            return None
    
    def save_toml(self, content, filename):
        """Sauvegarde du contenu au format TOML"""
        if self.dirs is None:
            raise RuntimeError("Structure de répertoires non initialisée")
        
        try:
            # Déterminer le chemin complet
            filepath = os.path.join(self.dirs["main"], filename)
            
            # Créer le répertoire parent si nécessaire
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Sauvegarder le contenu
            with open(filepath, 'w') as f:
                f.write(content)
                
            print(f"Fichier TOML sauvegardé: {filepath}")
            return filepath
        
        except Exception as e:
            print(f"Erreur lors de la sauvegarde du fichier TOML: {e}")
            return None