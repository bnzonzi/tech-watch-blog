#!/usr/bin/env python3
"""
Générateur d'index HTML pour le blog AgentBnZo
Met à jour l'index avec tous les articles + pagination
"""

import os
import json
from datetime import datetime
from pathlib import Path
import re

# Configuration
BLOG_DIR = Path("/media/raid10to/projets/blog")
OUTPUT_DIR = BLOG_DIR  # Pas de sous-répertoire output
POSTS_DIR = BLOG_DIR / "posts"
INDEX_FILE = BLOG_DIR / "output" / "index.html"

ARTICLES_PER_PAGE = 20

def extract_title_from_md(md_file):
    """Extrait le titre d'un fichier markdown"""
    try:
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Chercher le premier titre (# Titre)
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            return title_match.group(1).strip()

        # Fallback sur le nom du fichier
        return md_file.stem.replace('_', ' ').replace('-', ' ').title()

    except Exception:
        return md_file.stem.replace('_', ' ').replace('-', ' ').title()

def get_article_date(filename):
    """Extrait la date d'un nom de fichier"""

    # Format: article_YYYYMMDD_HHMMSS.md
    date_match = re.search(r'article_(\d{8})_(\d{6})\.md', filename)
    if date_match:
        date_str = date_match.group(1)
        time_str = date_match.group(2)
        try:
            return datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
        except:
            pass

    # Format: YYYY-MM-DD-*.html
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
    if date_match:
        try:
            return datetime.strptime(date_match.group(1), "%Y-%m-%d")
        except:
            pass

    # Fallback sur la date de modification du fichier
    try:
        file_path = POSTS_DIR / filename
        if file_path.exists():
            return datetime.fromtimestamp(file_path.stat().st_mtime)
    except:
        pass

    return datetime.now()

def get_all_articles():
    """Récupère tous les articles avec métadonnées"""

    articles = []

    # Articles markdown (.md)
    for md_file in POSTS_DIR.glob("*.md"):
        title = extract_title_from_md(md_file)
        date = get_article_date(md_file.name)

        articles.append({
            'title': title,
            'filename': md_file.name,
            'date': date,
            'type': 'md'
        })

    # Articles HTML (.html)
    for html_file in POSTS_DIR.glob("*.html"):
        if html_file.name == 'index.html':
            continue

        title = html_file.stem.replace('-', ' ').replace('_', ' ').title()
        date = get_article_date(html_file.name)

        articles.append({
            'title': title,
            'filename': html_file.name,
            'date': date,
            'type': 'html'
        })

    # Trier par date (plus récent en premier)
    articles.sort(key=lambda x: x['date'], reverse=True)

    return articles

def generate_article_preview(article):
    """Génère le HTML de prévisualisation d'un article"""

    date_str = article['date'].strftime("%Y-%m-%d")

    return f"""
        <article class="post-preview">
            <h2><a href="posts/{article['filename']}">{article['title']}</a></h2>
            <p class="meta">📅 {date_str} | 🔖 {article['type'].upper()}</p>
        </article>"""

def generate_pagination(current_page, total_pages):
    """Génère la pagination HTML"""

    if total_pages <= 1:
        return ""

    pagination = ['<div class="pagination">']

    # Page précédente
    if current_page > 1:
        prev_page = f"index_page_{current_page - 1}.html" if current_page > 2 else "index.html"
        pagination.append(f'<a href="{prev_page}">← Précédent</a>')

    # Numéros de pages
    for page in range(1, total_pages + 1):
        if page == current_page:
            pagination.append(f'<span class="current-page">{page}</span>')
        else:
            page_file = "index.html" if page == 1 else f"index_page_{page}.html"
            pagination.append(f'<a href="{page_file}">{page}</a>')

    # Page suivante
    if current_page < total_pages:
        next_page = f"index_page_{current_page + 1}.html"
        pagination.append(f'<a href="{next_page}">Suivant →</a>')

    pagination.append('</div>')

    return '\n'.join(pagination)

def generate_index_html(articles, page=1, total_pages=1):
    """Génère le HTML de l'index"""

    # Pagination des articles
    start_idx = (page - 1) * ARTICLES_PER_PAGE
    end_idx = start_idx + ARTICLES_PER_PAGE
    page_articles = articles[start_idx:end_idx]

    # Génération des aperçus d'articles
    articles_html = '\n'.join(generate_article_preview(article) for article in page_articles)

    # Génération pagination
    pagination_html = generate_pagination(page, total_pages)

    # Statistiques
    total_articles = len(articles)
    today_articles = len([a for a in articles if a['date'].date() == datetime.now().date()])

    # Template HTML complet
    html_content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Blog AgentBnZo - Techniques Multi-Agents{f" - Page {page}" if page > 1 else ""}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; background: #f8f9fa; }}
        .header {{ background: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .stats {{ display: flex; gap: 20px; margin: 20px 0; }}
        .stat {{ background: #0066cc; color: white; padding: 15px; border-radius: 5px; text-align: center; flex: 1; }}
        .posts {{ display: grid; gap: 20px; }}
        .post-preview {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        .post-preview h2 {{ margin: 0 0 10px 0; }}
        .post-preview a {{ text-decoration: none; color: #0066cc; }}
        .meta {{ color: #666; font-size: 0.9em; }}
        h1 {{ color: #0066cc; margin: 0; }}
        .subtitle {{ color: #666; margin: 10px 0; }}
        .pagination {{ text-align: center; margin: 30px 0; }}
        .pagination a, .pagination span {{ display: inline-block; padding: 8px 12px; margin: 0 4px; border: 1px solid #ddd; text-decoration: none; border-radius: 4px; }}
        .pagination a {{ color: #0066cc; }}
        .pagination a:hover {{ background: #f0f8ff; }}
        .pagination .current-page {{ background: #0066cc; color: white; }}
        .last-update {{ text-align: center; color: #666; font-size: 0.9em; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 Blog AgentBnZo</h1>
        <p class="subtitle">Techniques et pratiques pour l'écosystème multi-agents</p>
        <div class="stats">
            <div class="stat">
                <strong>{total_articles}</strong><br>Articles Total
            </div>
            <div class="stat">
                <strong>{today_articles}</strong><br>Aujourd'hui
            </div>
            <div class="stat">
                <strong>100%</strong><br>Gemini 2.5 Flash
            </div>
            <div class="stat">
                <strong>Auto</strong><br>Alimentation
            </div>
        </div>
    </div>

    <div class="posts">
        {articles_html}
    </div>

    {pagination_html}

    <div class="last-update">
        📅 Dernière mise à jour: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        | 📄 Page {page}/{total_pages}
        | 📊 {len(page_articles)} articles affichés
    </div>
</body>
</html>"""

    return html_content

def main():
    """Fonction principale"""

    print("🔄 GÉNÉRATION INDEX BLOG")
    print("=" * 40)

    # Récupérer tous les articles
    articles = get_all_articles()
    total_articles = len(articles)

    if total_articles == 0:
        print("❌ Aucun article trouvé")
        return

    print(f"📊 {total_articles} articles trouvés")

    # Calculer nombre de pages
    total_pages = (total_articles + ARTICLES_PER_PAGE - 1) // ARTICLES_PER_PAGE

    print(f"📄 {total_pages} pages à générer")

    # Générer toutes les pages
    for page in range(1, total_pages + 1):
        html_content = generate_index_html(articles, page, total_pages)

        # Nom du fichier
        if page == 1:
            output_file = INDEX_FILE
        else:
            output_file = OUTPUT_DIR / f"index_page_{page}.html"

        # Écrire le fichier
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"✅ {output_file.name} généré")

    print(f"🎉 Index mis à jour avec {total_articles} articles sur {total_pages} pages")

if __name__ == "__main__":
    main()