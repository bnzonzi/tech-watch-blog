#!/usr/bin/env python3
"""
Générateur de contenu d'articles avec Gemini 2.5 Flash
Rédaction française première personne, focus outils AgentBnZo
"""

import os
import sys
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re

# Imports Google Gemini
try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
except ImportError:
    print("❌ google-generativeai non installé. Utilisez: uv add google-generativeai")
    sys.exit(1)

# Import configuration locale
sys.path.append(str(Path(__file__).parent.parent))
from config.blog_config import (
    GEMINI_MODEL, GEMINI_API_KEY_ENV, GEMINI_TEMPERATURE, GEMINI_MAX_TOKENS,
    ARTICLE_TEMPLATES, BLOG_CATEGORIES, BLOG_CONFIG
)

@dataclass
class GeneratedArticle:
    """Article généré avec métadonnées"""
    title: str
    content: str
    category: str
    template_type: str
    source_articles: List[str]
    generation_metadata: Dict[str, Any]
    filename: str
    frontmatter: Dict[str, Any]

class GeminiContentGenerator:
    """
    Générateur d'articles de blog avec Gemini 2.5 Flash
    Expertise technique personnalisée pour AgentBnZo
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._setup_gemini()
        self._load_prompts()

    def _setup_gemini(self):
        """Configure l'API Gemini"""
        api_key = os.getenv(GEMINI_API_KEY_ENV)
        if not api_key:
            raise ValueError(f"Variable d'environnement manquante: {GEMINI_API_KEY_ENV}")

        genai.configure(api_key=api_key)

        # Configuration du modèle
        generation_config = {
            "temperature": GEMINI_TEMPERATURE,
            "max_output_tokens": GEMINI_MAX_TOKENS,
            "top_p": 0.95,
            "top_k": 64,
        }

        # Configuration sécurité (permissive pour contenu technique)
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }

        self.model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            generation_config=generation_config,
            safety_settings=safety_settings,
            system_instruction=self._get_system_instruction()
        )

        self.logger.info(f"Gemini {GEMINI_MODEL} configuré")

    def _get_system_instruction(self) -> str:
        """Instruction système pour Gemini"""
        return f"""Tu es un expert technique français spécialisé dans l'intelligence artificielle collaborative et les outils du projet AgentBnZo.

CONTEXTE PROJET AGENTBNZO:
- Workspace multi-agents CrewAI spécialisé en IA collaborative
- Stack: Python, CrewAI, UV, SQLite, Telegram, Gemini
- Crews: security_defense, tech_watch, llm_evaluation, infra_devops, etc.
- Focus: automation, monitoring, sécurité défensive, formation IA

STYLE D'ÉCRITURE REQUIS:
- Première personne obligatoire : **je** ou **nous** (jamais voix impersonnelle pour le récit principal)
- **je** : retour perso, test solo, erreur vécue ("Je teste", "J'utilise", "Mon expérience avec")
- **nous** : flotte agents ML / labo AgentBnZo ("Nous avons branché", "Chez nous on isole")
- Interdit : ton neutre ("il est recommandé"), 3e personne éditoriale, voix agence ou marketing
- Ton expert mais accessible, retour d'expérience authentique
- Approche pratique avec exemples concrets AgentBnZo
- Éviter le marketing, privilégier l'aspect technique

STRUCTURE ARTICLES:
- Introduction personnelle et contexte
- Explication technique avec exemples pratiques
- Retour d'expérience sur l'implémentation
- Code snippets et configurations quand pertinent
- Conclusion avec perspectives et apprentissages

CONTRAINTES:
- Articles 800-1500 mots
- Intégrer outils/patterns existants AgentBnZo
- Exemples concrets d'utilisation
- Liens vers documentation officielle
- Éviter répétitions et généralités

Tu génères du contenu de qualité professionnelle pour le blog tech AgentBnZo."""

    def _load_prompts(self):
        """Charge les templates de prompts par type d'article"""
        self.prompts = {
            "tutorial": """
# GÉNÉRATION TUTORIEL TECHNIQUE

Génère un tutoriel détaillé en français sur le sujet: {topic}

## SOURCES À ANALYSER:
{source_summaries}

## TEMPLATE TUTORIEL:
1. **Introduction personnelle** (150 mots)
   - Mon contexte et pourquoi ce tutoriel
   - Problème technique rencontré dans AgentBnZo

2. **Prérequis et préparation** (200 mots)
   - Outils AgentBnZo nécessaires
   - Configuration environment

3. **Étapes détaillées** (600-800 mots)
   - Implémentation step-by-step
   - Code snippets avec AgentBnZo
   - Pièges à éviter (retour d'expérience)

4. **Validation et tests** (200 mots)
   - Comment vérifier le fonctionnement
   - Métriques de performance

5. **Conclusion et perspectives** (150 mots)
   - Apprentissages personnels
   - Améliorations possibles

## CONTRAINTES:
- Première personne obligatoire : **je** ou **nous** (jamais voix impersonnelle pour le récit principal)
- Utiliser "je", "mon expérience", "j'ai testé" ou "nous", "notre flotte", "chez nous" selon le contexte
- Exemples concrets avec outils AgentBnZo existants
- Code Python/bash/yaml quand pertinent
- Liens documentation officielle
- 1000-1200 mots total

Génère l'article complet avec cette structure.
""",

            "best_practice": """
# GÉNÉRATION BEST PRACTICE

Rédige un article best practice en français sur: {topic}

## SOURCES D'INSPIRATION:
{source_summaries}

## TEMPLATE BEST PRACTICE:
1. **Contexte et enjeux** (200 mots)
   - Problématique rencontrée dans mes projets AgentBnZo
   - Impact et importance

2. **Méthodologie développée** (400 mots)
   - Approche technique adoptée
   - Patterns et conventions AgentBnZo
   - Comparaison avec alternatives

3. **Implémentation concrète** (500 mots)
   - Exemples de code et configuration
   - Integration avec stack AgentBnZo
   - Metrics et monitoring

4. **Retour d'expérience** (300 mots)
   - Gains observés en production
   - Difficultés rencontrées
   - Recommandations

5. **Perspectives d'évolution** (100 mots)
   - Améliorations prévues
   - Évolutions du pattern

## STYLE:
- Première personne obligatoire : **je** ou **nous** (jamais voix impersonnelle pour le récit principal)
- Retour d'expérience authentique première personne
- Focus pragmatique et opérationnel
- Exemples tirés de cas réels AgentBnZo
- Recommandations actionables

Génère l'article complet (1200-1500 mots).
""",

            "analysis": """
# GÉNÉRATION ANALYSE TECHNIQUE

Produis une analyse technique approfondie en français sur: {topic}

## DONNÉES SOURCE:
{source_summaries}

## STRUCTURE ANALYSE:
1. **Problématique technique** (200 mots)
   - Question ou challenge identifié
   - Contexte AgentBnZo concerné

2. **Investigation et méthodologie** (400 mots)
   - Approche d'analyse adoptée
   - Outils et métriques utilisés
   - Tests effectués

3. **Résultats et findings** (500 mots)
   - Données collectées
   - Patterns identifiés
   - Comparaisons benchmark

4. **Implications pratiques** (300 mots)
   - Impact sur architecture AgentBnZo
   - Recommandations d'implémentation
   - Trade-offs identifiés

5. **Conclusion et perspectives** (150 mots)
   - Synthèse des apprentissages
   - Axes d'investigation futurs

## EXIGENCES:
- Première personne obligatoire : **je** ou **nous** (jamais voix impersonnelle pour le récit principal)
- Analyse objective et factuelle (toujours à la 1re personne)
- Métriques et données quantitatives
- Liens avec écosystème AgentBnZo
- Perspective technique experte

Article total: 1300-1500 mots.
""",

            "innovation": """
# GÉNÉRATION ARTICLE INNOVATION

Crée un article innovation en français sur: {topic}

## CONTEXTE INNOVATION:
{source_summaries}

## TEMPLATE INNOVATION:
1. **Vision et concept** (250 mots)
   - Innovation identifiée ou développée
   - Potentiel pour AgentBnZo
   - Disruption apportée

2. **Implémentation expérimentale** (450 mots)
   - Proof of concept réalisé
   - Integration stack technique
   - Défis techniques surmontés

3. **Tests et validation** (400 mots)
   - Protocole de test
   - Résultats obtenus
   - Comparaisons avec approche classique

4. **Impact et applications** (300 mots)
   - Use cases AgentBnZo identifiés
   - Bénéfices mesurés
   - Scalabilité

5. **Roadmap et perspectives** (150 mots)
   - Évolutions prévues
   - Recherches à approfondir
   - Vision long terme

## STYLE:
- Première personne obligatoire : **je** ou **nous** (jamais voix impersonnelle pour le récit principal)
- Exploration créative mais rigoureuse
- Équilibre innovation/pragmatisme
- Exemples concrets d'expérimentation
- Perspective prospective

Article 1400-1550 mots.
"""
        }

    def generate_article_from_analysis(self, analyzed_articles: List[Any]) -> GeneratedArticle:
        """
        Génère un article à partir d'articles analysés
        """
        if not analyzed_articles:
            raise ValueError("Aucun article analysé fourni")

        # Sélectionner l'article principal (meilleur score)
        main_article = analyzed_articles[0]
        template_type = main_article.template_type
        category = main_article.category

        # Préparer le contexte
        topic = self._extract_topic(main_article)
        source_summaries = self._prepare_source_summaries(analyzed_articles[:3])

        # Générer le contenu
        content = self._generate_content(topic, source_summaries, template_type)

        # Créer métadonnées
        metadata = self._create_article_metadata(
            main_article, analyzed_articles, template_type, category
        )

        # Générer filename
        filename = self._generate_filename(topic, category, template_type)

        return GeneratedArticle(
            title=metadata["title"],
            content=content,
            category=category,
            template_type=template_type,
            source_articles=[art.url for art in analyzed_articles],
            generation_metadata=metadata,
            filename=filename,
            frontmatter=self._create_frontmatter(metadata, category)
        )

    def _extract_topic(self, article: Any) -> str:
        """Extrait le topic principal de l'article"""
        # Combiner titre et mots-clés codebase
        topic_elements = [article.title]

        if article.codebase_matches:
            topic_elements.append(f"avec {', '.join(article.codebase_matches[:3])}")

        if article.tech_keywords:
            topic_elements.append(f"({', '.join(article.tech_keywords[:2])})")

        return " ".join(topic_elements)

    def _prepare_source_summaries(self, articles: List[Any]) -> str:
        """Prépare le résumé des articles sources"""
        summaries = []
        for i, article in enumerate(articles, 1):
            summary = f"""
Article {i}:
- Titre: {article.title}
- Source: {article.source_name}
- Résumé: {article.summary[:200]}...
- Outils AgentBnZo: {', '.join(article.codebase_matches) if article.codebase_matches else 'Aucun'}
- Mots-clés tech: {', '.join(article.tech_keywords[:5]) if article.tech_keywords else 'Aucun'}
"""
            summaries.append(summary.strip())

        return "\n\n".join(summaries)

    def _generate_content(self, topic: str, source_summaries: str, template_type: str) -> str:
        """Génère le contenu avec Gemini"""
        prompt_template = self.prompts.get(template_type, self.prompts["analysis"])
        prompt = prompt_template.format(
            topic=topic,
            source_summaries=source_summaries
        )

        try:
            self.logger.info(f"Génération contenu Gemini pour: {topic[:50]}...")
            response = self.model.generate_content(prompt)

            if not response.text:
                raise Exception("Réponse Gemini vide")

            content = response.text.strip()
            self.logger.info(f"Contenu généré: {len(content)} caractères")

            return content

        except Exception as e:
            self.logger.error(f"Erreur génération Gemini: {e}")
            # Fallback avec contenu minimal
            return self._generate_fallback_content(topic, template_type)

    def _generate_fallback_content(self, topic: str, template_type: str) -> str:
        """Génère un contenu de fallback en cas d'erreur Gemini"""
        return f"""# {topic}

*[Article généré automatiquement - Mode fallback]*

## Introduction

Dans le cadre de mes travaux sur AgentBnZo, j'ai eu l'occasion d'explorer {topic}.
Cet article présente mon retour d'expérience et les enseignements tirés.

## Contexte technique

L'intégration de cette technologie dans l'écosystème AgentBnZo présente des défis
intéressants, notamment en termes d'architecture multi-agents et de performance.

## Implémentation

Les tests réalisés montrent des résultats prometteurs pour l'automatisation
et l'optimisation de nos workflows CrewAI.

## Conclusion

Cette exploration ouvre de nouvelles perspectives pour l'évolution du projet AgentBnZo.

---

*Article généré automatiquement par le système de blog AgentBnZo*
"""

    def _create_article_metadata(self, main_article: Any, all_articles: List[Any],
                                template_type: str, category: str) -> Dict[str, Any]:
        """Crée les métadonnées complètes de l'article"""

        # Générer titre optimisé
        title_prefix = ARTICLE_TEMPLATES[template_type]["title_prefix"]
        clean_title = self._clean_title(main_article.title)
        title = f"{title_prefix} {clean_title}"

        return {
            "title": title,
            "template_type": template_type,
            "category": category,
            "source_count": len(all_articles),
            "main_source": main_article.source_name,
            "codebase_tools": list(set([tool for art in all_articles for tool in art.codebase_matches])),
            "tech_keywords": list(set([kw for art in all_articles for kw in art.tech_keywords])),
            "relevance_score": main_article.relevance_score,
            "generation_timestamp": datetime.now().isoformat(),
            "model_used": GEMINI_MODEL,
            "estimated_reading_time": self._estimate_reading_time(1200)  # Moyenne
        }

    def _clean_title(self, title: str) -> str:
        """Nettoie et optimise le titre"""
        # Supprimer caractères spéciaux
        title = re.sub(r'[^\w\s\-àáâäéèêëíìîïóòôöúùûüýÿñç]', '', title)

        # Limiter longueur
        if len(title) > 60:
            title = title[:57] + "..."

        return title.strip()

    def _generate_filename(self, topic: str, category: str, template_type: str) -> str:
        """Génère le nom de fichier pour l'article"""
        # Slug du topic
        slug = re.sub(r'[^\w\s-]', '', topic.lower())
        slug = re.sub(r'[-\s]+', '-', slug)[:50]

        # Date
        date_str = datetime.now().strftime("%Y-%m-%d")

        return f"{date_str}-{category}-{template_type}-{slug}.md"

    def _create_frontmatter(self, metadata: Dict[str, Any], category: str) -> Dict[str, Any]:
        """Crée le frontmatter Jekyll/Hugo"""
        return {
            "title": metadata["title"],
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "categories": [category],
            "tags": metadata["tech_keywords"][:5],
            "author": BLOG_CONFIG["author"],
            "template_type": metadata["template_type"],
            "codebase_tools": metadata["codebase_tools"],
            "reading_time": metadata["estimated_reading_time"],
            "generated": True,
            "sources": metadata["source_count"]
        }

    def _estimate_reading_time(self, word_count: int) -> str:
        """Estime le temps de lecture (250 mots/min)"""
        minutes = max(1, round(word_count / 250))
        return f"{minutes} min"

    def save_article(self, article: GeneratedArticle, output_dir: Optional[Path] = None) -> Path:
        """Sauvegarde l'article avec frontmatter"""
        if not output_dir:
            from config.blog_config import BLOG_ROOT
            output_dir = BLOG_ROOT / "content" / "articles"

        output_dir.mkdir(parents=True, exist_ok=True)
        file_path = output_dir / article.filename

        # Construire contenu final avec frontmatter
        frontmatter_yaml = "---\n"
        for key, value in article.frontmatter.items():
            if isinstance(value, list):
                frontmatter_yaml += f"{key}:\n"
                for item in value:
                    frontmatter_yaml += f"  - {item}\n"
            else:
                frontmatter_yaml += f"{key}: {value}\n"
        frontmatter_yaml += "---\n\n"

        full_content = frontmatter_yaml + article.content

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(full_content)

        self.logger.info(f"Article sauvegardé: {file_path}")
        return file_path

def main():
    """Test du générateur Gemini"""
    logging.basicConfig(level=logging.INFO)

    # Mock article pour test
    from types import SimpleNamespace
    mock_article = SimpleNamespace(
        title="Test Gemini 2.5 Flash avec CrewAI",
        summary="Exploration des capacités de Gemini pour l'automation",
        source_name="Test",
        template_type="tutorial",
        codebase_matches=["crewai", "gemini"],
        tech_keywords=["ai", "automation"],
        relevance_score=0.9,
        url="https://test.com"
    )

    generator = GeminiContentGenerator()

    try:
        article = generator.generate_article_from_analysis([mock_article])
        output_path = generator.save_article(article)
        print(f"✅ Article généré: {output_path}")
        print(f"Titre: {article.title}")
        print(f"Taille: {len(article.content)} caractères")
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    main()