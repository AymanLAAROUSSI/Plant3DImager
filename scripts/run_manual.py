#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script pour exécuter le contrôle manuel du robot
"""

import os
import sys
import argparse

# Ajouter le répertoire parent au chemin de recherche Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from manual_control.manual_controller import ManualController
from core.utils import config

def parse_arguments():
    """Parse les arguments de la ligne de commande"""
    parser = argparse.ArgumentParser(description="Contrôle manuel du robot")
    
    parser.add_argument("--arduino-port", "-a", type=str, default=config.ARDUINO_PORT,
                      help=f"Port Arduino (défaut: {config.ARDUINO_PORT})")
    
    parser.add_argument("--speed", "-s", type=float, default=config.CNC_SPEED,
                      help=f"Vitesse de déplacement de la CNC en m/s (défaut: {config.CNC_SPEED})")
    
    return parser.parse_args()

def main():
    """Fonction principale"""
    print("=== Contrôle manuel du robot ===")
    
    # Parser les arguments
    args = parse_arguments()
    
    # Créer et exécuter le contrôleur manuel
    controller = ManualController(args)
    success = controller.run_manual_control()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())