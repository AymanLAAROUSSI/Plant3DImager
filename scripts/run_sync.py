#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script pour exécuter la synchronisation serveur
"""

import os
import sys
import argparse

# Ajouter le répertoire parent au chemin de recherche Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sync.server_sync import ServerSync

def parse_arguments():
    """Parse les arguments de la ligne de commande"""
    parser = argparse.ArgumentParser(description="Synchronisation Raspberry Pi - Serveur")
    
    parser.add_argument("--ssh-host", type=str,
                      help="Adresse du serveur SSH")
    
    parser.add_argument("--ssh-user", type=str,
                      help="Nom d'utilisateur SSH")
    
    parser.add_argument("--key-path", type=str,
                      help="Chemin vers la clé SSH")
    
    parser.add_argument("--remote-path", type=str,
                      help="Chemin du répertoire de travail distant")
    
    parser.add_argument("--local-acq", type=str,
                      help="Répertoire d'acquisition local")
    
    parser.add_argument("--ply-target", type=str,
                      help="Répertoire cible pour les fichiers PLY")
    
    parser.add_argument("--dry-run", action="store_true",
                      help="Mode simulation (pas d'exécution réelle)")
    
    return parser.parse_args()

def main():
    """Fonction principale"""
    print("=== Synchronisation Raspberry Pi - Serveur ===")
    
    # Parser les arguments
    args = parse_arguments()
    
    # Créer et exécuter la synchronisation
    sync = ServerSync(args)
    success = sync.run_sync()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())