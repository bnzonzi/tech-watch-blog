#!/usr/bin/env python3
"""
Blog Feeder Enhanced avec système anti-doublons et sources chinoises
Intègre prévention stricte des doublons + sources manquantes
"""

import os
import json
import requests
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from anti_duplicate_system import AntiDuplicateSystem

class EnhancedBlogFeeder:
    """
    Feeder de blog avec prévention des doublons et sources enrichies
    """

    def __init__(self, blog_dir: str = "/media/raid10to/projets/blog"):
        self.blog_dir = Path(blog_dir)
        self.output_dir = self.blog_dir / "output" / "posts"
        self.config_dir = self.blog_dir / "config"

        # Système anti-doublons
        self.anti_dup = AntiDuplicateSystem(str(self.blog_dir))

        # Chargement configuration catégories
        self.category_config = self._load_category_config()

        # Configuration sources enrichies
        self.sources_config = self._load_enhanced_sources()

    def _load_category_config(self) -> Dict:
        """Charge la configuration des catégories depuis category_filters.json"""
        config_file = self.config_dir / "category_filters.json"

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                print(f"✅ Configuration catégories chargée depuis {config_file.name}")
                return config.get('agentbnzo_config', {})
        except FileNotFoundError:
            print(f"⚠️  Fichier {config_file} introuvable, configuration par défaut")
            return self._get_default_category_config()
        except json.JSONDecodeError as e:
            print(f"❌ Erreur lecture JSON: {e}")
            return self._get_default_category_config()

    def _get_default_category_config(self) -> Dict:
        """Configuration catégories par défaut si fichier JSON absent"""
        return {
            "enabled_categories": {
                "china_tech_ai": {
                    "enabled": True,
                    "non_youtube_sources": {"enabled": True}
                }
            },
            "global_filters": {
                "agentbnzo_relevance_only": True
            }
        }

    def _load_enhanced_sources(self) -> Dict:
        """Charge configuration sources enrichies avec sources chinoises complètes"""
        return {
            "chinese_sources": [
                # ✅ ENTREPRISES & LABS IA MAJEURS
                {
                    "name": "机器之心 (Machine Heart)",
                    "url": "https://www.jiqizhixin.com/rss",
                    "category": "ai-news",
                    "language": "zh-CN",
                    "priority": "high",
                    "keywords": ["ai", "machine-learning", "deep-learning", "china"]
                },
                {
                    "name": "百度 AI",
                    "url": "https://ai.baidu.com/rss/",
                    "category": "ai-platform",
                    "language": "zh-CN",
                    "priority": "high",
                    "keywords": ["baidu", "ai", "ernie", "apollo", "paddlepaddle"]
                },
                {
                    "name": "腾讯 AI Lab",
                    "url": "https://ai.tencent.com/rss/",
                    "category": "ai-research",
                    "language": "zh-CN",
                    "priority": "high",
                    "keywords": ["tencent", "ai", "gaming", "wechat", "social"]
                },
                {
                    "name": "阿里巴巴 DAMO Academy",
                    "url": "https://damo.alibaba.com/news/rss",
                    "category": "ai-research",
                    "language": "zh-CN",
                    "priority": "high",
                    "keywords": ["alibaba", "damo", "nlp", "computer-vision"]
                },
                {
                    "name": "字节跳动 AI Lab",
                    "url": "https://ailab.bytedance.com/rss/",
                    "category": "ai-research",
                    "language": "zh-CN",
                    "priority": "high",
                    "keywords": ["bytedance", "tiktok", "recommendation", "ai"]
                },
                {
                    "name": "商汤科技 (SenseTime)",
                    "url": "https://www.sensetime.com/news/rss",
                    "category": "computer-vision",
                    "language": "zh-CN",
                    "priority": "high",
                    "keywords": ["sensetime", "vision", "autonomous-driving", "cv"]
                },
                {
                    "name": "旷视科技 (Megvii Face++)",
                    "url": "https://www.megvii.com/news/rss",
                    "category": "computer-vision",
                    "language": "zh-CN",
                    "priority": "high",
                    "keywords": ["megvii", "face", "smart-city", "iot"]
                },
                {
                    "name": "科大讯飞 (iFlytek)",
                    "url": "https://www.iflytek.com/news/rss",
                    "category": "speech-ai",
                    "language": "zh-CN",
                    "priority": "high",
                    "keywords": ["iflytek", "speech", "voice", "recognition"]
                },

                # ✅ TECH NEWS & BUSINESS
                {
                    "name": "36氪 (36Kr)",
                    "url": "https://www.36kr.com/rss",
                    "category": "tech-news",
                    "language": "zh-CN",
                    "priority": "high",
                    "keywords": ["startup", "venture", "tech", "business"]
                },
                {
                    "name": "TechNode",
                    "url": "https://technode.com/feed/",
                    "category": "tech-news",
                    "language": "zh-CN",
                    "priority": "medium",
                    "keywords": ["china", "tech", "startup", "innovation"]
                },
                {
                    "name": "PingWest",
                    "url": "https://www.pingwest.com/feed",
                    "category": "tech-news",
                    "language": "zh-CN",
                    "priority": "medium",
                    "keywords": ["tech", "analysis", "trends", "china"]
                },
                {
                    "name": "雷锋网 (Leiphone)",
                    "url": "https://www.leiphone.com/feed",
                    "category": "ai-tech",
                    "language": "zh-CN",
                    "priority": "medium",
                    "keywords": ["ai", "tech", "innovation", "analysis"]
                },
                {
                    "name": "钛媒体 (TMTPost)",
                    "url": "https://www.tmtpost.com/rss",
                    "category": "tech-business",
                    "language": "zh-CN",
                    "priority": "medium",
                    "keywords": ["tmt", "media", "business", "tech"]
                },
                {
                    "name": "创业邦 (Cyzone)",
                    "url": "https://www.cyzone.cn/rss",
                    "category": "startup",
                    "language": "zh-CN",
                    "priority": "medium",
                    "keywords": ["startup", "entrepreneur", "investment", "innovation"]
                },
                {
                    "name": "i黑马 (iHeima)",
                    "url": "https://www.iheima.com/rss",
                    "category": "startup",
                    "language": "zh-CN",
                    "priority": "medium",
                    "keywords": ["startup", "business", "entrepreneur", "model"]
                },

                # ✅ RECHERCHE & ACADÉMIQUE
                {
                    "name": "AI科技评论 (AI Tech Review)",
                    "url": "https://www.leiphone.com/category/academic/rss",
                    "category": "research",
                    "language": "zh-CN",
                    "priority": "medium",
                    "keywords": ["research", "academic", "papers", "ai"]
                },
                {
                    "name": "PaperWeekly",
                    "url": "https://www.paperweekly.site/rss",
                    "category": "research",
                    "language": "zh-CN",
                    "priority": "medium",
                    "keywords": ["papers", "weekly", "research", "ml"]
                },
                {
                    "name": "AI研习社 (AI Study Society)",
                    "url": "https://ai.yanxishe.com/rss",
                    "category": "research",
                    "language": "zh-CN",
                    "priority": "low",
                    "keywords": ["community", "study", "tutorials", "ai"]
                },

                # ✅ InfoQ & Aggregators
                {
                    "name": "InfoQ China AI",
                    "url": "https://www.infoq.cn/ai/rss",
                    "category": "tech-news",
                    "language": "zh-CN",
                    "priority": "medium",
                    "keywords": ["infoq", "development", "architecture", "ai"]
                },
                {
                    "name": "36氪 AI专栏",
                    "url": "https://36kr.com/newsflashes/rss?tag=AI",
                    "category": "ai-news",
                    "language": "zh-CN",
                    "priority": "medium",
                    "keywords": ["36kr", "ai", "startup", "news"]
                },
                {
                    "name": "虎嗅 AI",
                    "url": "https://www.huxiu.com/rss/ai.xml",
                    "category": "ai-business",
                    "language": "zh-CN",
                    "priority": "medium",
                    "keywords": ["huxiu", "business", "analysis", "ai"]
                },

                # ✅ MARKETING & AUTOMATION (OPML sources)
                {
                    "name": "SocialBeta",
                    "url": "https://www.socialbeta.com/rss",
                    "category": "marketing",
                    "language": "zh-CN",
                    "priority": "low",
                    "keywords": ["marketing", "social", "digital", "automation"]
                },
                {
                    "name": "梅花网 (Meihua)",
                    "url": "https://www.meihua.info/rss",
                    "category": "marketing",
                    "language": "zh-CN",
                    "priority": "low",
                    "keywords": ["marketing", "creative", "advertising", "brand"]
                },
                {
                    "name": "MarketingChina",
                    "url": "https://www.marketingchina.com/feed",
                    "category": "marketing",
                    "language": "zh-CN",
                    "priority": "low",
                    "keywords": ["marketing", "china", "digital", "strategy"]
                }
            ],
            "fallback_chinese_feeds": [
                # Fallbacks si RSS direct non disponible
                "https://rsshub.app/jiqizhixin/ai",
                "https://rsshub.app/csdn/blog/FL63Zv9Zou86950w",
                "https://rsshub.app/qbitai",
                "https://rsshub.app/infoq/topic/ai"
            ],
            "existing_sources": [
                # Sources existantes maintenues
                "https://korben.info/feed",
                "https://blog.crewai.com/rss/",
                "https://www.marktechpost.com/feed/",
                "https://deepmind.google/blog/rss.xml"
            ],
            # Mapping catégories → sources RSS
            "category_sources": {
                "ai_ml": [
                    {"name": "CrewAI Blog", "url": "https://blog.crewai.com/rss/", "language": "en"},
                    {"name": "MarktechPost", "url": "https://www.marktechpost.com/feed/", "language": "en"},
                    {"name": "DeepMind", "url": "https://deepmind.google/blog/rss.xml", "language": "en"},
                    {"name": "OpenAI", "url": "https://openai.com/blog/rss.xml", "language": "en"}
                ],
                "cloud_computing": [
                    {"name": "AWS Blog", "url": "https://aws.amazon.com/blogs/aws/feed/", "language": "en"},
                    {"name": "Azure Blog", "url": "https://azure.microsoft.com/en-us/blog/feed/", "language": "en"}
                ],
                "security": [
                    {"name": "Krebs on Security", "url": "https://krebsonsecurity.com/feed/", "language": "en"},
                    {"name": "SANS ISC", "url": "https://isc.sans.edu/rssfeed.xml", "language": "en"}
                ],
                "software_dev": [
                    {"name": "Korben", "url": "https://korben.info/feed", "language": "fr"},
                    {"name": "Dev.to", "url": "https://dev.to/feed", "language": "en"}
                ],
                "hardware_tech": [
                    {"name": "AnandTech", "url": "https://www.anandtech.com/rss/", "language": "en"}
                ]
            }
        }

    def check_article_uniqueness(self, title: str, content: str = "", source_url: str = "") -> bool:
        """
        Vérifie unicité avec système anti-doublons
        Returns: True si unique, False si doublon
        """
        is_duplicate, reason = self.anti_dup.is_duplicate(title, content, source_url)

        if is_duplicate:
            print(f"🚫 Article rejeté: {reason}")
            return False

        return True

    def fetch_standard_content(self, source: Dict) -> List[Dict]:
        """Récupère contenu depuis sources standards (EN/FR)"""
        articles = []

        try:
            print(f"📰 Récupération: {source['name']}")

            headers = {'User-Agent': 'Mozilla/5.0 (compatible; AgentBnZo/1.0)'}
            response = requests.get(source['url'], headers=headers, timeout=30)

            if response.status_code != 200:
                print(f"  ⚠️  HTTP {response.status_code}")
                return articles

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.content, 'xml')
            items = soup.find_all('item') or soup.find_all('entry')

            for item in items[:5]:  # Limite 5 par source
                try:
                    title_elem = item.find('title')
                    link_elem = item.find('link')
                    desc_elem = item.find('description') or item.find('summary')

                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    link = link_elem.get_text(strip=True) if link_elem else None
                    if not link and link_elem and hasattr(link_elem, 'get'):
                        link = link_elem.get('href')
                    description = desc_elem.get_text(strip=True) if desc_elem else ""

                    if not self.check_article_uniqueness(title, description, link):
                        continue

                    article = {
                        'title': title,
                        'description': description,
                        'link': link,
                        'source': source['name'],
                        'language': source.get('language', 'en'),
                        'category': source.get('category', 'general')
                    }

                    articles.append(article)

                except Exception as e:
                    print(f"  ⚠️  Parsing error: {e}")
                    continue

        except Exception as e:
            print(f"  ❌ Fetch error: {e}")

        return articles

    def fetch_chinese_content(self, source: Dict) -> List[Dict]:
        """Récupère contenu depuis sources chinoises avec gestion encoding"""
        articles = []

        try:
            print(f"🇨🇳 Récupération: {source['name']}")

            # Headers pour sources chinoises
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/rss+xml, application/xml, text/xml',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Charset': 'utf-8'
            }

            response = requests.get(source['url'], headers=headers, timeout=30)
            response.encoding = 'utf-8'  # Force UTF-8 pour chinois

            if response.status_code != 200:
                print(f"⚠️ Erreur HTTP {response.status_code} pour {source['name']}")
                return articles

            # Parse RSS/XML
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.content, 'xml')

            # Recherche items RSS
            items = soup.find_all('item') or soup.find_all('entry')

            for item in items[:5]:  # Limite 5 articles par source
                try:
                    title_elem = item.find('title')
                    link_elem = item.find('link')
                    desc_elem = item.find('description') or item.find('summary')

                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    # Correction: extraire d'abord le texte, puis tester l'attribut href (pour flux Atom)
                    link = link_elem.get_text(strip=True) if link_elem else None
                    if not link and link_elem and hasattr(link_elem, 'get'):
                        link = link_elem.get('href')
                    description = desc_elem.get_text(strip=True) if desc_elem else ""

                    # Vérification unicité
                    if not self.check_article_uniqueness(title, description, link):
                        continue

                    article = {
                        'title': title,
                        'description': description,
                        'link': link,
                        'source': source['name'],
                        'language': source['language'],
                        'category': source['category'],
                        'keywords': source['keywords']
                    }

                    articles.append(article)
                    print(f"✅ Article chinois ajouté: {title[:50]}...")

                except Exception as e:
                    print(f"⚠️ Erreur parsing article: {e}")
                    continue

        except Exception as e:
            print(f"❌ Erreur récupération {source['name']}: {e}")

        return articles

    def process_article_with_translation(self, article: Dict) -> Optional[Dict]:
        """Traite article avec traduction si nécessaire"""

        title = article['title']
        description = article['description']
        language = article.get('language', 'en')

        # Double vérification anti-doublons avec contenu complet
        if not self.check_article_uniqueness(title, description, article['link']):
            return None

        processed_content = self._generate_multilingual_content(article)

        if not processed_content:
            return None

        # Enregistrement dans anti-doublons
        filename = self._generate_filename(title)
        self.anti_dup.register_article(
            title=title,
            content=processed_content,
            source_url=article['link'],
            filename=filename
        )

        return {
            'title': title,
            'content': processed_content,
            'filename': filename,
            'source_info': article,
            'generated_at': datetime.now().isoformat()
        }

    def _generate_multilingual_content(self, article: Dict) -> Optional[str]:
        """Génère contenu avec support multilingue"""

        try:
            # Template HTML moderne
            template = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{article['title']} - Blog AgentBnZo</title>
    <style>
        body {{ font-family: 'Inter', sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 2rem; border-radius: 10px; margin-bottom: 2rem; }}
        .content {{ background: white; padding: 2rem; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .meta {{ color: #666; margin-bottom: 1rem; }}
        .flag {{ font-size: 1.5em; margin-right: 0.5rem; }}
        h1 {{ margin: 0; font-size: 2rem; }}
        p {{ line-height: 1.6; margin-bottom: 1rem; }}
    </style>
</head>
<body>
    <header class="header">
        <h1>🤖 Blog AgentBnZo</h1>
        <p>Intelligence Artificielle & Écosystème Multi-Agents</p>
    </header>

    <article class="content">
        <div class="meta">
            <span class="flag">{'🇨🇳' if article['language'] == 'zh-CN' else '🌍'}</span>
            <strong>Source:</strong> {article['source']} |
            <strong>Catégorie:</strong> {article['category']} |
            <strong>Date:</strong> {datetime.now().strftime('%d/%m/%Y')}
        </div>

        <h2>{article['title']}</h2>

        <div class="description">
            <p>{article['description']}</p>
        </div>

        <div class="original-source">
            <p><strong>🔗 Source originale:</strong>
            <a href="{article['link']}" target="_blank">{article['link']}</a></p>
        </div>

        <div class="keywords">
            <p><strong>🏷️ Mots-clés:</strong> {', '.join(article['keywords'])}</p>
        </div>
    </article>
</body>
</html>"""

            return template

        except Exception as e:
            print(f"❌ Erreur génération contenu: {e}")
            return None

    def _generate_filename(self, title: str) -> str:
        """Génère nom de fichier unique"""
        # Nettoyage titre
        clean_title = title.replace(' ', '-').replace('/', '-')
        clean_title = ''.join(c for c in clean_title if c.isalnum() or c in '-_')[:50]

        # Date + hash pour unicité
        date_str = datetime.now().strftime('%Y-%m-%d')
        title_hash = hashlib.md5(title.encode('utf-8')).hexdigest()[:8]

        return f"{date_str}-{clean_title}-{title_hash}.html"

    def run_enhanced_feed(self):
        """Lance le processus de feed enrichi avec configuration catégories"""
        print("🚀 Démarrage Enhanced Blog Feeder avec système de catégories")

        # Affichage configuration active
        enabled_cats = self.category_config.get('enabled_categories', {})
        active_count = sum(1 for cat in enabled_cats.values() if cat.get('enabled', False))
        print(f"📂 Catégories actives: {active_count}/{len(enabled_cats)}")

        # Statistiques initiales
        initial_stats = self.anti_dup.get_duplicate_stats()
        print(f"📊 Articles existants: {initial_stats['total_articles']}")

        all_articles = []
        sources_processed = 0

        # Traitement sources chinoises (si catégorie activée)
        china_config = enabled_cats.get('china_tech_ai', {})
        if china_config.get('enabled', False) and china_config.get('non_youtube_sources', {}).get('enabled', False):
            print("\n🇨🇳 Traitement catégorie China Tech AI...")
            for source in self.sources_config['chinese_sources']:
                try:
                    articles = self.fetch_chinese_content(source)
                    all_articles.extend(articles)
                    sources_processed += 1
                    print(f"  ✅ {source['name']}: {len(articles)} articles")
                except Exception as e:
                    print(f"  ❌ Erreur {source['name']}: {e}")
        else:
            print("\n⏭️  Catégorie China Tech AI désactivée")

        # Traitement autres catégories (AI/ML, Cloud, Security, etc.)
        category_sources = self.sources_config.get('category_sources', {})
        for category_name, sources_list in category_sources.items():
            cat_config = enabled_cats.get(category_name, {})

            if cat_config.get('enabled', False) and cat_config.get('non_youtube_sources', {}).get('enabled', False):
                print(f"\n📂 Traitement catégorie {category_name.replace('_', ' ').upper()}...")
                for source in sources_list:
                    try:
                        articles = self.fetch_standard_content(source)
                        all_articles.extend(articles)
                        sources_processed += 1
                        print(f"  ✅ {source['name']}: {len(articles)} articles")
                    except Exception as e:
                        print(f"  ❌ Erreur {source['name']}: {e}")
            else:
                print(f"\n⏭️  Catégorie {category_name} désactivée")

        # Traitement et sauvegarde
        saved_count = 0
        for article in all_articles:
            processed = self.process_article_with_translation(article)
            if processed and self._save_article(processed):
                saved_count += 1

        # Statistiques finales
        final_stats = self.anti_dup.get_duplicate_stats()
        print(f"\n📈 Résultats:")
        print(f"  • Sources traitées: {sources_processed}")
        print(f"  • Articles récupérés: {len(all_articles)}")
        print(f"  • Articles sauvegardés: {saved_count}")
        print(f"  • Total en base: {final_stats['total_articles']}")

    def _save_article(self, processed_article: Dict) -> bool:
        """Sauvegarde article avec vérification finale"""
        try:
            output_path = self.output_dir / processed_article['filename']

            if output_path.exists():
                print(f"⚠️ Fichier existant: {processed_article['filename']}")
                return False

            output_path.write_text(processed_article['content'], encoding='utf-8')
            print(f"💾 Sauvegardé: {processed_article['filename']}")
            return True

        except Exception as e:
            print(f"❌ Erreur sauvegarde: {e}")
            return False

def main():
    """Point d'entrée principal"""
    feeder = EnhancedBlogFeeder()
    feeder.run_enhanced_feed()

if __name__ == "__main__":
    main()