#!/usr/bin/env python3
"""
Filtre de qualité du contenu pour validation pertinence
Validation croisée avec la codebase AgentBnZo et critères qualité
"""

import os
import sys
import json
import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import hashlib

# Configuration locale
sys.path.append(str(Path(__file__).parent.parent))
from config.blog_config import (
    BLOG_ROOT, BLOG_CATEGORIES, CONTENT_FILTER_CONFIG,
    ARTICLE_TEMPLATES
)

@dataclass
class QualityScore:
    """Score de qualité détaillé"""
    total_score: float
    relevance_score: float
    content_quality_score: float
    codebase_alignment_score: float
    technical_depth_score: float
    originality_score: float
    issues: List[str]
    recommendations: List[str]

@dataclass
class ContentValidation:
    """Résultat de validation du contenu"""
    is_valid: bool
    quality_score: QualityScore
    filtered_content: str
    metadata: Dict[str, Any]
    validation_notes: List[str]

class ContentQualityFilter:
    """
    Filtre de qualité avancé pour validation du contenu
    Vérifie la pertinence, la qualité technique et l'alignement AgentBnZo
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._load_codebase_knowledge()
        self._setup_quality_patterns()
        self._load_duplicate_detector()

    def _load_codebase_knowledge(self):
        """Charge la connaissance de la codebase AgentBnZo"""
        self.codebase_knowledge = {
            'tools': set(),
            'concepts': set(),
            'technologies': set(),
            'patterns': []
        }

        # Analyser la structure AgentBnZo pour extraction automatique
        agentbnzo_root = Path("/media/raid10to/projets")
        if agentbnzo_root.exists():
            self._extract_codebase_knowledge(agentbnzo_root)

        # Ajouter connaissances statiques
        self._add_static_knowledge()

    def _extract_codebase_knowledge(self, root_path: Path):
        """Extrait automatiquement la connaissance de la codebase"""
        try:
            # Scanner les crews pour identifier outils et patterns
            crews_dir = root_path / "crews"
            if crews_dir.exists():
                for crew_dir in crews_dir.iterdir():
                    if crew_dir.is_dir() and not crew_dir.name.startswith('.'):
                        crew_name = crew_dir.name.replace('_crew', '')
                        self.codebase_knowledge['tools'].add(crew_name)

                        # Scanner les fichiers Python pour imports et classes
                        self._scan_python_files(crew_dir)

            # Scanner scripts racine
            for py_file in root_path.glob("*.py"):
                self._scan_python_files(py_file.parent, [py_file])

        except Exception as e:
            self.logger.warning(f"Erreur extraction codebase: {e}")

    def _scan_python_files(self, directory: Path, files: Optional[List[Path]] = None):
        """Scanne les fichiers Python pour extraire concepts techniques"""
        if files is None:
            files = list(directory.rglob("*.py"))

        for py_file in files[:20]:  # Limiter pour performance
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # Extraire imports
                imports = re.findall(r'(?:from|import)\s+([a-zA-Z_][a-zA-Z0-9_\.]*)', content)
                for imp in imports:
                    if any(tech in imp.lower() for tech in ['crewai', 'gemini', 'telegram', 'docker']):
                        self.codebase_knowledge['technologies'].add(imp.split('.')[0])

                # Extraire classes et fonctions importantes
                classes = re.findall(r'class\s+([A-Z][a-zA-Z0-9_]*)', content)
                functions = re.findall(r'def\s+([a-z_][a-zA-Z0-9_]*)', content)

                self.codebase_knowledge['concepts'].update(classes[:5])
                self.codebase_knowledge['concepts'].update(functions[:5])

            except Exception:
                continue

    def _add_static_knowledge(self):
        """Ajoute la connaissance statique AgentBnZo"""
        static_tools = {
            'crewai', 'gemini', 'telegram', 'docker', 'sqlite', 'nginx',
            'ollama', 'fabric', 'security_defense', 'tech_watch',
            'llm_evaluation', 'infra_devops', 'formation_pedagogy'
        }

        static_concepts = {
            'multi_agent', 'orchestration', 'automation', 'monitoring',
            'security_audit', 'performance_optimization', 'ai_training',
            'content_generation', 'workflow_management', 'api_integration'
        }

        static_technologies = {
            'python', 'uv', 'fastapi', 'jinja2', 'yaml', 'json',
            'markdown', 'html', 'css', 'javascript', 'bash'
        }

        self.codebase_knowledge['tools'].update(static_tools)
        self.codebase_knowledge['concepts'].update(static_concepts)
        self.codebase_knowledge['technologies'].update(static_technologies)

        self.logger.info(f"Connaissance codebase chargée: "
                        f"{len(self.codebase_knowledge['tools'])} outils, "
                        f"{len(self.codebase_knowledge['concepts'])} concepts")

    def _setup_quality_patterns(self):
        """Configure les patterns de qualité du contenu"""
        self.quality_patterns = {
            'technical_indicators': [
                r'\b(?:implement|configure|optimize|deploy|monitor)\b',
                r'\b(?:architecture|framework|library|api|database)\b',
                r'\b(?:performance|security|scalability|automation)\b'
            ],
            'code_patterns': [
                r'```[\s\S]*?```',  # Blocs de code
                r'`[^`]+`',         # Code inline
                r'\$[^$\n]+',       # Commandes shell
            ],
            'structure_patterns': [
                r'^#+\s+.+$',       # Titres markdown
                r'^\s*[-*+]\s+',    # Listes
                r'^\s*\d+\.\s+',    # Listes numérotées
            ],
            'agentbnzo_patterns': [
                r'\b(?:crew|agent|workflow|task|tool)\b',
                r'\b(?:gemini|openai|llm|ai|model)\b',
                r'\b(?:automation|orchestration|monitoring)\b'
            ]
        }

        # Compiler les patterns pour optimisation
        self.compiled_patterns = {}
        for category, patterns in self.quality_patterns.items():
            self.compiled_patterns[category] = [
                re.compile(pattern, re.IGNORECASE | re.MULTILINE)
                for pattern in patterns
            ]

    def _load_duplicate_detector(self):
        """Initialise le détecteur de contenu dupliqué"""
        self.content_hashes = set()
        self.similarity_threshold = 0.85

        # Charger hashes existants si disponible
        hash_file = BLOG_ROOT / "content" / "content_hashes.json"
        if hash_file.exists():
            try:
                with open(hash_file, 'r') as f:
                    data = json.load(f)
                    self.content_hashes.update(data.get('hashes', []))
            except Exception as e:
                self.logger.warning(f"Erreur chargement hashes: {e}")

    def validate_content(self, content: str, metadata: Dict[str, Any]) -> ContentValidation:
        """
        Valide la qualité et pertinence du contenu
        """
        # Scores individuels
        relevance_score = self._calculate_relevance_score(content, metadata)
        content_quality_score = self._calculate_content_quality_score(content)
        codebase_alignment_score = self._calculate_codebase_alignment_score(content)
        technical_depth_score = self._calculate_technical_depth_score(content)
        originality_score = self._calculate_originality_score(content)

        # Score total pondéré
        total_score = (
            relevance_score * 0.25 +
            content_quality_score * 0.25 +
            codebase_alignment_score * 0.20 +
            technical_depth_score * 0.20 +
            originality_score * 0.10
        )

        # Identifier issues et recommandations
        issues, recommendations = self._analyze_content_issues(content, {
            'relevance': relevance_score,
            'quality': content_quality_score,
            'codebase': codebase_alignment_score,
            'technical': technical_depth_score,
            'originality': originality_score
        })

        quality_score = QualityScore(
            total_score=total_score,
            relevance_score=relevance_score,
            content_quality_score=content_quality_score,
            codebase_alignment_score=codebase_alignment_score,
            technical_depth_score=technical_depth_score,
            originality_score=originality_score,
            issues=issues,
            recommendations=recommendations
        )

        # Filtrer le contenu si nécessaire
        filtered_content = self._filter_content(content, quality_score)

        # Déterminer si le contenu est valide
        min_score = CONTENT_FILTER_CONFIG.get('min_relevance_score', 0.7)
        is_valid = total_score >= min_score and len(issues) <= 2

        return ContentValidation(
            is_valid=is_valid,
            quality_score=quality_score,
            filtered_content=filtered_content,
            metadata=self._enhance_metadata(metadata, quality_score),
            validation_notes=self._generate_validation_notes(quality_score, is_valid)
        )

    def _calculate_relevance_score(self, content: str, metadata: Dict[str, Any]) -> float:
        """Calcule le score de pertinence pour AgentBnZo"""
        score = 0.0
        content_lower = content.lower()

        # Score basé sur catégorie
        category = metadata.get('category', '')
        if category in BLOG_CATEGORIES:
            category_config = BLOG_CATEGORIES[category]

            # Vérifier mots-clés de catégorie
            keywords = category_config.get('keywords', [])
            keyword_matches = sum(1 for kw in keywords if kw.lower() in content_lower)
            score += min(keyword_matches / len(keywords), 1.0) * 0.4

            # Vérifier outils codebase
            codebase_tools = category_config.get('codebase_tools', [])
            tool_matches = sum(1 for tool in codebase_tools if tool.lower() in content_lower)
            score += min(tool_matches / max(len(codebase_tools), 1), 1.0) * 0.4

        # Score patterns AgentBnZo
        agentbnzo_matches = 0
        for pattern in self.compiled_patterns['agentbnzo_patterns']:
            agentbnzo_matches += len(pattern.findall(content))
        score += min(agentbnzo_matches / 10, 1.0) * 0.2

        return min(score, 1.0)

    def _calculate_content_quality_score(self, content: str) -> float:
        """Calcule le score de qualité du contenu"""
        score = 0.0

        # Longueur appropriée
        word_count = len(content.split())
        if 800 <= word_count <= 2000:
            score += 0.3
        elif 500 <= word_count < 800:
            score += 0.2
        elif word_count > 2000:
            score += 0.1

        # Structure markdown
        structure_score = 0.0
        for pattern in self.compiled_patterns['structure_patterns']:
            matches = pattern.findall(content)
            structure_score += min(len(matches) / 5, 1.0) * 0.1

        score += min(structure_score, 0.3)

        # Présence de code
        code_score = 0.0
        for pattern in self.compiled_patterns['code_patterns']:
            if pattern.search(content):
                code_score += 0.1

        score += min(code_score, 0.2)

        # Indicateurs techniques
        tech_score = 0.0
        for pattern in self.compiled_patterns['technical_indicators']:
            matches = pattern.findall(content)
            tech_score += min(len(matches) / 5, 1.0) * 0.05

        score += min(tech_score, 0.2)

        return min(score, 1.0)

    def _calculate_codebase_alignment_score(self, content: str) -> float:
        """Calcule l'alignement avec la codebase AgentBnZo"""
        score = 0.0
        content_lower = content.lower()

        # Vérifier outils AgentBnZo
        tool_matches = sum(1 for tool in self.codebase_knowledge['tools']
                          if tool.lower() in content_lower)
        score += min(tool_matches / 5, 1.0) * 0.4

        # Vérifier concepts
        concept_matches = sum(1 for concept in self.codebase_knowledge['concepts']
                             if concept.lower() in content_lower)
        score += min(concept_matches / 3, 1.0) * 0.3

        # Vérifier technologies
        tech_matches = sum(1 for tech in self.codebase_knowledge['technologies']
                          if tech.lower() in content_lower)
        score += min(tech_matches / 3, 1.0) * 0.3

        return min(score, 1.0)

    def _calculate_technical_depth_score(self, content: str) -> float:
        """Calcule la profondeur technique du contenu"""
        score = 0.0

        # Compter éléments techniques
        technical_elements = {
            'code_blocks': len(re.findall(r'```[\s\S]*?```', content)),
            'inline_code': len(re.findall(r'`[^`]+`', content)),
            'commands': len(re.findall(r'\$[^$\n]+', content)),
            'links': len(re.findall(r'https?://[^\s\)]+', content)),
            'technical_terms': len(re.findall(
                r'\b(?:API|JSON|YAML|Docker|Python|JavaScript|SQL|HTTP|SSL|SSH|Git)\b',
                content, re.IGNORECASE
            ))
        }

        # Scorer les éléments
        score += min(technical_elements['code_blocks'] / 3, 1.0) * 0.3
        score += min(technical_elements['inline_code'] / 10, 1.0) * 0.2
        score += min(technical_elements['commands'] / 5, 1.0) * 0.2
        score += min(technical_elements['links'] / 5, 1.0) * 0.15
        score += min(technical_elements['technical_terms'] / 10, 1.0) * 0.15

        return min(score, 1.0)

    def _calculate_originality_score(self, content: str) -> float:
        """Calcule le score d'originalité (anti-duplication)"""
        # Hash du contenu pour comparaison
        content_hash = hashlib.md5(content.encode()).hexdigest()

        if content_hash in self.content_hashes:
            return 0.0  # Contenu identique trouvé

        # Vérifier similarité textuelle basique
        words = set(content.lower().split())
        if len(words) < 50:
            return 0.5  # Contenu trop court

        # Scorer l'originalité basée sur la diversité du vocabulaire
        unique_words = len(words)
        total_words = len(content.split())
        diversity_ratio = unique_words / total_words if total_words > 0 else 0

        # Ajouter le hash pour détection future
        self.content_hashes.add(content_hash)

        return min(diversity_ratio * 2, 1.0)

    def _analyze_content_issues(self, content: str, scores: Dict[str, float]) -> Tuple[List[str], List[str]]:
        """Analyse les problèmes du contenu et génère des recommandations"""
        issues = []
        recommendations = []

        # Analyser les scores faibles
        if scores['relevance'] < 0.6:
            issues.append("Pertinence faible pour AgentBnZo")
            recommendations.append("Ajouter plus de références aux outils AgentBnZo")

        if scores['quality'] < 0.6:
            issues.append("Qualité de contenu insuffisante")
            recommendations.append("Améliorer la structure et ajouter des exemples de code")

        if scores['codebase'] < 0.5:
            issues.append("Alignement codebase faible")
            recommendations.append("Intégrer plus d'outils et concepts de l'écosystème AgentBnZo")

        if scores['technical'] < 0.5:
            issues.append("Profondeur technique insuffisante")
            recommendations.append("Ajouter des détails techniques et des exemples pratiques")

        if scores['originality'] < 0.3:
            issues.append("Contenu potentiellement dupliqué")
            recommendations.append("Vérifier l'originalité et personnaliser le contenu")

        # Analyser le contenu directement
        word_count = len(content.split())
        if word_count < 500:
            issues.append("Contenu trop court")
            recommendations.append("Développer les explications et ajouter des exemples")

        if not re.search(r'```[\s\S]*?```', content):
            recommendations.append("Ajouter des exemples de code pour illustrer")

        return issues, recommendations

    def _filter_content(self, content: str, quality_score: QualityScore) -> str:
        """Filtre et améliore le contenu si nécessaire"""
        filtered_content = content

        # Nettoyer le contenu de base
        filtered_content = self._clean_content(filtered_content)

        # Ajouter des améliorations automatiques si le score est moyen
        if 0.6 <= quality_score.total_score < 0.8:
            filtered_content = self._enhance_content(filtered_content, quality_score)

        return filtered_content

    def _clean_content(self, content: str) -> str:
        """Nettoie le contenu de base"""
        # Supprimer lignes vides excessives
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)

        # Nettoyer espaces
        content = re.sub(r'[ \t]+', ' ', content)

        # Nettoyer fins de lignes
        content = re.sub(r' +\n', '\n', content)

        return content.strip()

    def _enhance_content(self, content: str, quality_score: QualityScore) -> str:
        """Améliore automatiquement le contenu"""
        enhanced = content

        # Ajouter note d'amélioration si pertinence faible
        if quality_score.codebase_alignment_score < 0.6:
            footer = "\n\n---\n\n*Pour aller plus loin avec AgentBnZo, consultez les outils de l'écosystème mentionnés dans cet article.*"
            enhanced += footer

        return enhanced

    def _enhance_metadata(self, metadata: Dict[str, Any], quality_score: QualityScore) -> Dict[str, Any]:
        """Enrichit les métadonnées avec les scores de qualité"""
        enhanced_metadata = metadata.copy()

        enhanced_metadata.update({
            'quality_validation': {
                'total_score': quality_score.total_score,
                'relevance_score': quality_score.relevance_score,
                'content_quality_score': quality_score.content_quality_score,
                'codebase_alignment_score': quality_score.codebase_alignment_score,
                'technical_depth_score': quality_score.technical_depth_score,
                'originality_score': quality_score.originality_score,
                'validation_timestamp': datetime.now().isoformat(),
                'issues_count': len(quality_score.issues),
                'recommendations_count': len(quality_score.recommendations)
            }
        })

        return enhanced_metadata

    def _generate_validation_notes(self, quality_score: QualityScore, is_valid: bool) -> List[str]:
        """Génère des notes de validation"""
        notes = []

        if is_valid:
            notes.append(f"✅ Contenu validé avec un score de {quality_score.total_score:.2f}")
        else:
            notes.append(f"❌ Contenu rejeté - Score: {quality_score.total_score:.2f}")

        if quality_score.issues:
            notes.append(f"⚠️ {len(quality_score.issues)} problème(s) identifié(s)")

        if quality_score.recommendations:
            notes.append(f"💡 {len(quality_score.recommendations)} recommandation(s) d'amélioration")

        # Ajouter insights spécifiques
        if quality_score.codebase_alignment_score > 0.8:
            notes.append("🎯 Excellent alignement avec l'écosystème AgentBnZo")

        if quality_score.technical_depth_score > 0.8:
            notes.append("🔧 Contenu techniquement approfondi")

        return notes

    def save_content_hashes(self):
        """Sauvegarde les hashes de contenu pour détection de doublons"""
        hash_file = BLOG_ROOT / "content" / "content_hashes.json"
        hash_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(hash_file, 'w') as f:
                json.dump({
                    'hashes': list(self.content_hashes),
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            self.logger.error(f"Erreur sauvegarde hashes: {e}")

def main():
    """Test du filtre de qualité"""
    logging.basicConfig(level=logging.INFO)

    filter = ContentQualityFilter()

    # Test avec contenu exemple
    test_content = """
# Test CrewAI avec Gemini 2.5 Flash

Dans mes travaux sur AgentBnZo, j'ai testé l'intégration de Gemini 2.5 Flash avec CrewAI.

## Configuration

```python
from crewai import Agent, Task, Crew
import google.generativeai as genai

agent = Agent(
    role="Développeur IA",
    goal="Optimiser les workflows AgentBnZo",
    llm="gemini-2.5-flash-lite-preview-06-17"
)
```

## Résultats

L'automation fonctionne parfaitement avec les outils security_defense_crew et tech_watch.

Performance: +30% vs configuration précédente.
"""

    test_metadata = {
        'category': 'ia',
        'template_type': 'tutorial',
        'generated': True
    }

    print("🔍 Test du filtre de qualité...")
    validation = filter.validate_content(test_content, test_metadata)

    print(f"\n📊 Résultat: {'✅ VALIDE' if validation.is_valid else '❌ REJETÉ'}")
    print(f"Score total: {validation.quality_score.total_score:.2f}")
    print(f"- Pertinence: {validation.quality_score.relevance_score:.2f}")
    print(f"- Qualité: {validation.quality_score.content_quality_score:.2f}")
    print(f"- Alignement codebase: {validation.quality_score.codebase_alignment_score:.2f}")
    print(f"- Profondeur technique: {validation.quality_score.technical_depth_score:.2f}")
    print(f"- Originalité: {validation.quality_score.originality_score:.2f}")

    if validation.quality_score.issues:
        print(f"\n⚠️ Problèmes identifiés:")
        for issue in validation.quality_score.issues:
            print(f"  - {issue}")

    if validation.quality_score.recommendations:
        print(f"\n💡 Recommandations:")
        for rec in validation.quality_score.recommendations:
            print(f"  - {rec}")

    print(f"\n📝 Notes de validation:")
    for note in validation.validation_notes:
        print(f"  {note}")

if __name__ == "__main__":
    main()
