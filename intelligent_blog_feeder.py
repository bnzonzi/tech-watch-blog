#!/usr/bin/env python3
"""
Intelligent Blog Feeder avec filtrage catégories réel
Utilise:
- feedly_classified_feeds.json (mapping flux → catégories)
- agentbnzo_blog_config.json (config Category Manager)
"""
import os
import logging
import json
import hashlib
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
import requests
import warnings
from bs4 import XMLParsedAsHTMLWarning

# Supprimer warning XML/HTML
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# Setup logger
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Chemins
BLOG_ROOT = Path(__file__).parent
FEEDS_FILE = BLOG_ROOT / 'crews/tech_watch_autolearning_crew/knowledge/feedly_classified_feeds.json'
CONFIG_FILE = BLOG_ROOT / 'agentbnzo_blog_config.json'
POSTS_DIR = BLOG_ROOT / 'posts'
METADATA_DIR = BLOG_ROOT / 'metadata'
LOGS_DIR = BLOG_ROOT / 'logs'

# Créer répertoires
POSTS_DIR.mkdir(exist_ok=True)
METADATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)


class CategoryAwareFeeder:
    """Feeder intelligent avec filtrage catégories"""

    def __init__(self):
        self.feeds_map = self.load_feeds_mapping()
        self.config = self.load_user_config()
        self.stats = {
            'total_fetched': 0,
            'filtered_out': 0,
            'saved': 0,
            'errors': 0,
            'by_category': {}
        }

    def load_feeds_mapping(self):
        """Charge le mapping flux RSS → catégories"""
        if not FEEDS_FILE.exists():
            logger.error(f"❌ Fichier feeds introuvable: {FEEDS_FILE}")
            return {}

        with open(FEEDS_FILE, 'r', encoding='utf-8') as f:
            feeds = json.load(f)

        logger.info(f"✅ {sum(len(v) for v in feeds.values())} flux chargés")
        return feeds

    def load_user_config(self):
        """Charge la configuration utilisateur (Category Manager)"""
        if not CONFIG_FILE.exists():
            logger.warning(f"⚠️ Pas de config utilisateur, mode ALL")
            # Configuration par défaut : tout actif
            return {
                "agentbnzo_config": {
                    "enabled_categories": {
                        cat: {"enabled": True, "youtube_subcategories": {"enabled": True}, "non_youtube_sources": {"enabled": True}}
                        for cat in ["ai_ml", "software_dev", "hardware_tech", "security",
                                    "mobile_android", "mobile_ios", "cloud_computing", "enterprise", "china_tech_ai"]
                    },
                    "global_filters": {
                        "exclude_religion": True,
                        "exclude_sports": False,
                        "agentbnzo_relevance_only": True
                    }
                }
            }

        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)

        logger.info(f"✅ Configuration utilisateur chargée")
        return config

    def is_category_enabled(self, category):
        """Vérifie si une catégorie est activée"""
        enabled_cats = self.config.get('agentbnzo_config', {}).get('enabled_categories', {})
        cat_config = enabled_cats.get(category, {})
        return cat_config.get('enabled', False)

    def is_source_enabled(self, category, feed_url):
        """Vérifie si un type de source est activé (YouTube vs non-YouTube)"""
        enabled_cats = self.config.get('agentbnzo_config', {}).get('enabled_categories', {})
        cat_config = enabled_cats.get(category, {})

        is_youtube = 'youtube.com' in feed_url

        if is_youtube:
            return cat_config.get('youtube_subcategories', {}).get('enabled', False)
        else:
            return cat_config.get('non_youtube_sources', {}).get('enabled', False)

    def get_active_feeds(self):
        """Retourne seulement les flux actifs selon config"""
        active_feeds = []

        for category, feeds in self.feeds_map.items():
            if not self.is_category_enabled(category):
                logger.info(f"⏭️ Catégorie désactivée: {category}")
                continue

            for feed in feeds:
                feed_url = feed['url']
                if self.is_source_enabled(category, feed_url):
                    active_feeds.append({
                        **feed,
                        'category': category
                    })

        logger.info(f"✅ {len(active_feeds)} flux actifs sélectionnés")
        return active_feeds

    def apply_global_filters(self, article):
        """Applique les filtres globaux"""
        filters = self.config.get('agentbnzo_config', {}).get('global_filters', {})

        title_lower = article.get('title', '').lower()
        content_lower = article.get('content', '').lower()

        # Filtre religion
        if filters.get('exclude_religion'):
            religion_keywords = ['bible', 'jesus', 'christ', 'god', 'church', 'prayer',
                                 'theology', 'testament', 'gospel', 'abraham', 'moses']
            if any(kw in title_lower or kw in content_lower for kw in religion_keywords):
                return False, "Religion/théologie exclu"

        # Filtre sport
        if filters.get('exclude_sports'):
            sport_keywords = ['football', 'basketball', 'tennis', 'soccer', 'nfl', 'nba']
            if any(kw in title_lower or kw in content_lower for kw in sport_keywords):
                return False, "Sport exclu"

        return True, "OK"

    def fetch_feed(self, feed_info):
        """Récupère les articles d'un flux RSS"""
        feed_url = feed_info['url']
        category = feed_info['category']

        try:
            response = requests.get(feed_url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'xml')  # Utiliser parser XML

            # Chercher items (RSS) ou entries (Atom)
            articles = soup.find_all('item')
            if not articles:
                articles = soup.find_all('entry')

            entries = []
            for article in articles[:5]:  # Limiter à 5 par flux
                title_tag = article.find('title')
                link_tag = article.find('link')
                desc_tag = article.find('description') or article.find('summary')

                title = title_tag.text if title_tag else 'Sans titre'
                link = link_tag.get('href', '') if hasattr(link_tag, 'get') else (link_tag.text if link_tag else '')
                description = desc_tag.text if desc_tag else ''

                entries.append({
                    'title': title,
                    'content': description,
                    'link': link,
                    'category': category,
                    'source_feed': feed_info.get('title', 'Unknown'),
                    'feed_url': feed_url
                })

            self.stats['total_fetched'] += len(entries)
            return entries

        except Exception as e:
            logger.error(f"❌ Erreur fetch {feed_url}: {e}")
            self.stats['errors'] += 1
            return []

    def save_article(self, article):
        """Sauvegarde un article"""
        try:
            # Générer nom de fichier unique
            title_clean = article['title'][:100].replace(' ', '-').replace('/', '-')
            title_clean = ''.join(c for c in title_clean if c.isalnum() or c in '-_')

            # Hash pour unicité
            content_hash = hashlib.md5(article['link'].encode()).hexdigest()[:8]
            filename = f"{datetime.now().strftime('%Y-%m-%d')}-{title_clean}-{content_hash}.html"
            filepath = POSTS_DIR / filename

            # Éviter doublons
            if filepath.exists():
                logger.debug(f"⏩ Article existe: {filename}")
                return False

            # Créer HTML
            html_content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>{article['title']}</title>
    <meta name="category" content="{article['category']}">
</head>
<body>
    <article>
        <h1>{article['title']}</h1>
        <p><strong>Source:</strong> <a href="{article['link']}" target="_blank">{article['source_feed']}</a></p>
        <p><strong>Catégorie:</strong> {article['category']}</p>
        <div class="content">
            <p>{article['content'][:500]}...</p>
        </div>
        <footer>
            <p><small>Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}</small></p>
        </footer>
    </article>
</body>
</html>"""

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)

            # Métadonnées
            metadata = {
                'title': article['title'],
                'category': article['category'],
                'source_url': article['link'],
                'source_feed': article['source_feed'],
                'feed_url': article['feed_url'],
                'generated_at': datetime.now().isoformat(),
                'filename': filename
            }

            metadata_file = METADATA_DIR / f"metadata_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{content_hash}.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            # Stats
            self.stats['saved'] += 1
            cat = article['category']
            self.stats['by_category'][cat] = self.stats['by_category'].get(cat, 0) + 1

            logger.info(f"✅ [{cat}] {article['title'][:60]}...")
            return True

        except Exception as e:
            logger.error(f"❌ Erreur save article: {e}")
            self.stats['errors'] += 1
            return False

    def run(self):
        """Exécution principale"""
        logger.info("=" * 60)
        logger.info("🚀 INTELLIGENT BLOG FEEDER - Démarrage")
        logger.info("=" * 60)

        # Récupérer flux actifs
        active_feeds = self.get_active_feeds()
        if not active_feeds:
            logger.warning("⚠️ Aucun flux actif, vérifier configuration")
            return

        # Traiter chaque flux
        for feed_info in active_feeds:
            logger.info(f"🔄 Traitement: {feed_info.get('title', 'Unknown')} [{feed_info['category']}]")

            articles = self.fetch_feed(feed_info)

            for article in articles:
                # Filtres globaux
                should_include, reason = self.apply_global_filters(article)
                if not should_include:
                    logger.debug(f"🚫 Filtré: {article['title'][:40]}... ({reason})")
                    self.stats['filtered_out'] += 1
                    continue

                # Sauvegarder
                self.save_article(article)

        # Rapport final
        logger.info("=" * 60)
        logger.info("📊 STATISTIQUES FINALES")
        logger.info("=" * 60)
        logger.info(f"Total récupéré: {self.stats['total_fetched']}")
        logger.info(f"Filtrés: {self.stats['filtered_out']}")
        logger.info(f"Sauvegardés: {self.stats['saved']}")
        logger.info(f"Erreurs: {self.stats['errors']}")
        logger.info("\n📁 Par catégorie:")
        for cat, count in sorted(self.stats['by_category'].items()):
            logger.info(f"  - {cat}: {count} articles")


if __name__ == "__main__":
    feeder = CategoryAwareFeeder()
    feeder.run()
