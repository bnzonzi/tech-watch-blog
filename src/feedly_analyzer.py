#!/usr/bin/env python3
"""
Analyseur de flux RSS Feedly avec filtrage intelligent
Basé sur l'infrastructure existante tech_watch_autolearning_crew
Focus sur les outils présents dans la codebase AgentBnZo
"""

import os
import sys
import json
import logging
import requests
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import re

# Import configuration
sys.path.append(str(Path(__file__).parent.parent))
from config.blog_config import (
    FEEDLY_RSS_URLS_PATH, BLOG_CATEGORIES, CONTENT_FILTER_CONFIG,
    BLOG_ROOT
)

@dataclass
class AnalyzedArticle:
    """Article analysé avec scoring de pertinence"""
    title: str
    url: str
    summary: str
    published: str
    source_name: str
    category: str
    relevance_score: float
    codebase_matches: List[str]
    tech_keywords: List[str]
    template_type: str
    raw_content: str = ""

class FeedlyAnalyzer:
    """
    Analyseur intelligent des flux RSS Feedly
    Filtre le contenu selon la pertinence pour AgentBnZo
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AgentBnZo-TechBlog/1.0 (https://github.com/AgentBnZo)'
        })

        # Compilation des patterns pour optimisation
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile les patterns regex pour le filtrage rapide"""
        self.codebase_patterns = {}
        self.tech_patterns = {}

        # Patterns pour outils codebase
        for category, config in BLOG_CATEGORIES.items():
            patterns = []
            for tool in config.get("codebase_tools", []):
                # Pattern flexible pour variations du nom
                pattern = rf'\b{re.escape(tool).replace("_", "[_-]?")}\b'
                patterns.append(pattern)
            self.codebase_patterns[category] = re.compile(
                '|'.join(patterns), re.IGNORECASE
            ) if patterns else None

            # Patterns pour mots-clés techniques
            tech_keywords = config.get("keywords", [])
            if tech_keywords:
                self.tech_patterns[category] = re.compile(
                    '|'.join(rf'\b{kw}\b' for kw in tech_keywords),
                    re.IGNORECASE
                )

    def get_filtered_rss_urls(self) -> List[Tuple[str, str]]:
        """
        Récupère et filtre les URLs RSS pertinentes
        Returns: List[(url, source_name)]
        """
        if not Path(FEEDLY_RSS_URLS_PATH).exists():
            self.logger.error(f"Fichier RSS non trouvé: {FEEDLY_RSS_URLS_PATH}")
            return []

        urls = []
        with open(FEEDLY_RSS_URLS_PATH, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Extraire nom source depuis l'URL
                    source_name = self._extract_source_name(line)

                    # Filtrer selon sources préférées
                    if self._is_preferred_source(line, source_name):
                        urls.append((line, source_name))

        self.logger.info(f"URLs RSS filtrées: {len(urls)}")
        return urls

    def _extract_source_name(self, url: str) -> str:
        """Extrait le nom de la source depuis l'URL"""
        if "korben.info" in url:
            return "Korben"
        elif "nvidia" in url:
            return "NVIDIA"
        elif "pytorch" in url:
            return "PyTorch"
        elif "automl.org" in url:
            return "AutoML"
        elif "youtube.com" in url:
            # Extraire ID chaîne YouTube si possible
            return "YouTube"
        elif "medium.com" in url:
            return "Medium"
        else:
            # Extraire domaine principal
            try:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc
                return domain.replace('www.', '').split('.')[0].title()
            except:
                return "RSS Feed"

    def _is_preferred_source(self, url: str, source_name: str) -> bool:
        """Vérifie si la source est dans les préférées"""
        preferred = CONTENT_FILTER_CONFIG.get("preferred_sources", [])

        # Toujours inclure si pas de filtre
        if not preferred:
            return True

        # Vérifier URL et nom source
        for pref in preferred:
            if pref.lower() in url.lower() or pref.lower() in source_name.lower():
                return True

        return False

    def fetch_and_analyze_articles(self, max_articles: int = 50) -> List[AnalyzedArticle]:
        """
        Récupère et analyse les articles de tous les flux RSS
        """
        urls = self.get_filtered_rss_urls()
        all_articles = []

        for url, source_name in urls:
            try:
                articles = self._fetch_rss_articles(url, source_name, limit=10)
                all_articles.extend(articles)

                # Limite globale
                if len(all_articles) >= max_articles:
                    break

            except Exception as e:
                self.logger.warning(f"Erreur fetch RSS {url}: {e}")
                continue

        # Analyser et scorer
        analyzed_articles = []
        for article in all_articles:
            analyzed = self._analyze_article(article)
            if analyzed and analyzed.relevance_score >= CONTENT_FILTER_CONFIG.get("min_relevance_score", 0.7):
                analyzed_articles.append(analyzed)

        # Trier par score de pertinence
        analyzed_articles.sort(key=lambda x: x.relevance_score, reverse=True)

        self.logger.info(f"Articles analysés: {len(analyzed_articles)}/{len(all_articles)}")
        return analyzed_articles[:CONTENT_FILTER_CONFIG.get("max_articles_per_day", 3)]

    def _fetch_rss_articles(self, url: str, source_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Parse un flux RSS et extrait les articles récents"""
        articles = []

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            root = ET.fromstring(response.content)

            # Support RSS 2.0 et Atom
            if root.tag == 'rss':
                items = root.findall('.//item')
            else:  # Atom
                items = root.findall('.//{http://www.w3.org/2005/Atom}entry')

            for item in items[:limit]:
                article = self._parse_rss_item(item, source_name)
                if article and self._is_recent_article(article.get('published', '')):
                    articles.append(article)

        except Exception as e:
            self.logger.warning(f"Erreur parsing RSS {url}: {e}")

        return articles

    def _parse_rss_item(self, item: ET.Element, source_name: str) -> Optional[Dict[str, Any]]:
        """Parse un item RSS/Atom en article"""
        try:
            if item.tag == 'item':  # RSS 2.0
                title = item.findtext('title', '').strip()
                url = item.findtext('link', '').strip()
                summary = item.findtext('description', '').strip()
                published = item.findtext('pubDate', '').strip()
            else:  # Atom
                ns = {'atom': 'http://www.w3.org/2005/Atom'}
                title = item.findtext('./atom:title', '', ns).strip()

                link_elem = item.find('./atom:link[@rel="alternate"]', ns)
                url = link_elem.get('href', '') if link_elem is not None else ''

                summary = item.findtext('./atom:summary', '', ns).strip()
                published = item.findtext('./atom:published', '', ns).strip()

            if not title or not url:
                return None

            return {
                'title': title,
                'url': url,
                'summary': summary,
                'published': published,
                'source_name': source_name
            }

        except Exception as e:
            self.logger.warning(f"Erreur parse item: {e}")
            return None

    def _is_recent_article(self, published_str: str) -> bool:
        """Vérifie si l'article est récent (dernières 48h)"""
        if not published_str:
            return True  # Inclure si pas de date

        try:
            # Essayer plusieurs formats de date
            for fmt in ['%a, %d %b %Y %H:%M:%S %z',
                       '%Y-%m-%dT%H:%M:%S%z',
                       '%Y-%m-%d %H:%M:%S']:
                try:
                    pub_date = datetime.strptime(published_str, fmt)
                    if pub_date.tzinfo is None:
                        pub_date = pub_date.replace(tzinfo=datetime.now().astimezone().tzinfo)

                    cutoff = datetime.now().astimezone() - timedelta(hours=48)
                    return pub_date >= cutoff
                except ValueError:
                    continue

            return True  # Si parsing échoue, inclure par défaut

        except Exception:
            return True

    def _analyze_article(self, article: Dict[str, Any]) -> Optional[AnalyzedArticle]:
        """Analyse un article et calcule son score de pertinence"""
        content = f"{article['title']} {article['summary']}"

        # Vérifier mots-clés exclus
        excluded = CONTENT_FILTER_CONFIG.get("excluded_keywords", [])
        if any(kw.lower() in content.lower() for kw in excluded):
            return None

        # Analyser catégorie et scoring
        category, score, matches, tech_kws = self._calculate_relevance(content)

        if score < CONTENT_FILTER_CONFIG.get("min_relevance_score", 0.7):
            return None

        # Déterminer type de template
        template_type = self._determine_template_type(article['title'], content)

        return AnalyzedArticle(
            title=article['title'],
            url=article['url'],
            summary=article['summary'],
            published=article['published'],
            source_name=article['source_name'],
            category=category,
            relevance_score=score,
            codebase_matches=matches,
            tech_keywords=tech_kws,
            template_type=template_type,
            raw_content=content
        )

    def _calculate_relevance(self, content: str) -> Tuple[str, float, List[str], List[str]]:
        """Calcule le score de pertinence et identifie les correspondances"""
        best_category = "general"
        best_score = 0.0
        best_matches = []
        best_tech_kws = []

        for category, config in BLOG_CATEGORIES.items():
            score = 0.0
            matches = []
            tech_kws = []

            # Score codebase tools (poids fort)
            if self.codebase_patterns.get(category):
                codebase_matches = self.codebase_patterns[category].findall(content)
                if codebase_matches:
                    score += len(set(codebase_matches)) * 0.4
                    matches.extend(codebase_matches)

            # Score mots-clés techniques
            if self.tech_patterns.get(category):
                tech_matches = self.tech_patterns[category].findall(content)
                if tech_matches:
                    score += len(set(tech_matches)) * 0.2
                    tech_kws.extend(tech_matches)

            # Score keywords généraux
            keywords = config.get("keywords", [])
            general_matches = sum(1 for kw in keywords if kw.lower() in content.lower())
            score += general_matches * 0.1

            # Bonus source préférée
            if any(src in content for src in CONTENT_FILTER_CONFIG.get("preferred_sources", [])):
                score += 0.2

            if score > best_score:
                best_score = score
                best_category = category
                best_matches = list(set(matches))
                best_tech_kws = list(set(tech_kws))

        # Normaliser le score entre 0 et 1
        normalized_score = min(best_score, 1.0)

        return best_category, normalized_score, best_matches, best_tech_kws

    def _determine_template_type(self, title: str, content: str) -> str:
        """Détermine le type de template le plus approprié"""
        title_lower = title.lower()
        content_lower = content.lower()

        # Patterns pour différents types
        if any(word in title_lower for word in ["tutorial", "guide", "how to", "comment"]):
            return "tutorial"
        elif any(word in content_lower for word in ["best practice", "methodology", "approach"]):
            return "best_practice"
        elif any(word in title_lower for word in ["analysis", "review", "study", "benchmark"]):
            return "analysis"
        elif any(word in content_lower for word in ["innovation", "new", "breakthrough", "advance"]):
            return "innovation"
        else:
            return "analysis"  # Par défaut

    def export_analysis_results(self, articles: List[AnalyzedArticle],
                               output_path: Optional[Path] = None) -> Path:
        """Exporte les résultats d'analyse en JSON"""
        if not output_path:
            output_path = BLOG_ROOT / "content" / "analysis_results.json"

        results = {
            "timestamp": datetime.now().isoformat(),
            "total_articles": len(articles),
            "articles": [asdict(article) for article in articles],
            "categories_distribution": self._get_categories_stats(articles)
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Résultats exportés: {output_path}")
        return output_path

    def _get_categories_stats(self, articles: List[AnalyzedArticle]) -> Dict[str, int]:
        """Calcule les statistiques par catégorie"""
        stats = {}
        for article in articles:
            stats[article.category] = stats.get(article.category, 0) + 1
        return stats

def main():
    """Test de l'analyseur Feedly"""
    logging.basicConfig(level=logging.INFO,
                       format='%(asctime)s - %(levelname)s - %(message)s')

    analyzer = FeedlyAnalyzer()

    print("🔍 Analyse des flux RSS Feedly...")
    articles = analyzer.fetch_and_analyze_articles(max_articles=20)

    print(f"\n📊 Résultats ({len(articles)} articles):")
    for i, article in enumerate(articles, 1):
        print(f"{i}. [{article.category}] {article.title}")
        print(f"   Score: {article.relevance_score:.2f} | Matches: {article.codebase_matches}")
        print(f"   Source: {article.source_name} | Template: {article.template_type}")
        print()

    # Export résultats
    output_path = analyzer.export_analysis_results(articles)
    print(f"✅ Résultats exportés: {output_path}")

if __name__ == "__main__":
    main()