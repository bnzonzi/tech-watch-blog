#!/bin/bash
# Auto-push blog posts vers GitHub Pages (repo dédié bnzonzi/tech-watch-blog)
# IMPORTANT: ne jamais git add depuis le monorepo parent /media/raid10to/projets
set -euo pipefail

BLOG_DIR="/media/raid10to/projets/blog"
DEPLOY_DIR="${BLOG_DIR}/.pages-repo"
REMOTE="https://github.com/bnzonzi/tech-watch-blog.git"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M')

cd "$BLOG_DIR"

# Copier index.html de output/ vers racine si présent
if [ -f output/index.html ]; then
  cp output/index.html index.html
fi

# Clone persistant (une seule fois)
if [ ! -d "$DEPLOY_DIR/.git" ]; then
  rm -rf "$DEPLOY_DIR"
  git clone --depth 1 "$REMOTE" "$DEPLOY_DIR"
fi

# Sync fichiers publiables (exclure logs/metadata lourds/symlink crews)
rsync -a --delete \
  --exclude '.git/' \
  --exclude '.pages-repo/' \
  --exclude 'logs/' \
  --exclude 'metadata/' \
  --exclude '__pycache__/' \
  --exclude 'crews' \
  --exclude 'drafts/' \
  --exclude 'content/' \
  --exclude '*.log' \
  --exclude 'feeder_status.json' \
  --exclude 'feeder_api.log' \
  --exclude '.venv/' \
  --exclude 'chroma_db/' \
  --exclude 'rag_local_db/' \
  "$BLOG_DIR/" "$DEPLOY_DIR/"

cd "$DEPLOY_DIR"
git add -A
if git diff --cached --quiet; then
  echo "[$TIMESTAMP] Rien à pousser"
  exit 0
fi

git -c user.email="golem@agentbnzo.local" -c user.name="Golem" commit -q -m "auto: posts update $TIMESTAMP"
git push origin main 2>&1 | tail -5
echo "[$TIMESTAMP] Push OK"
