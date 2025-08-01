#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module de chargement de la configuration JSON partagée entre les modules d'acquisition et de ciblage
"""

import json
import os
import sys

# Chemin vers le fichier de configuration - à la racine du projet
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'config.json')

# Variables globales pour stocker la configuration
_config_data = {}
_config_loaded = False

# Valeurs par défaut
_defaults = {
    "TARGET_POINT": [0.375, 0.35, 0.30],
    "CENTER_POINT": [0.375, 0.35, 0.00],
    "CIRCLE_RADIUS": 0.30,
    "NUM_POSITIONS": 80,
    "Z_OFFSET": 0.20,
    "ARDUINO_PORT": "/dev/ttyACM0",
    "CNC_SPEED": 0.1,
    "UPDATE_INTERVAL": 0.1,
    "STABILIZATION_TIME": 3.0,
    "RESULTS_DIR": "results",
    "ACQUISITION_DIR": "plant_acquisition",
    "TARGETING_DIR": "leaf_targeting",
    "SSH_HOST": "10.0.7.22",
    "SSH_USER": "ayman",
    "KEY_PATH": "/home/romi/.ssh/id_rsa",
    "REMOTE_WORK_PATH": "/mnt/diskSustainability/Scanner_Data/scanner_lyon/3dt_colA/Col_A_2021-01-29/",
    "LOCAL_ACQUISITION_BASE": "results/plant_acquisition",
    "LOCAL_PLY_TARGET": "results/pointclouds",
    "ROMI_CONFIG": "~/plant-3d-vision/configs/geom_pipe_real.toml"
}

def _load_config():
    """
    Charge la configuration à partir du fichier JSON
    """
    global _config_data, _config_loaded
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            _config_data = json.load(f)
        _config_loaded = True
        print(f"Configuration chargée depuis {CONFIG_FILE}")
    except FileNotFoundError:
        print(f"Fichier de configuration non trouvé: {CONFIG_FILE}")
        print("Création du fichier avec les valeurs par défaut...")
        _config_data = _defaults.copy()
        save_config(_config_data)
        _config_loaded = True
    except json.JSONDecodeError as e:
        print(f"Erreur de format dans le fichier de configuration: {e}")
        print("Utilisation des valeurs par défaut")
        _config_data = _defaults.copy()
        _config_loaded = False

def get(key, default=None):
    """
    Retourne la valeur de configuration pour la clé spécifiée
    
    Args:
        key: Clé de configuration
        default: Valeur par défaut si la clé n'existe pas
    
    Returns:
        Valeur de configuration
    """
    if not _config_loaded:
        _load_config()
    
    # Utiliser la valeur par défaut fournie ou celle des _defaults
    if default is None and key in _defaults:
        default = _defaults[key]
        
    value = _config_data.get(key, default)
    
    # Convertir les listes en tuples pour certaines clés
    if key in ["TARGET_POINT", "CENTER_POINT"] and isinstance(value, list):
        value = tuple(value)
        
    return value

def save_config(config_dict):
    """
    Sauvegarde les modifications de configuration dans le fichier JSON
    
    Args:
        config_dict: Dictionnaire contenant les nouvelles valeurs de configuration
    
    Returns:
        True si la sauvegarde est réussie, False sinon
    """
    global _config_data
    
    try:
        if not _config_loaded:
            _load_config()
        
        # Mettre à jour la configuration avec les nouvelles valeurs
        _config_data.update(config_dict)
        
        # Sauvegarder la configuration mise à jour
        with open(CONFIG_FILE, 'w') as f:
            json.dump(_config_data, f, indent=4)
            
        print(f"Configuration sauvegardée dans {CONFIG_FILE}")
        return True
    except Exception as e:
        print(f"Erreur lors de la sauvegarde de la configuration: {e}")
        return False

# Charger la configuration au démarrage
_load_config()

# Exposer les variables de configuration comme attributs du module
TARGET_POINT = get("TARGET_POINT")
CENTER_POINT = get("CENTER_POINT")
CIRCLE_RADIUS = get("CIRCLE_RADIUS")
NUM_POSITIONS = get("NUM_POSITIONS")
Z_OFFSET = get("Z_OFFSET")
ARDUINO_PORT = get("ARDUINO_PORT")
CNC_SPEED = get("CNC_SPEED")
UPDATE_INTERVAL = get("UPDATE_INTERVAL")
STABILIZATION_TIME = get("STABILIZATION_TIME")
RESULTS_DIR = get("RESULTS_DIR")
ACQUISITION_DIR = get("ACQUISITION_DIR")
TARGETING_DIR = get("TARGETING_DIR")
SSH_HOST = get("SSH_HOST")
SSH_USER = get("SSH_USER")
KEY_PATH = get("KEY_PATH")
REMOTE_WORK_PATH = get("REMOTE_WORK_PATH")
LOCAL_ACQUISITION_BASE = get("LOCAL_ACQUISITION_BASE")
LOCAL_PLY_TARGET = get("LOCAL_PLY_TARGET")
ROMI_CONFIG = get("ROMI_CONFIG")