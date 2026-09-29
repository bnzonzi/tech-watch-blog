#!/usr/bin/env python3
"""
Système minimal d'alimentation automatique du blog AgentBnZo
Version simplifiée avec Gemini 2.5 Flash uniquement
"""

import os
import sys
import json
import requests
import feedparser
import google.generativeai as genai
from datetime import datetime
from pathlib import Path
import logging
import time
import re

# Mode dry-run si argument fourni
DRY_RUN = '--dry-run' in sys.argv or '--test' in sys.argv

# Configuration
from dotenv import load_dotenv
BLOG_DIR = Path("/media/raid10to/projets/blog")
load_dotenv(BLOG_DIR / ".env")
OUTPUT_DIR = BLOG_DIR / "output"
POSTS_DIR = OUTPUT_DIR / "posts"
FEEDLY_CONFIG = Path("/media/raid10to/projets/crews/tech_watch_autolearning_crew/knowledge/feedly_classified_feeds.json")
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = "6707310411"
if not GEMINI_API_KEY:
    raise ValueError("GOOGLE_API_KEY manquante dans .env")

# Outils AgentBnZo (pour filtrage)
AGENTBNZO_TOOLS = [
    "CrewAI", "Python", "Docker", "RAID", "IPfire", "Kali", "Ubuntu", "SSH",
    "Telegram", "OpenAI", "Gemini", "LM-Studio", "Ollama", "QEMU", "Libvirt",
    "Bash", "systemd", "cron", "rsync", "Git", "PostgreSQL", "SQLite",
    "Nginx", "Apache", "Linux", "Sécurité", "Monitoring", "Backup"
]

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(BLOG_DIR / "logs" / "blog_feeder.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def setup_directories():
    """Créer les répertoires nécessaires"""
    for dir_path in [OUTPUT_DIR, POSTS_DIR, BLOG_DIR / "logs"]:
        dir_path.mkdir(parents=True, exist_ok=True)

def load_feedly_feeds():
    """Charger les flux Feedly classifiés"""
    try:
        with open(FEEDLY_CONFIG, 'r', encoding='utf-8') as f:
            feeds_data = json.load(f)

        # Extraire les URLs des flux pertinents
        urls = []
        for category in ['ai_ml', 'security', 'hardware_tech']:
            if category in feeds_data:
                for feed in feeds_data[category]:
                    if 'url' in feed:
                        urls.append(feed['url'])

        logger.info(f"📡 Chargé {len(urls)} flux RSS")
        return urls
    except Exception as e:
        logger.error(f"❌ Erreur chargement flux Feedly: {e}")
        return []

def analyze_rss_feeds(feed_urls, max_articles=150):
    """Analyser les flux RSS et extraire les articles pertinents"""
    articles = []

    # Mode dry-run: limite drastique pour test rapide
    feed_limit = 3 if DRY_RUN else 250
    article_limit = 2 if DRY_RUN else 150

    for url in feed_urls[:feed_limit]:  # Limiter flux pour éviter surcharge
        try:
            logger.info(f"📖 Analyse flux: {url}")
            feed = feedparser.parse(url)

            for entry in feed.entries[:article_limit]:  # Max articles par flux
                # Filtrage basique par mots-clés AgentBnZo
                content = f"{entry.get('title', '')} {entry.get('summary', '')}"

                relevance_score = 0
                for tool in AGENTBNZO_TOOLS:
                    if tool.lower() in content.lower():
                        relevance_score += 1

                if relevance_score >= 2:  # Au moins 2 outils mentionnés
                    articles.append({
                        'title': entry.get('title', ''),
                        'summary': entry.get('summary', ''),
                        'link': entry.get('link', ''),
                        'published': entry.get('published', ''),
                        'source': feed.feed.get('title', url),
                        'relevance_score': relevance_score
                    })

            time.sleep(1)  # Politesse entre requêtes

        except Exception as e:
            logger.error(f"❌ Erreur analyse flux {url}: {e}")
            continue

    # Trier par pertinence et limiter
    articles.sort(key=lambda x: x['relevance_score'], reverse=True)
    return articles[:max_articles]

def generate_article_with_gemini(source_article):
    """Générer un article avec Gemini 2.5 Flash"""

    # Mode dry-run: simuler sans appel API
    if DRY_RUN:
        logger.info("🔬 DRY-RUN: Simulation génération Gemini")
        return f"""# Article Simulé - {source_article['title']}

Ceci est un article généré en mode dry-run pour tester le système.

## Introduction
Article basé sur: {source_article['title']}

## Contenu technique
Analyse des outils AgentBnZo pertinents pour ce sujet.

## Conclusion
Article de test généré sans appel API Gemini.
"""

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-06-17')

        prompt = f"""
Tu es un expert technique AgentBnZo qui rédige des articles pratiques.

ARTICLE SOURCE:
Titre: {source_article['title']}
Résumé: {source_article['summary']}
Source: {source_article['source']}

CONSIGNES:
- Rédige en français ; première personne obligatoire : **je** ou **nous** (jamais voix impersonnelle pour le récit principal)
- Style tutorial/best-practice/retour d'expérience
- Focus sur l'application pratique avec les outils AgentBnZo
- 800-1200 mots
- Structure: Introduction, Contexte technique, Mise en pratique, Conclusion
- Évite les sujets non applicables sur le système AgentBnZo

OUTILS AGENTBNZO DISPONIBLES:
{', '.join(AGENTBNZO_TOOLS)}

Génère un article pratique et actionnable:
"""

        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        logger.error(f"❌ Erreur génération Gemini: {e}")
        return None

def create_blog_post(article_content, source_article):
    """Créer un post de blog HTML"""
    # Générer slug pour URL
    title_clean = re.sub(r'[^a-zA-Z0-9\s]', '', source_article['title'])
    slug = re.sub(r'\s+', '-', title_clean.lower())[:50]
    date_str = datetime.now().strftime('%Y-%m-%d')

    # Extraire titre du contenu généré
    lines = article_content.split('\n')
    generated_title = lines[0].replace('#', '').strip() if lines else source_article['title']

    # Template HTML simple
    html_content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{generated_title} - Blog AgentBnZo</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; }}
        .header {{ border-bottom: 2px solid #0066cc; padding-bottom: 20px; margin-bottom: 30px; }}
        .meta {{ color: #666; font-size: 0.9em; margin-bottom: 20px; }}
        .content {{ margin-bottom: 40px; }}
        .source {{ background: #f5f5f5; padding: 15px; border-radius: 5px; }}
        h1 {{ color: #0066cc; }}
        h2, h3 {{ color: #333; }}
        code {{ background: #f4f4f4; padding: 2px 4px; border-radius: 3px; }}
        .back-link {{ margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 Blog AgentBnZo</h1>
        <p>Techniques et pratiques pour l'écosystème multi-agents</p>
    </div>

    <article>
        <h1>{generated_title}</h1>
        <div class="meta">
            📅 {date_str} | 🔗 <a href="{source_article['link']}" target="_blank">Source: {source_article['source']}</a>
        </div>

        <div class="content">
            {article_content.replace(chr(10), '<br>').replace('**', '<strong>').replace('**', '</strong>')}
        </div>

        <div class="source">
            <h3>📰 Source originale</h3>
            <p><strong>{source_article['title']}</strong></p>
            <p>{source_article['summary']}</p>
            <a href="{source_article['link']}" target="_blank">Lire l'article original</a>
        </div>
    </article>

    <div class="back-link">
        <a href="../index.html">← Retour au blog</a>
    </div>
</body>
</html>"""

    # Sauvegarder l'article
    filename = f"{date_str}-{slug}.html"
    filepath = POSTS_DIR / filename

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)

    logger.info(f"📄 Article créé: {filename}")
    return filename, generated_title

def update_blog_index():
    """Mettre à jour la page d'accueil du blog"""
    # Lister tous les articles
    posts = []
    for post_file in POSTS_DIR.glob("*.html"):
        # Extraire date et titre du nom de fichier
        parts = post_file.stem.split('-', 3)
        if len(parts) >= 4:
            date_str = f"{parts[0]}-{parts[1]}-{parts[2]}"
            title = parts[3].replace('-', ' ').title()
            posts.append({
                'filename': post_file.name,
                'date': date_str,
                'title': title
            })

    # Trier par date décroissante
    posts.sort(key=lambda x: x['date'], reverse=True)

    # Générer HTML index
    posts_html = ""
    for post in posts[:10]:  # Derniers 10 articles
        posts_html += f"""
        <article class="post-preview">
            <h2><a href="posts/{post['filename']}">{post['title']}</a></h2>
            <p class="meta">📅 {post['date']}</p>
        </article>
        """

    index_html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Blog AgentBnZo - Techniques Multi-Agents</title>
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
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 Blog AgentBnZo</h1>
        <p class="subtitle">Techniques et pratiques pour l'écosystème multi-agents</p>
        <div class="stats">
            <div class="stat">
                <strong>{len(posts)}</strong><br>Articles
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
        {posts_html}
    </div>

    <footer style="text-align: center; margin-top: 40px; color: #666;">
        <p>🔄 Dernière mise à jour: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        <p>Alimenté automatiquement par Gemini 2.5 Flash depuis les flux Feedly AgentBnZo</p>
    </footer>
</body>
</html>"""

    with open(OUTPUT_DIR / "index.html", 'w', encoding='utf-8') as f:
        f.write(index_html)

    logger.info("🏠 Page d'accueil mise à jour")

def send_telegram_notification(message):
    """Envoyer notification Telegram"""

    # Mode dry-run: simuler notification
    if DRY_RUN:
        logger.info(f"🔬 DRY-RUN: Notification Telegram simulée - {message}")
        return

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': f"🤖 Blog AgentBnZo\n\n{message}",
            'parse_mode': 'HTML'
        }
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            logger.info("📱 Notification Telegram envoyée")
        else:
            logger.error(f"❌ Échec notification Telegram: {response.status_code}")
    except Exception as e:
        logger.error(f"❌ Erreur notification: {e}")

def main():
    """Fonction principale d'alimentation du blog"""
    mode_str = " (DRY-RUN MODE)" if DRY_RUN else ""
    logger.info(f"🚀 Démarrage alimentation automatique blog AgentBnZo{mode_str}")

    if DRY_RUN:
        logger.info("🔬 Mode test actif - aucun appel API, 3 flux max, notifications simulées")

    # Setup
    setup_directories()

    # Charger et analyser les flux
    feed_urls = load_feedly_feeds()
    if not feed_urls:
        logger.error("❌ Aucun flux Feedly trouvé")
        return

    articles = analyze_rss_feeds(feed_urls, max_articles=150)
    logger.info(f"📊 {len(articles)} articles pertinents trouvés")

    if not articles:
        logger.info("ℹ️ Aucun article pertinent aujourd'hui")
        return

    # Générer articles
    generated_count = 0
    for article in articles:
        logger.info(f"✍️ Génération article: {article['title'][:50]}...")

        content = generate_article_with_gemini(article)
        if content:
            filename, title = create_blog_post(content, article)
            generated_count += 1

            # Notification pour chaque article
            send_telegram_notification(f"✅ Nouvel article publié: <b>{title}</b>")

        time.sleep(2)  # Pause entre générations

    # Mettre à jour l'index
    update_blog_index()

    # Rapport final
    blog_url = f"file://{OUTPUT_DIR}/index.html"
    report = f"""📈 Session terminée:
• {len(articles)} articles analysés
• {generated_count} articles générés
• Blog mis à jour: {blog_url}"""

    logger.info(report)
    send_telegram_notification(report)

if __name__ == "__main__":
    main()
