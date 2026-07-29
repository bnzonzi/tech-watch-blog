#!/usr/bin/env python3
"""
Script de régénération rapide de l'index.html du blog
Utilisé après ajout manuel d'articles ou crash du feeder
"""
import sys
import os
from pathlib import Path

# Ajouter le répertoire src au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent / "src"))

from blog_engine import BlogEngine

def main():
    """Régénère l'index.html du blog"""
    print("🔄 Régénération index.html du blog AgentBnZo...")

    engine = BlogEngine()

    # Parser les articles existants
    posts = engine.parse_posts()
    print(f"✅ {len(posts)} articles trouvés")

    # Générer le site (index + pages)
    result = engine.generate_site(posts)

    print(f"✅ Index régénéré : {result.get('index_path')}")
    print(f"📊 Stats: {result.get('stats')}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
