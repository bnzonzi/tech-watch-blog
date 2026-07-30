#!/usr/bin/env python3
"""
Générateur d'index HTML pour le blog AgentBnZo
Met à jour l'index avec tous les articles + pagination (template P0 partagé)
"""

import re
import sys
from datetime import datetime
from pathlib import Path

BLOG_DIR = Path("/media/raid10to/projets/blog")
POSTS_DIR = BLOG_DIR / "posts"
OUTPUT_DIR = BLOG_DIR
OUTPUT_LEGACY = BLOG_DIR / "output"
SRC_DIR = BLOG_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
from blog_template import render_index_page

ARTICLES_PER_PAGE = 20


def extract_title_from_md(md_file):
    """Extrait le titre d'un fichier markdown"""
    try:
        with open(md_file, "r", encoding="utf-8") as f:
            content = f.read()
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if title_match:
            return title_match.group(1).strip()
        return md_file.stem.replace("_", " ").replace("-", " ").title()
    except Exception:
        return md_file.stem.replace("_", " ").replace("-", " ").title()


def get_article_date(filename):
    """Extrait la date d'un nom de fichier"""
    date_match = re.search(r"article_(\d{8})_(\d{6})\.md", filename)
    if date_match:
        date_str = date_match.group(1)
        time_str = date_match.group(2)
        try:
            return datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
        except Exception:
            pass

    # Format: YYYY-MM-DD-*.html
    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", filename)
    if date_match:
        try:
            return datetime.strptime(date_match.group(1), "%Y-%m-%d")
        except Exception:
            pass

    return datetime.now()


def extract_title_from_html(html_file: Path) -> str:
    try:
        text = html_file.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"<h1[^>]*>(.*?)</h1>", text, re.IGNORECASE | re.DOTALL)
        if m:
            title = re.sub(r"<[^>]+>", "", m.group(1)).strip()
            if title:
                return title
        m = re.search(r"<title>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
        if m:
            title = re.sub(r"\s*·\s*AgentBnZo.*$", "", m.group(1)).strip()
            if title:
                return title
    except Exception:
        pass
    return html_file.stem.replace("-", " ").replace("_", " ").title()


def extract_category_from_html(html_file: Path) -> str:
    try:
        text = html_file.read_text(encoding="utf-8", errors="replace")
        m = re.search(r'name="category"\s+content="([^"]+)"', text, re.IGNORECASE)
        if m:
            return m.group(1)
        m = re.search(r'class="badge"[^>]*>([^<]+)', text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    except Exception:
        pass
    return "html"


def get_all_articles():
    """Récupère tous les articles du blog"""
    articles = []

    for md_file in POSTS_DIR.glob("*.md"):
        articles.append(
            {
                "title": extract_title_from_md(md_file),
                "filename": md_file.name,
                "date": get_article_date(md_file.name),
                "type": "md",
                "category": "markdown",
            }
        )

    for html_file in POSTS_DIR.glob("*.html"):
        if html_file.name == "index.html":
            continue
        articles.append(
            {
                "title": extract_title_from_html(html_file),
                "filename": html_file.name,
                "date": get_article_date(html_file.name),
                "type": "html",
                "category": extract_category_from_html(html_file),
            }
        )

    articles.sort(key=lambda x: x["date"], reverse=True)
    return articles


def generate_article_preview(article):
    """Génère le HTML de prévisualisation d'un article"""
    date_str = article["date"].strftime("%Y-%m-%d")
    category = article.get("category") or article.get("type", "post")
    return f"""
        <article class="post-preview">
            <span class="badge">{category}</span>
            <h2><a href="posts/{article['filename']}">{article['title']}</a></h2>
            <p class="meta">{date_str} · {article['type'].upper()}</p>
        </article>"""


def generate_pagination(current_page, total_pages):
    """Génère la pagination HTML"""
    if total_pages <= 1:
        return ""

    pagination = ['<nav class="pagination" aria-label="Pagination">']

    if current_page > 1:
        prev_page = f"index_page_{current_page - 1}.html" if current_page > 2 else "index.html"
        pagination.append(f'<a href="{prev_page}" rel="prev">← Précédent</a>')

    for page in range(1, total_pages + 1):
        if page == current_page:
            pagination.append(f'<span class="current-page" aria-current="page">{page}</span>')
        else:
            page_file = "index.html" if page == 1 else f"index_page_{page}.html"
            pagination.append(f'<a href="{page_file}">{page}</a>')

    if current_page < total_pages:
        next_page = f"index_page_{current_page + 1}.html"
        pagination.append(f'<a href="{next_page}" rel="next">Suivant →</a>')

    pagination.append("</nav>")
    return "\n".join(pagination)


def generate_index_html(articles, page=1, total_pages=1):
    """Génère le HTML de l'index"""
    start_idx = (page - 1) * ARTICLES_PER_PAGE
    end_idx = start_idx + ARTICLES_PER_PAGE
    page_articles = articles[start_idx:end_idx]
    articles_html = "\n".join(generate_article_preview(article) for article in page_articles)
    pagination_html = generate_pagination(page, total_pages)
    total_articles = len(articles)
    today_articles = len([a for a in articles if a["date"].date() == datetime.now().date()])

    return render_index_page(
        articles_html=articles_html,
        pagination_html=pagination_html,
        total_articles=total_articles,
        today_articles=today_articles,
        page=page,
        total_pages=total_pages,
        page_articles_count=len(page_articles),
        updated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )


def main():
    print("🔄 GÉNÉRATION INDEX BLOG (template P0)")
    print("=" * 40)

    articles = get_all_articles()
    total_articles = len(articles)
    if total_articles == 0:
        print("❌ Aucun article trouvé")
        return

    print(f"📊 {total_articles} articles trouvés")
    total_pages = (total_articles + ARTICLES_PER_PAGE - 1) // ARTICLES_PER_PAGE
    print(f"📄 {total_pages} pages à générer")

    OUTPUT_DIR.mkdir(exist_ok=True)
    OUTPUT_LEGACY.mkdir(exist_ok=True)

    for page in range(1, total_pages + 1):
        html_content = generate_index_html(articles, page, total_pages)
        if page == 1:
            output_file = OUTPUT_DIR / "index.html"
            legacy_file = OUTPUT_LEGACY / "index.html"
        else:
            output_file = OUTPUT_DIR / f"index_page_{page}.html"
            legacy_file = None

        output_file.write_text(html_content, encoding="utf-8")
        print(f"✅ {output_file.name} généré")
        if legacy_file is not None:
            legacy_file.write_text(html_content, encoding="utf-8")

    print(f"🎉 Index mis à jour avec {total_articles} articles sur {total_pages} pages")


if __name__ == "__main__":
    main()
