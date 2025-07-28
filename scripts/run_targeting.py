#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script pour exécuter le ciblage de feuilles
"""

import os
import sys
import argparse

# Ajouter le répertoire parent au chemin de recherche Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importer la classe LeafTargeting refactorisée
from targeting.leaf_targeting import LeafTargeting, parse_arguments

def main():
    """Fonction principale"""
    print("=== Système de ciblage de feuilles ===")
    
    # Parser les arguments
    args = parse_arguments()
    
    # Créer et exécuter le ciblage
    targeting = LeafTargeting(args)
    success = targeting.run_targeting()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())