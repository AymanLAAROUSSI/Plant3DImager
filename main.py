#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Point d'entrée principal pour le système robotique de photographie et ciblage
"""

import os
import sys
import argparse
import subprocess

def main():
    """Fonction principale"""
    print("=== Système Robotique de Photographie et Ciblage ===")
    
    # Créer le parseur principal
    parser = argparse.ArgumentParser(description="Système robotique de photographie et ciblage")
    
    # Ajouter l'argument mode
    parser.add_argument("--mode", choices=["acquisition", "targeting", "manual", "sync"], required=True,
                      help="Mode d'exécution: acquisition d'images, ciblage de feuilles, contrôle manuel, ou synchronisation serveur")
    
    # Parser seulement l'argument mode
    args, remaining_args = parser.parse_known_args()
    
    # Construire le chemin du script
    script_paths = {
        "acquisition": os.path.join("scripts", "run_acquisition.py"),
        "targeting": os.path.join("scripts", "run_targeting.py"),
        "manual": os.path.join("scripts", "run_manual.py"),
        "sync": os.path.join("scripts", "run_sync.py")
    }
    
    script_path = script_paths[args.mode]
    
    # Vérifier que le script existe
    if not os.path.exists(script_path):
        print(f"Erreur: Le script {script_path} n'existe pas.")
        return 1
    
    # Construire la commande avec tous les arguments restants
    cmd = [sys.executable, script_path] + remaining_args
    print(f"Exécution de: {' '.join(cmd)}")
    
    # Utiliser subprocess pour une meilleure gestion des arguments
    return subprocess.call(cmd)

if __name__ == "__main__":
    sys.exit(main())