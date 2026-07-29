#!/bin/bash
"""
Script d'automatisation pour mise à jour patterns Fabric
À exécuter via cron pour maintenir les patterns à jour
"""

set -e

# Variables
FABRIC_DIR="/media/Infereur/fabric"
BLOG_DIR="/media/raid10to/projets/blog"
LOG_FILE="$BLOG_DIR/logs/fabric_update.log"
PYENV_FABRIC="fabric"

# Fonction de logging
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Fonction de notification
notify_telegram() {
    local message="$1"
    local status="$2"  # success, warning, error

    local emoji="📦"
    case $status in
        "success") emoji="✅" ;;
        "warning") emoji="⚠️" ;;
        "error") emoji="❌" ;;
    esac

    # Ici on pourrait ajouter une notification Telegram
    log "$emoji $message"
}

# Créer le répertoire de logs si nécessaire
mkdir -p "$BLOG_DIR/logs"

log "🚀 Démarrage mise à jour patterns Fabric"

# Vérifier que Fabric est disponible
if ! command -v pyenv &> /dev/null; then
    notify_telegram "PyEnv non trouvé" "error"
    exit 1
fi

# Aller dans le répertoire Fabric
cd "$FABRIC_DIR" || {
    notify_telegram "Répertoire Fabric non trouvé: $FABRIC_DIR" "error"
    exit 1
}

# Sauvegarder l'état actuel
log "📦 Sauvegarde état actuel..."
BACKUP_DIR="/tmp/fabric_backup_$(date +%Y%m%d_%H%M%S)"
cp -r "$FABRIC_DIR" "$BACKUP_DIR"
log "✅ Sauvegarde créée: $BACKUP_DIR"

# Mise à jour Git
log "📡 Mise à jour repository Git..."
git fetch origin

# Vérifier s'il y a des mises à jour
CURRENT_COMMIT=$(git rev-parse HEAD)
REMOTE_COMMIT=$(git rev-parse origin/main)

if [ "$CURRENT_COMMIT" = "$REMOTE_COMMIT" ]; then
    log "✅ Patterns déjà à jour (commit: ${CURRENT_COMMIT:0:8})"
    rm -rf "$BACKUP_DIR"
    exit 0
fi

log "🔄 Nouvelles mises à jour disponibles"
log "   Local:  ${CURRENT_COMMIT:0:8}"
log "   Remote: ${REMOTE_COMMIT:0:8}"

# Résoudre les conflits automatiquement
log "🔧 Résolution des conflits..."
git reset --hard origin/main

# Vérifier le statut après mise à jour
NEW_COMMIT=$(git rev-parse HEAD)
log "✅ Mise à jour Git terminée (nouveau commit: ${NEW_COMMIT:0:8})"

# Mettre à jour les patterns via Fabric
log "🧵 Mise à jour patterns Fabric..."
eval "$(pyenv init -)"
pyenv activate "$PYENV_FABRIC"

# Tester Fabric
if fabric --list > /dev/null 2>&1; then
    log "✅ Fabric opérationnel"
else
    log "⚠️ Problème avec Fabric, utilisation des patterns Git seulement"
fi

# Compter les patterns disponibles
PATTERN_COUNT=$(find "$FABRIC_DIR/data/patterns" -maxdepth 1 -type d | wc -l)
log "📊 Patterns disponibles: $PATTERN_COUNT"

# Vérifier les nouveaux patterns
log "🔍 Analyse des nouveaux patterns..."
ADDED_PATTERNS=$(git log --name-only --pretty=format: $CURRENT_COMMIT..$NEW_COMMIT | grep "data/patterns/" | grep "system.md" | wc -l)

if [ "$ADDED_PATTERNS" -gt 0 ]; then
    log "🆕 $ADDED_PATTERNS nouveaux patterns détectés"
    git log --oneline $CURRENT_COMMIT..$NEW_COMMIT | head -10 | while read line; do
        log "   📝 $line"
    done
else
    log "📄 Aucun nouveau pattern, mises à jour existants"
fi

# Test de validation
log "🧪 Test de validation..."
TEST_PATTERN="summarize"
echo "Test Fabric pattern" | timeout 30 fabric --pattern "$TEST_PATTERN" > /dev/null 2>&1 && {
    log "✅ Test validation réussi"
} || {
    log "⚠️ Test validation échoué, rollback..."
    cd "$BACKUP_DIR"
    cp -r . "$FABRIC_DIR/"
    notify_telegram "Rollback effectué suite à échec validation" "warning"
    exit 1
}

# Nettoyage
rm -rf "$BACKUP_DIR"

# Notification finale
notify_telegram "Patterns Fabric mis à jour avec succès ($PATTERN_COUNT patterns)" "success"

log "🎉 Mise à jour patterns Fabric terminée avec succès"

# Optionnel: Redémarrer le blog feeder pour prendre en compte les nouveaux patterns
if pgrep -f "enhanced_blog_feeder.py" > /dev/null; then
    log "🔄 Redémarrage blog feeder pour nouveaux patterns..."
    # Ici on pourrait ajouter un signal de rechargement propre
    log "💡 Patterns seront pris en compte au prochain article"
fi

exit 0