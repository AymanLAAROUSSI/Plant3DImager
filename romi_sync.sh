#!/bin/bash
# Script de synchronisation Raspberry Pi - Serveur
# Ce script utilise une approche shell simple pour reproduire
# exactement ce que vous feriez manuellement.

# Configuration
SSH_HOST="10.0.7.22"
SSH_USER="ayman"
SSH_KEY="/home/romi/.ssh/id_rsa"
REMOTE_BASE="/mnt/diskSustainability/Scanner_Data/scanner_lyon/3dt_colA/Col_A_2021-01-29"
LOCAL_BASE="/home/romi/ayman/results/plant_acquisition"
LOCAL_PLY_TARGET="/home/romi/ayman/PointClouds"

# Fonctions utilitaires
log() {
  echo "$(date +'%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
  echo "$(date +'%Y-%m-%d %H:%M:%S') - ❌ $1" >&2
}

# 1. Trouver le dossier circular_scan_* le plus récent
log "Recherche du dossier d'acquisition le plus récent..."
LATEST_DIR=$(find "$LOCAL_BASE" -maxdepth 1 -type d -name "circular_scan_*" | sort -r | head -n1)

if [ -z "$LATEST_DIR" ]; then
  log_error "Aucun dossier circular_scan trouvé dans $LOCAL_BASE"
  exit 1
fi

TIMESTAMP=$(basename "$LATEST_DIR" | sed 's/circular_scan_//')
log "✅ Dernier dossier trouvé: $(basename "$LATEST_DIR")"

# 2. Lancer la task Clean
log "Étape 1: Lancement de la tâche Clean..."
ssh -i "$SSH_KEY" "$SSH_USER@$SSH_HOST" "romi_run_task Clean $REMOTE_BASE --config ~/plant-3d-vision/configs/geom_pipe_real.toml"

if [ $? -ne 0 ]; then
  log_error "Échec de la tâche Clean"
  exit 1
fi

# 3. Supprimer anciens fichiers
log "Étape 2: Suppression des anciens fichiers..."
ssh -i "$SSH_KEY" "$SSH_USER@$SSH_HOST" "rm -rf $REMOTE_BASE/images $REMOTE_BASE/metadata $REMOTE_BASE/files.json $REMOTE_BASE/scan.toml"

if [ $? -ne 0 ]; then
  log_error "Échec de la suppression des anciens fichiers"
  exit 1
fi

# 4. Copier les fichiers/dossiers vers le serveur
log "Étape 3: Transfert des données vers le serveur..."
for ITEM in "images" "metadata" "files.json" "scan.toml"; do
  SRC="$LATEST_DIR/$ITEM"
  DST="$REMOTE_BASE/$ITEM"
  
  if [ ! -e "$SRC" ]; then
    log "⚠️ Item manquant, ignoré: $SRC"
    continue
  fi
  
  # Créer le répertoire parent distant si nécessaire pour les dossiers
  if [ -d "$SRC" ]; then
    ssh -i "$SSH_KEY" "$SSH_USER@$SSH_HOST" "mkdir -p $DST"
    scp -i "$SSH_KEY" -r "$SRC" "$SSH_USER@$SSH_HOST:$REMOTE_BASE/"
  else
    scp -i "$SSH_KEY" "$SRC" "$SSH_USER@$SSH_HOST:$DST"
  fi
  
  if [ $? -ne 0 ]; then
    log_error "Échec de la copie de $SRC"
    exit 1
  fi
done

# 5. Lancer la task PointCloud
log "Étape 4: Génération du nuage de points..."
ssh -i "$SSH_KEY" "$SSH_USER@$SSH_HOST" "romi_run_task PointCloud $REMOTE_BASE --config ~/plant-3d-vision/configs/geom_pipe_real.toml"

if [ $? -ne 0 ]; then
  log_error "Échec de la tâche PointCloud"
  exit 1
fi

# 6. Récupérer le bon dossier PointCloud*
log "Étape 5: Récupération du nuage de points..."
POINTCLOUD_DIR=$(ssh -i "$SSH_KEY" "$SSH_USER@$SSH_HOST" "ls -td $REMOTE_BASE/PointCloud*/ | head -n1")

if [ -z "$POINTCLOUD_DIR" ]; then
  log_error "Impossible de trouver le répertoire PointCloud"
  exit 1
fi

POINTCLOUD_FILE="$POINTCLOUD_DIR/PointCloud.ply"
LOCAL_PLY_PATH="$LOCAL_PLY_TARGET/PointCloud_$TIMESTAMP.ply"

# Créer le répertoire local si nécessaire
mkdir -p "$LOCAL_PLY_TARGET"

# Télécharger le fichier PLY
scp -i "$SSH_KEY" "$SSH_USER@$SSH_HOST:$POINTCLOUD_FILE" "$LOCAL_PLY_PATH"

if [ $? -ne 0 ]; then
  log_error "Échec du téléchargement du fichier PLY"
  exit 1
fi

log "✅ Fichier récupéré: $LOCAL_PLY_PATH"
log "✅ Synchronisation terminée avec succès"
