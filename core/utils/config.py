#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Configuration globale partagée entre les modules d'acquisition et de ciblage
"""

# Point cible à regarder (en mètres)
TARGET_POINT = (0.375, 0.35, 0.30)

# Point central du cercle (en mètres)
CENTER_POINT = (0.375, 0.35, 0.00)

# Rayon du cercle (en mètres)
CIRCLE_RADIUS = 0.30

# Nombre de positions sur le cercle par défaut
NUM_POSITIONS = 80

# Décalage en Z entre les deux cercles (en mètres)
Z_OFFSET = 0.20  # 20 centimètres

# Port Arduino par défaut
ARDUINO_PORT = "/dev/ttyACM0"

# Vitesse par défaut de déplacement de la CNC (en m/s)
CNC_SPEED = 0.1

# Intervalle de mise à jour de la caméra pendant le mouvement (en secondes)
UPDATE_INTERVAL = 0.1

# Temps de stabilisation avant la prise de photo (en secondes)
STABILIZATION_TIME = 3.0

# Dossiers par défaut
RESULTS_DIR = "results"  # Nouveau répertoire parent pour tous les résultats
ACQUISITION_DIR = "plant_acquisition"  # Renommé de aa_photos_reconstructions
TARGETING_DIR = "leaf_targeting"  # Inchangé mais plus cohérent

# Configuration de la synchronisation
SSH_HOST = "10.0.7.22"
SSH_USER = "ayman"
KEY_PATH = "/home/romi/.ssh/id_rsa"
REMOTE_WORK_PATH = "/mnt/diskSustainability/Scanner_Data/scanner_lyon/3dt_colA/Col_A_2021-01-29/"
LOCAL_ACQUISITION_BASE = "results/plant_acquisition"  # Relatif au répertoire du projet
LOCAL_PLY_TARGET = "results/pointclouds"  # Relatif au répertoire du projet
ROMI_CONFIG = "~/plant-3d-vision/configs/geom_pipe_real.toml"