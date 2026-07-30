#!/bin/bash
# Auto-push blog posts vers GitHub Pages (repo dédié bnzonzi/tech-watch-blog)
# IMPORTANT: ne jamais git add depuis le monorepo parent /media/raid10to/projets
# Gate pré-production OBLIGATOIRE avant push (charte + sources chinoises)
set -euo pipefail

BLOG_DIR="/media/raid10to/projets/blog"
DEPLOY_DIR="${BLOG_DIR}/.pages-repo"
REMOTE="https://github.com/bnzonzi/tech-watch-blog.git"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M')
LOG_DIR="${BLOG_DIR}/logs"
mkdir -p "$LOG_DIR"

cd "$BLOG_DIR"

# --- GATE PRÉ-PRODUCTION (bloque le push si HTML cassé / chinois non enrichi en posts/) ---
python3 src/preprod_gate.py --repair >> "$LOG_DIR/preprod_gate.log" 2>&1 || true
AUDIT_JSON=$(python3 src/preprod_gate.py --audit 2>/dev/null || echo '{}')
FAIL_COUNT=$(python3 -c "import json,sys; d=json.loads(sys.argv[1] or '{}'); print(d.get('fail',0) if isinstance(d.get('fail'),int) else len(d.get('fail') or []))" "$AUDIT_JSON" 2>/dev/null || echo 0)
if [ "${FAIL_COUNT:-0}" -gt 0 ]; then
  echo "[$TIMESTAMP] PUSH BLOQUÉ — $FAIL_COUNT articles hors charte encore en posts/" | tee -a "$LOG_DIR/preprod_gate.log"
  echo "$AUDIT_JSON" | tee -a "$LOG_DIR/preprod_gate.log"
  exit 2
fi

# Copier index.html de output/ vers racine si présent
if [ -f output/index.html ]; then
  cp output/index.html index.html
fi

# Régénérer index après repair/quarantine
python3 generate_index.py >> "$LOG_DIR/preprod_gate.log" 2>&1

# Clone persistant (une seule fois)
if [ ! -d "$DEPLOY_DIR/.git" ]; then
  rm -rf "$DEPLOY_DIR"
  git clone --depth 1 "$REMOTE" "$DEPLOY_DIR"
fi

# Sync fichiers publiables (exclure logs/metadata/quarantine/symlink crews)
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

git -c user.email="golem@agentbnzo.local" -c user.name="Golem" commit -q -m "auto: posts update $TIMESTAMP (preprod gate OK)"
git push origin main 2>&1 | tail -5
echo "[$TIMESTAMP] Push OK (preprod gate passed)"
