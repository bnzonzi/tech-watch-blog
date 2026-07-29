#!/bin/bash
# Auto-push blog posts vers GitHub Pages (autonomie)
# Lancé par cron après intelligent_blog_feeder + generate_index
set -e
cd /media/raid10to/projets/blog
TIMESTAMP=$(date '+%Y-%m-%d %H:%M')

# Copier index.html de output/ vers racine (GitHub Pages sert la racine)
if [ -f output/index.html ]; then
  cp output/index.html index.html
fi

git add -A 2>/dev/null
if git diff --cached --quiet; then
  echo "[$TIMESTAMP] Rien à pousser"
  exit 0
fi
git -c user.email="golem@agentbnzo.local" -c user.name="Golem" commit -q -m "auto: posts update $TIMESTAMP"
git push origin main 2>&1 | tail -3
echo "[$TIMESTAMP] Push OK"
