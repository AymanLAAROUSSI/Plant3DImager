#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Contrôleur de caméra unifié pour les modules d'acquisition et de ciblage
"""

import os
import time
from datetime import datetime
from romi.camera import Camera

class CameraController:
    def __init__(self):
        """Initialise le contrôleur de caméra"""
        self.camera = None
        self.photos_dir = None
        self.initialized = False
    
    def connect(self):
        """Connecte à la caméra et l'initialise"""
        if self.initialized:
            return self
        
        try:
            print("Initialisation de la caméra...")
            self.camera = Camera("camera", "camera")
            self.initialized = True
            return self
        except Exception as e:
            print(f"Erreur lors de l'initialisation de la caméra: {e}")
            raise
    
    def set_output_directory(self, directory):
        """Définit le répertoire de sortie pour les photos"""
        self.photos_dir = directory
        os.makedirs(directory, exist_ok=True)
        print(f"Répertoire de sortie des photos: {directory}")
    
    def take_photo(self, filename=None, metadata=None):
        """Prend une photo avec la caméra"""
        if not self.initialized:
            raise RuntimeError("Caméra non initialisée")
        
        try:
            print("Capture d'image en cours...")
            image = self.camera.grab()
            
            if image is not None:
                # Générer un nom de fichier s'il n'est pas spécifié
                if filename is None:
                    timestamp = time.strftime("%Y%m%d-%H%M%S")
                    filename = f"photo_{timestamp}.jpg"
                
                # Ajouter le chemin complet
                if self.photos_dir:
                    filepath = os.path.join(self.photos_dir, filename)
                else:
                    filepath = filename
                
                # Sauvegarder l'image
                image.save(filepath)
                print(f"Image sauvegardée: {filepath}")
                return filepath, metadata
            else:
                print("Erreur: Impossible de capturer l'image")
                return None, None
                
        except Exception as e:
            print(f"Erreur lors de la prise de photo: {e}")
            return None, None
    
    def shutdown(self):
        """Arrête proprement la caméra"""
        if not self.initialized:
            return True
            
        self.initialized = False
        return True