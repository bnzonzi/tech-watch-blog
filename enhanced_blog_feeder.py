# enhanced_blog_feeder.py
import os
import logging
from datetime import datetime
import json
from bs4 import BeautifulSoup
import requests

# Setup logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants and paths
CONFIG_FILE = 'config.json'
LOGS_DIR = 'logs'
POSTS_DIR = 'posts'
METADATA_DIR = 'metadata'

# Initialize directories if they don't exist
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(POSTS_DIR, exist_ok=True)
os.makedirs(METADATA_DIR, exist_ok=True)

class QualityFilter:
    @staticmethod
    def should_include_article(article_data):
        # Dummy implementation for demonstration
        return True, "Valid article", {"score": 5}

def main():
    with open(CONFIG_FILE) as config_file:
        config = json.load(config_file)
    
    articles = scrape_articles(config['feeds'])

    processed_articles = [process_article(entry, {'title': 'Feed RSS'}) for entry in articles]
    
    saved_articles = []
    for article in filter(None, processed_articles):
        if save_article(article):
            saved_articles.append(article)

def scrape_articles(feeds):
    entries = []
    for feed_url in feeds:
        response = requests.get(feed_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        articles = soup.find_all('item')
        if not articles:
            articles = soup.find_all('entry')
        
        for article in articles:
            title = article.title.string if article.title else 'Sans titre'
            link = article.link.get('href', '') if hasattr(article.link, 'get') else (article.link.string if article.link else '')
            description = article.description.string if article.description else ''
            
            entry = {
                'title': title,
                'description': description,
                'link': link,
            }
            
            entries.append(entry)
    
    return entries

def process_article(entry, feed):
    title = entry.get('title', 'Sans titre')
    description = entry.get('description', '')
    link = entry.get('link', '')

    should_include, reason, quality_details = QualityFilter.should_include_article({
        'title': title,
        'content': description,
        'summary': description,
        'link': link
    })

    if not should_include:
        logger.info(f"🚫 Article filtré: {title[:50]}... | Raison: {reason} | Score: {quality_details.get('score', 0)}")
        return None

    quality_score = quality_details.get('score', 0)
    logger.info(f"✅ Article validé (score: {quality_score}): {title[:50]}...")

    # Création d'un contenu HTML simple pour test
    content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
</head>
<body>
    <article>
        <h1>{title}</h1>
        <p><strong>Source:</strong> <a href="{link}" target="_blank">{link}</a></p>
        <div class="content">
            <p>{description}</p>
        </div>
        <footer>
            <p><small>Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}</small></p>
        </footer>
    </article>
</body>
</html>"""

    enhanced_content = content
    
    try:
        is_enhanced = enhanced_content != content
    except Exception as e:
        is_enhanced = False
    
    return {
        'title': title,
        'content': enhanced_content,
        'source_url': link,
        'source_feed': feed.get('title'),
        'generated_at': datetime.now().isoformat(),
        'fabric_enhanced': is_enhanced,
        'quality_score': quality_score,
        'quality_details': quality_details
    }

def save_article(article_content):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    title_clean = article_content['title'].replace(' ', '-').replace('/', '-')[:50]
    title_clean = ''.join(c for c in title_clean if c.isalnum() or c in '-_')

    filename = f"{datetime.now().strftime('%Y-%m-%d')}-{title_clean}.html"
    filepath = os.path.join(POSTS_DIR, filename)

    metadata_file = os.path.join(METADATA_DIR, f"metadata_{timestamp}.json")

    if not os.path.exists(filepath):
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(article_content['content'])

        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump({
                'title': article_content['title'],
                'source_url': article_content['source_url'],
                'source_feed': article_content['source_feed'],
                'generated_at': article_content['generated_at'],
                'filename': filename,
                'format': 'html',
                'fabric_enhanced': article_content.get('fabric_enhanced', False),
                'quality_score': article_content.get('quality_score', 0),
                'quality_details': article_content.get('quality_details', {}),
                'quality_filtered': True
            }, f, indent=2, ensure_ascii=False)

        return True

    logger.info(f"⏩ Article existe déjà: {filename}")
    return False

if __name__ == "__main__":
    main()