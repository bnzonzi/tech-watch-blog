#!/usr/bin/env python3
"""
Moteur de génération de blog statique
Site responsive moderne pour consultation via file:// et http://localhost
"""

import os
import sys
import json
import logging
import shutil
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import yaml
import re
from jinja2 import Environment, FileSystemLoader, select_autoescape
import markdown
from markdown.extensions import codehilite, toc, meta

# Configuration locale
sys.path.append(str(Path(__file__).parent.parent))
from config.blog_config import (
    BLOG_ROOT, CONTENT_DIR, TEMPLATES_DIR, STATIC_DIR, OUTPUT_DIR,
    BLOG_CONFIG, BLOG_CATEGORIES
)

@dataclass
class BlogPost:
    """Article de blog parsé"""
    title: str
    content: str
    html_content: str
    metadata: Dict[str, Any]
    filename: str
    date: datetime
    category: str
    tags: List[str]
    reading_time: str
    url_slug: str

@dataclass
class BlogStats:
    """Statistiques du blog"""
    total_posts: int
    categories_count: Dict[str, int]
    tags_count: Dict[str, int]
    latest_posts: List[BlogPost]
    popular_categories: List[str]

class BlogEngine:
    """
    Générateur de site statique moderne et responsive
    Compatible file:// et serveur local
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._setup_directories()
        self._setup_jinja()
        self._setup_markdown()

    def _setup_directories(self):
        """Initialise les répertoires nécessaires"""
        for directory in [CONTENT_DIR, TEMPLATES_DIR, STATIC_DIR, OUTPUT_DIR]:
            directory.mkdir(parents=True, exist_ok=True)

        # Sous-répertoires output
        for subdir in ['css', 'js', 'img', 'posts', 'categories']:
            (OUTPUT_DIR / subdir).mkdir(exist_ok=True)

    def _setup_jinja(self):
        """Configure Jinja2 pour les templates"""
        self.jinja_env = Environment(
            loader=FileSystemLoader(TEMPLATES_DIR),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )

        # Filtres personnalisés
        self.jinja_env.filters['dateformat'] = self._format_date
        self.jinja_env.filters['truncate_words'] = self._truncate_words
        self.jinja_env.filters['url_slug'] = self._create_url_slug

    def _setup_markdown(self):
        """Configure le processeur Markdown"""
        self.markdown_processor = markdown.Markdown(
            extensions=[
                'meta',
                'toc',
                'codehilite',
                'fenced_code',
                'tables',
                'abbr',
                'attr_list'
            ],
            extension_configs={
                'codehilite': {
                    'css_class': 'highlight',
                    'use_pygments': True
                },
                'toc': {
                    'permalink': True,
                    'title': 'Table des matières'
                }
            }
        )

    def parse_posts(self) -> List[BlogPost]:
        """Parse tous les articles du répertoire content"""
        posts = []
        articles_dir = CONTENT_DIR / "articles"

        if not articles_dir.exists():
            self.logger.warning(f"Répertoire articles non trouvé: {articles_dir}")
            return posts

        for md_file in articles_dir.glob("*.md"):
            try:
                post = self._parse_single_post(md_file)
                if post:
                    posts.append(post)
            except Exception as e:
                self.logger.error(f"Erreur parsing {md_file}: {e}")

        # Trier par date (plus récent en premier)
        posts.sort(key=lambda x: x.date, reverse=True)

        self.logger.info(f"Articles parsés: {len(posts)}")
        return posts

    def _parse_single_post(self, md_file: Path) -> Optional[BlogPost]:
        """Parse un fichier Markdown en BlogPost"""
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Reset markdown processor
        self.markdown_processor.reset()

        # Traiter le contenu
        html_content = self.markdown_processor.convert(content)
        metadata = self.markdown_processor.Meta or {}

        # Extraire métadonnées
        title = self._get_meta_value(metadata, 'title', md_file.stem)
        date_str = self._get_meta_value(metadata, 'date', '')
        category = self._get_meta_value(metadata, 'categories', 'general')
        tags = self._get_meta_list(metadata, 'tags')
        reading_time = self._get_meta_value(metadata, 'reading_time', '5 min')

        # Convertir date
        try:
            if isinstance(date_str, list):
                date_str = date_str[0] if date_str else ''
            post_date = datetime.fromisoformat(date_str.replace(' ', 'T')) if date_str else datetime.now()
        except:
            post_date = datetime.now()

        # Nettoyer catégorie
        if isinstance(category, list):
            category = category[0] if category else 'general'

        return BlogPost(
            title=title,
            content=content,
            html_content=html_content,
            metadata=dict(metadata),
            filename=md_file.name,
            date=post_date,
            category=category,
            tags=tags,
            reading_time=reading_time,
            url_slug=self._create_url_slug(title)
        )

    def _get_meta_value(self, metadata: Dict, key: str, default: str = '') -> str:
        """Récupère une valeur de métadonnée"""
        value = metadata.get(key, default)
        if isinstance(value, list):
            return value[0] if value else default
        return str(value)

    def _get_meta_list(self, metadata: Dict, key: str) -> List[str]:
        """Récupère une liste de métadonnées"""
        value = metadata.get(key, [])
        if isinstance(value, str):
            return [value]
        return list(value) if value else []

    def generate_site(self, posts: List[BlogPost]) -> Dict[str, Any]:
        """Génère le site statique complet"""
        self.logger.info("Génération du site statique...")

        # Calculer statistiques
        stats = self._calculate_stats(posts)

        # Générer pages
        results = {
            'index': self._generate_index_page(posts, stats),
            'posts': self._generate_post_pages(posts),
            'categories': self._generate_category_pages(posts),
            'assets': self._copy_static_assets(),
            'stats': stats
        }

        self.logger.info("Site statique généré avec succès")
        return results

    def _calculate_stats(self, posts: List[BlogPost]) -> BlogStats:
        """Calcule les statistiques du blog"""
        categories_count = {}
        tags_count = {}

        for post in posts:
            # Compter catégories
            categories_count[post.category] = categories_count.get(post.category, 0) + 1

            # Compter tags
            for tag in post.tags:
                tags_count[tag] = tags_count.get(tag, 0) + 1

        # Catégories populaires
        popular_categories = sorted(
            categories_count.keys(),
            key=lambda x: categories_count[x],
            reverse=True
        )[:5]

        return BlogStats(
            total_posts=len(posts),
            categories_count=categories_count,
            tags_count=tags_count,
            latest_posts=posts[:5],
            popular_categories=popular_categories
        )

    def _generate_index_page(self, posts: List[BlogPost], stats: BlogStats) -> Path:
        """Génère la page d'accueil"""
        template = self.jinja_env.get_template('index.html')

        html_content = template.render(
            config=BLOG_CONFIG,
            posts=posts[:10],  # 10 derniers articles
            stats=stats,
            categories=BLOG_CATEGORIES,
            featured_posts=posts[:3],  # Articles en vedette
            recent_posts=posts[:5]
        )

        output_path = OUTPUT_DIR / 'index.html'
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        self.logger.info(f"Page d'accueil générée: {output_path}")
        return output_path

    def _generate_post_pages(self, posts: List[BlogPost]) -> List[Path]:
        """Génère les pages individuelles des articles"""
        template = self.jinja_env.get_template('post.html')
        generated_paths = []

        posts_dir = OUTPUT_DIR / 'posts'
        posts_dir.mkdir(exist_ok=True)

        for i, post in enumerate(posts):
            # Articles précédent/suivant
            prev_post = posts[i + 1] if i + 1 < len(posts) else None
            next_post = posts[i - 1] if i > 0 else None

            html_content = template.render(
                config=BLOG_CONFIG,
                post=post,
                prev_post=prev_post,
                next_post=next_post,
                categories=BLOG_CATEGORIES
            )

            output_path = posts_dir / f"{post.url_slug}.html"
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            generated_paths.append(output_path)

        self.logger.info(f"Pages articles générées: {len(generated_paths)}")
        return generated_paths

    def _generate_category_pages(self, posts: List[BlogPost]) -> List[Path]:
        """Génère les pages par catégorie"""
        template = self.jinja_env.get_template('category.html')
        generated_paths = []

        categories_dir = OUTPUT_DIR / 'categories'
        categories_dir.mkdir(exist_ok=True)

        # Grouper par catégorie
        posts_by_category = {}
        for post in posts:
            if post.category not in posts_by_category:
                posts_by_category[post.category] = []
            posts_by_category[post.category].append(post)

        # Générer une page par catégorie
        for category, category_posts in posts_by_category.items():
            category_config = BLOG_CATEGORIES.get(category, {
                'name': category.title(),
                'description': f'Articles dans la catégorie {category}'
            })

            html_content = template.render(
                config=BLOG_CONFIG,
                category=category,
                category_config=category_config,
                posts=category_posts,
                total_posts=len(category_posts),
                categories=BLOG_CATEGORIES
            )

            output_path = categories_dir / f"{category}.html"
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            generated_paths.append(output_path)

        self.logger.info(f"Pages catégories générées: {len(generated_paths)}")
        return generated_paths

    def _copy_static_assets(self) -> Dict[str, Path]:
        """Copie les assets statiques (CSS, JS, images)"""
        assets_paths = {}

        # CSS
        css_source = STATIC_DIR / 'css'
        css_dest = OUTPUT_DIR / 'css'
        if css_source.exists():
            shutil.copytree(css_source, css_dest, dirs_exist_ok=True)
            assets_paths['css'] = css_dest

        # JavaScript
        js_source = STATIC_DIR / 'js'
        js_dest = OUTPUT_DIR / 'js'
        if js_source.exists():
            shutil.copytree(js_source, js_dest, dirs_exist_ok=True)
            assets_paths['js'] = js_dest

        # Images
        img_source = STATIC_DIR / 'img'
        img_dest = OUTPUT_DIR / 'img'
        if img_source.exists():
            shutil.copytree(img_source, img_dest, dirs_exist_ok=True)
            assets_paths['img'] = img_dest

        # Générer CSS par défaut si inexistant
        if not (OUTPUT_DIR / 'css' / 'style.css').exists():
            self._generate_default_css()
            assets_paths['css'] = OUTPUT_DIR / 'css'

        # Générer JS par défaut si inexistant
        if not (OUTPUT_DIR / 'js' / 'main.js').exists():
            self._generate_default_js()
            assets_paths['js'] = OUTPUT_DIR / 'js'

        return assets_paths

    def _generate_default_css(self):
        """Génère un CSS par défaut moderne et responsive"""
        css_content = '''/* AgentBnZo Blog - CSS moderne et responsive */

:root {
    --primary-color: #2563eb;
    --secondary-color: #64748b;
    --accent-color: #f59e0b;
    --bg-color: #ffffff;
    --text-color: #1f2937;
    --border-color: #e5e7eb;
    --code-bg: #f3f4f6;
    --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    --border-radius: 8px;
}

@media (prefers-color-scheme: dark) {
    :root {
        --bg-color: #111827;
        --text-color: #f9fafb;
        --border-color: #374151;
        --code-bg: #1f2937;
    }
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    line-height: 1.6;
    color: var(--text-color);
    background-color: var(--bg-color);
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 1rem;
}

/* Header */
header {
    background: var(--primary-color);
    color: white;
    padding: 1rem 0;
    box-shadow: var(--shadow);
}

.header-content {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.logo h1 {
    font-size: 1.5rem;
    font-weight: bold;
}

nav ul {
    display: flex;
    list-style: none;
    gap: 2rem;
}

nav a {
    color: white;
    text-decoration: none;
    transition: opacity 0.2s;
}

nav a:hover {
    opacity: 0.8;
}

/* Main content */
main {
    min-height: calc(100vh - 200px);
    padding: 2rem 0;
}

/* Articles */
.post-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 2rem;
    margin: 2rem 0;
}

.post-card {
    background: var(--bg-color);
    border: 1px solid var(--border-color);
    border-radius: var(--border-radius);
    padding: 1.5rem;
    box-shadow: var(--shadow);
    transition: transform 0.2s;
}

.post-card:hover {
    transform: translateY(-2px);
}

.post-meta {
    display: flex;
    align-items: center;
    gap: 1rem;
    font-size: 0.875rem;
    color: var(--secondary-color);
    margin-bottom: 1rem;
}

.category-badge {
    background: var(--primary-color);
    color: white;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.75rem;
}

.post-title {
    margin-bottom: 1rem;
}

.post-title a {
    color: var(--text-color);
    text-decoration: none;
}

.post-title a:hover {
    color: var(--primary-color);
}

/* Article content */
.post-content {
    max-width: 800px;
    margin: 0 auto;
}

.post-content h2,
.post-content h3,
.post-content h4 {
    margin: 2rem 0 1rem 0;
    color: var(--text-color);
}

.post-content p {
    margin-bottom: 1rem;
}

.post-content pre {
    background: var(--code-bg);
    padding: 1rem;
    border-radius: var(--border-radius);
    overflow-x: auto;
    margin: 1rem 0;
}

.post-content code {
    background: var(--code-bg);
    padding: 0.2rem 0.4rem;
    border-radius: 4px;
    font-family: "Fira Code", Monaco, monospace;
}

.post-content blockquote {
    border-left: 4px solid var(--accent-color);
    padding-left: 1rem;
    margin: 1rem 0;
    font-style: italic;
}

/* Tags */
.tags {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin: 1rem 0;
}

.tag {
    background: var(--secondary-color);
    color: white;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.75rem;
    text-decoration: none;
}

/* Footer */
footer {
    background: var(--secondary-color);
    color: white;
    text-align: center;
    padding: 2rem 0;
    margin-top: 4rem;
}

/* Responsive */
@media (max-width: 768px) {
    .header-content {
        flex-direction: column;
        gap: 1rem;
    }

    nav ul {
        flex-direction: column;
        text-align: center;
        gap: 1rem;
    }

    .post-grid {
        grid-template-columns: 1fr;
    }
}

/* Syntax highlighting */
.highlight {
    background: var(--code-bg);
    border-radius: var(--border-radius);
}

.highlight .err { color: #a61717; background-color: #e3d2d2; }
.highlight .k { color: #000000; font-weight: bold; }
.highlight .o { color: #000000; font-weight: bold; }
.highlight .cm { color: #999988; font-style: italic; }
.highlight .cp { color: #999999; font-weight: bold; font-style: italic; }
.highlight .c1 { color: #999988; font-style: italic; }
.highlight .cs { color: #999999; font-weight: bold; font-style: italic; }
.highlight .gd { color: #000000; background-color: #ffdddd; }
.highlight .ge { color: #000000; font-style: italic; }
.highlight .gr { color: #aa0000; }
.highlight .gh { color: #999999; }
.highlight .gi { color: #000000; background-color: #ddffdd; }
.highlight .go { color: #888888; }
.highlight .gp { color: #555555; }
.highlight .gs { font-weight: bold; }
.highlight .gu { color: #aaaaaa; }
.highlight .gt { color: #aa0000; }
.highlight .kc { color: #000000; font-weight: bold; }
.highlight .kd { color: #000000; font-weight: bold; }
.highlight .kn { color: #000000; font-weight: bold; }
.highlight .kp { color: #000000; font-weight: bold; }
.highlight .kr { color: #000000; font-weight: bold; }
.highlight .kt { color: #445588; font-weight: bold; }
.highlight .m { color: #009999; }
.highlight .s { color: #d01040; }
.highlight .na { color: #008080; }
.highlight .nb { color: #0086B3; }
.highlight .nc { color: #445588; font-weight: bold; }
.highlight .no { color: #008080; }
.highlight .nd { color: #3c5d5d; font-weight: bold; }
.highlight .ni { color: #800080; }
.highlight .ne { color: #990000; font-weight: bold; }
.highlight .nf { color: #990000; font-weight: bold; }
.highlight .nl { color: #990000; font-weight: bold; }
.highlight .nn { color: #555555; }
.highlight .nt { color: #000080; }
.highlight .nv { color: #008080; }
.highlight .ow { color: #000000; font-weight: bold; }
.highlight .w { color: #bbbbbb; }
.highlight .mf { color: #009999; }
.highlight .mh { color: #009999; }
.highlight .mi { color: #009999; }
.highlight .mo { color: #009999; }
.highlight .sb { color: #d01040; }
.highlight .sc { color: #d01040; }
.highlight .sd { color: #d01040; }
.highlight .s2 { color: #d01040; }
.highlight .se { color: #d01040; }
.highlight .sh { color: #d01040; }
.highlight .si { color: #d01040; }
.highlight .sx { color: #d01040; }
.highlight .sr { color: #009926; }
.highlight .s1 { color: #d01040; }
.highlight .ss { color: #990073; }
.highlight .bp { color: #999999; }
.highlight .vc { color: #008080; }
.highlight .vg { color: #008080; }
.highlight .vi { color: #008080; }
.highlight .il { color: #009999; }
'''

        css_dir = OUTPUT_DIR / 'css'
        css_dir.mkdir(exist_ok=True)
        with open(css_dir / 'style.css', 'w', encoding='utf-8') as f:
            f.write(css_content)

    def _generate_default_js(self):
        """Génère un JavaScript par défaut pour interactivité"""
        js_content = '''// AgentBnZo Blog - JavaScript interactif

document.addEventListener('DOMContentLoaded', function() {
    // Dark mode toggle
    initDarkMode();

    // Search functionality
    initSearch();

    // Smooth scrolling
    initSmoothScrolling();

    // Reading progress
    initReadingProgress();
});

function initDarkMode() {
    const darkModeToggle = document.createElement('button');
    darkModeToggle.innerHTML = '🌙';
    darkModeToggle.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: var(--primary-color);
        color: white;
        border: none;
        border-radius: 50%;
        width: 50px;
        height: 50px;
        cursor: pointer;
        font-size: 20px;
        z-index: 1000;
    `;

    darkModeToggle.addEventListener('click', function() {
        document.body.classList.toggle('dark-mode');
        darkModeToggle.innerHTML = document.body.classList.contains('dark-mode') ? '☀️' : '🌙';
    });

    document.body.appendChild(darkModeToggle);
}

function initSearch() {
    const searchInput = document.querySelector('#search');
    if (searchInput) {
        searchInput.addEventListener('input', function(e) {
            const query = e.target.value.toLowerCase();
            const posts = document.querySelectorAll('.post-card');

            posts.forEach(post => {
                const title = post.querySelector('.post-title').textContent.toLowerCase();
                const content = post.textContent.toLowerCase();

                if (title.includes(query) || content.includes(query)) {
                    post.style.display = 'block';
                } else {
                    post.style.display = 'none';
                }
            });
        });
    }
}

function initSmoothScrolling() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });
}

function initReadingProgress() {
    if (document.querySelector('.post-content')) {
        const progressBar = document.createElement('div');
        progressBar.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 0%;
            height: 3px;
            background: var(--accent-color);
            z-index: 1000;
            transition: width 0.3s;
        `;
        document.body.appendChild(progressBar);

        window.addEventListener('scroll', function() {
            const scrollTop = window.pageYOffset;
            const docHeight = document.documentElement.scrollHeight - window.innerHeight;
            const scrollPercent = (scrollTop / docHeight) * 100;
            progressBar.style.width = scrollPercent + '%';
        });
    }
}

// Lazy loading images
function initLazyLoading() {
    const images = document.querySelectorAll('img[data-src]');
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.classList.remove('lazy');
                imageObserver.unobserve(img);
            }
        });
    });

    images.forEach(img => imageObserver.observe(img));
}

// Analytics (si nécessaire)
function trackPageView() {
    console.log('Page view:', window.location.pathname);
}

trackPageView();
'''

        js_dir = OUTPUT_DIR / 'js'
        js_dir.mkdir(exist_ok=True)
        with open(js_dir / 'main.js', 'w', encoding='utf-8') as f:
            f.write(js_content)

    # Méthodes utilitaires pour Jinja2
    def _format_date(self, date: datetime, format: str = '%d/%m/%Y') -> str:
        """Formate une date pour l'affichage"""
        return date.strftime(format)

    def _truncate_words(self, text: str, length: int = 50) -> str:
        """Tronque un texte au nombre de mots"""
        words = text.split()
        if len(words) <= length:
            return text
        return ' '.join(words[:length]) + '...'

    def _create_url_slug(self, text: str) -> str:
        """Crée un slug URL-friendly"""
        # Supprimer caractères spéciaux
        slug = re.sub(r'[^\w\s-]', '', text.lower())
        # Remplacer espaces par tirets
        slug = re.sub(r'[-\s]+', '-', slug)
        return slug.strip('-')

def main():
    """Test du moteur de blog"""
    logging.basicConfig(level=logging.INFO)

    engine = BlogEngine()

    # Parse posts existants
    posts = engine.parse_posts()
    print(f"Articles trouvés: {len(posts)}")

    if posts:
        # Générer site
        results = engine.generate_site(posts)
        print(f"✅ Site généré dans: {OUTPUT_DIR}")
        print(f"Pages créées: {len(results['posts'])} articles, {len(results['categories'])} catégories")
    else:
        print("❌ Aucun article trouvé")

if __name__ == "__main__":
    main()