#!/usr/bin/env python3
"""
Script d'enrichissement des articles chinois
- Scraping contenu complet depuis URL source
- Traduction français via Gemini
- Génération analyse enrichie
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
import requests
import google.generativeai as genai

# Configuration
BLOG_DIR = Path("/media/raid10to/projets/blog")
OUTPUT_DIR = BLOG_DIR / "output" / "posts"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ChineseArticleEnricher:
    """Enrichit les articles chinois avec traduction et analyse"""

    def __init__(self):
        if not GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY manquante dans l'environnement")

        genai.configure(api_key=GOOGLE_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')

    def scrape_article_content(self, url: str) -> str:
        """Scrape le contenu complet de l'article"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extraction contenu principal (patterns communs sites chinois)
            content_selectors = [
                'article', '.article-content', '.post-content',
                '.content', '#content', 'main', '.main-content'
            ]

            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    # Nettoyer scripts/styles
                    for tag in content_elem(['script', 'style', 'nav', 'footer']):
                        tag.decompose()

                    text = content_elem.get_text(separator='\n', strip=True)
                    if len(text) > 200:  # Minimum viable
                        return text[:4000]  # Limite pour Gemini

            # Fallback: tout le body
            return soup.get_text(separator='\n', strip=True)[:4000]

        except Exception as e:
            logger.warning(f"Échec scraping {url}: {e}")
            return ""

    def translate_and_analyze(self, title: str, description: str, content: str) -> dict:
        """Traduit et analyse l'article via Gemini"""

        prompt = f"""Tu es un expert en IA et tech chinoise. Analyse cet article :

**Titre (chinois):** {title}
**Description:** {description}
**Contenu complet:**
{content}

Génère une analyse structurée en français :

1. **Traduction titre** (concise, percutante)
2. **Résumé exécutif** (2-3 phrases, contexte tech)
3. **Points clés** (3-5 bullet points)
4. **Analyse AgentBnZo** (Pourquoi c'est pertinent pour l'écosystème multi-agents ? Technologies applicables ?)
5. **Conclusion** (Impact, perspectives)

Format Markdown. Ton professionnel mais accessible."""

        try:
            response = self.model.generate_content(prompt)
            return {
                'success': True,
                'french_content': response.text,
                'generated_at': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Échec génération Gemini: {e}")
            return {'success': False, 'error': str(e)}

    def enrich_article(self, html_file: Path):
        """Enrichit un article HTML existant"""

        logger.info(f"📄 Traitement: {html_file.name}")

        # Parse HTML existant
        with open(html_file, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')

        # Extraction métadonnées
        title = soup.find('h2').text if soup.find('h2') else "Sans titre"
        description_elem = soup.select_one('.description p')
        description = description_elem.text if description_elem else ""

        source_link = soup.select_one('.original-source a')
        source_url = source_link['href'] if source_link and source_link.get('href') != 'None' else None

        if not source_url or source_url == 'None':
            logger.warning(f"⚠️  Pas d'URL source pour {html_file.name}, skip")
            return False

        # Scraping contenu complet
        logger.info(f"🌐 Scraping: {source_url}")
        full_content = self.scrape_article_content(source_url)

        if not full_content:
            logger.warning(f"⚠️  Contenu vide après scraping")
            full_content = description  # Fallback

        # Traduction + Analyse Gemini
        logger.info(f"🤖 Génération Gemini...")
        analysis = self.translate_and_analyze(title, description, full_content)

        if not analysis['success']:
            logger.error(f"❌ Échec enrichissement: {analysis.get('error')}")
            return False

        # Injection contenu enrichi dans HTML
        enriched_section = soup.new_tag('div', **{'class': 'enriched-content'})
        enriched_section.string = analysis['french_content']

        description_div = soup.select_one('.description')
        if description_div:
            description_div.insert_after(enriched_section)

        # Sauvegarde
        enriched_file = html_file.parent / f"enriched_{html_file.name}"
        with open(enriched_file, 'w', encoding='utf-8') as f:
            f.write(str(soup.prettify()))

        logger.info(f"✅ Enrichi: {enriched_file.name}")
        return True

def main():
    """Point d'entrée principal"""

    enricher = ChineseArticleEnricher()

    # Trouver articles chinois (pattern 2025-11-07 ou titres chinois)
    chinese_articles = list(OUTPUT_DIR.glob("*2025-11-07*.html"))

    logger.info(f"📊 {len(chinese_articles)} articles chinois trouvés")

    enriched_count = 0
    for article_file in chinese_articles[:5]:  # Limite test: 5 premiers
        if enricher.enrich_article(article_file):
            enriched_count += 1

    logger.info(f"🎉 Enrichissement terminé: {enriched_count}/{len(chinese_articles[:5])}")

if __name__ == "__main__":
    main()
