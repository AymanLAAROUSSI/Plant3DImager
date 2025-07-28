#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Point d'entrée principal pour le système robotique de photographie et ciblage
"""

import os
import sys
import argparse

def parse_arguments():
    """Parse les arguments de la ligne de commande"""
    parser = argparse.ArgumentParser(description="Système robotique de photographie et ciblage")
    
    parser.add_argument("--mode", choices=["acquisition", "targeting"], required=True,
                      help="Mode d'exécution: acquisition d'images ou ciblage de feuilles")
    
    parser.add_argument("--args", nargs=argparse.REMAINDER,
                      help="Arguments à passer au script spécifique")
    
    return parser.parse_args()

def main():
    """Fonction principale"""
    print("=== Système Robotique de Photographie et Ciblage ===")
    
    # Parser les arguments
    args = parse_arguments()
    
    # Construire la commande à exécuter
    if args.mode == "acquisition":
        script_path = os.path.join("scripts", "run_acquisition.py")
    else:  # targeting
        script_path = os.path.join("scripts", "run_targeting.py")
    
    # Vérifier que le script existe
    if not os.path.exists(script_path):
        print(f"Erreur: Le script {script_path} n'existe pas.")
        return 1
    
    # Construire les arguments
    script_args = sys.argv[0:1] + ["--" + arg for arg in args.args] if args.args else []
    
    # Exécuter le script approprié
    cmd = [sys.executable, script_path] + script_args
    print(f"Exécution de: {' '.join(cmd)}")
    
    return os.system(" ".join(cmd)) >> 8  # Récupérer le code de retour

if __name__ == "__main__":
    sys.exit(main())