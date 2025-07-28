#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script pour exécuter l'acquisition d'images en cercle
"""

import os
import sys
import argparse

# Ajouter le répertoire parent au chemin de recherche Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from acquisition.circle_acquisition import CircleAcquisition
from core.utils import config

def parse_arguments():
    """Parse les arguments de la ligne de commande"""
    parser = argparse.ArgumentParser(description="Acquisition d'images en cercle")
    
    parser.add_argument("--circles", "-c", type=int, choices=[1, 2], default=1,
                      help=f"Nombre de cercles à photographier (1 ou 2, défaut: 1)")
    
    parser.add_argument("--positions", "-p", type=int, default=config.NUM_POSITIONS, 
                      help=f"Nombre de positions par cercle (défaut: {config.NUM_POSITIONS})")
    
    parser.add_argument("--radius", "-r", type=float, default=config.CIRCLE_RADIUS,
                      help=f"Rayon du cercle en mètres (défaut: {config.CIRCLE_RADIUS})")
    
    parser.add_argument("--z-offset", "-z", type=float, default=config.Z_OFFSET,
                      help=f"Décalage en Z entre les deux cercles en mètres (défaut: {config.Z_OFFSET})")
    
    parser.add_argument("--arduino-port", "-a", type=str, default=config.ARDUINO_PORT,
                      help=f"Port Arduino (défaut: {config.ARDUINO_PORT})")
    
    parser.add_argument("--speed", "-s", type=float, default=config.CNC_SPEED,
                      help=f"Vitesse de déplacement de la CNC en m/s (défaut: {config.CNC_SPEED})")
    
    return parser.parse_args()

def main():
    """Fonction principale"""
    print("=== Acquisition d'images en cercle ===")
    
    # Parser les arguments
    args = parse_arguments()
    
    # Créer et exécuter l'acquisition
    acquisition = CircleAcquisition(args)
    success = acquisition.run_acquisition()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())