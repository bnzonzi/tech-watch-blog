#!/usr/bin/env python3
"""
Planificateur d'automatisation pour le blog tech AgentBnZo
Orchestration complète: Feedly → Analyse → Gemini → Blog → Publication
"""

import os
import sys
import json
import logging
import asyncio
import traceback
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import signal
import time

# Imports des modules du blog
sys.path.append(str(Path(__file__).parent.parent))
from config.blog_config import (
    BLOG_ROOT, AUTOMATION_CONFIG, TELEGRAM_CONFIG, GEMINI_API_KEY_ENV
)

# Import modules locaux
try:
    from feedly_analyzer import FeedlyAnalyzer
    from gemini_content_generator import GeminiContentGenerator
    from blog_engine import BlogEngine
    from content_quality_filter import ContentQualityFilter
except ImportError as e:
    print(f"❌ Erreur import modules: {e}")
    sys.exit(1)

@dataclass
class AutomationReport:
    """Rapport d'exécution d'automatisation"""
    timestamp: str
    success: bool
    articles_analyzed: int
    articles_generated: int
    articles_published: int
    execution_time: float
    errors: List[str]
    warnings: List[str]
    quality_scores: List[float]
    next_execution: str

@dataclass
class AutomationState:
    """État persistant de l'automatisation"""
    last_execution: str
    total_articles_generated: int
    success_rate: float
    average_quality_score: float
    consecutive_failures: int
    configuration_version: str

class AutomationScheduler:
    """
    Orchestrateur principal du blog automatique AgentBnZo
    Gère le cycle complet: analyse → génération → validation → publication
    """

    def __init__(self):
        self.logger = self._setup_logging()
        self.state_file = BLOG_ROOT / "automation_state.json"
        self.reports_dir = BLOG_ROOT / "reports"
        self.reports_dir.mkdir(exist_ok=True)

        # Components
        self.feedly_analyzer = None
        self.content_generator = None
        self.blog_engine = None
        self.quality_filter = None

        # État
        self.state = self._load_state()
        self.running = False
        self._setup_signal_handlers()

    def _setup_logging(self) -> logging.Logger:
        """Configure le logging complet"""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)

        # Éviter les doublons
        if logger.handlers:
            return logger

        # Handler console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Handler fichier
        log_file = BLOG_ROOT / "automation.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)

        # Format
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        return logger

    def _setup_signal_handlers(self):
        """Configure les gestionnaires de signaux pour arrêt propre"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Gestionnaire d'arrêt propre"""
        self.logger.info(f"Signal {signum} reçu, arrêt en cours...")
        self.running = False

    def _load_state(self) -> AutomationState:
        """Charge l'état persistant"""
        if not self.state_file.exists():
            return AutomationState(
                last_execution="",
                total_articles_generated=0,
                success_rate=0.0,
                average_quality_score=0.0,
                consecutive_failures=0,
                configuration_version="1.0"
            )

        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)
                return AutomationState(**data)
        except Exception as e:
            self.logger.warning(f"Erreur chargement état: {e}")
            return AutomationState(
                last_execution="",
                total_articles_generated=0,
                success_rate=0.0,
                average_quality_score=0.0,
                consecutive_failures=0,
                configuration_version="1.0"
            )

    def _save_state(self):
        """Sauvegarde l'état persistant"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(asdict(self.state), f, indent=2)
        except Exception as e:
            self.logger.error(f"Erreur sauvegarde état: {e}")

    def _initialize_components(self) -> bool:
        """Initialise les composants nécessaires"""
        try:
            self.logger.info("Initialisation des composants...")

            # Vérifier variables d'environnement
            if not os.getenv(GEMINI_API_KEY_ENV):
                raise ValueError(f"Variable manquante: {GEMINI_API_KEY_ENV}")

            # Initialiser composants
            self.feedly_analyzer = FeedlyAnalyzer()
            self.content_generator = GeminiContentGenerator()
            self.blog_engine = BlogEngine()
            self.quality_filter = ContentQualityFilter()

            self.logger.info("✅ Composants initialisés")
            return True

        except Exception as e:
            self.logger.error(f"❌ Erreur initialisation: {e}")
            return False

    async def run_automation_cycle(self) -> AutomationReport:
        """
        Exécute un cycle complet d'automatisation
        """
        start_time = time.time()
        timestamp = datetime.now().isoformat()

        report = AutomationReport(
            timestamp=timestamp,
            success=False,
            articles_analyzed=0,
            articles_generated=0,
            articles_published=0,
            execution_time=0.0,
            errors=[],
            warnings=[],
            quality_scores=[],
            next_execution=""
        )

        try:
            self.logger.info("🚀 Démarrage cycle d'automatisation")

            # 1. Analyse des flux RSS Feedly
            self.logger.info("📡 Analyse flux RSS Feedly...")
            analyzed_articles = await self._run_feedly_analysis()
            report.articles_analyzed = len(analyzed_articles)

            if not analyzed_articles:
                report.warnings.append("Aucun article pertinent trouvé dans les flux RSS")
                self.logger.warning("⚠️ Aucun article à traiter")
                return report

            # 2. Génération de contenu avec Gemini
            self.logger.info(f"🤖 Génération contenu pour {len(analyzed_articles)} articles...")
            generated_articles = await self._run_content_generation(analyzed_articles)
            report.articles_generated = len(generated_articles)

            # 3. Validation qualité
            self.logger.info("🔍 Validation qualité du contenu...")
            validated_articles = await self._run_quality_validation(generated_articles)

            # Extraire scores pour rapport
            for article in validated_articles:
                if hasattr(article, 'quality_score'):
                    report.quality_scores.append(article.quality_score.total_score)

            # 4. Génération du blog statique
            if validated_articles:
                self.logger.info("🌐 Génération du blog statique...")
                await self._run_blog_generation(validated_articles)
                report.articles_published = len(validated_articles)

            # 5. Notification succès
            await self._send_success_notification(report)

            report.success = True
            self.state.consecutive_failures = 0
            self.logger.info("✅ Cycle d'automatisation terminé avec succès")

        except Exception as e:
            error_msg = f"Erreur cycle automation: {e}"
            self.logger.error(error_msg)
            self.logger.error(traceback.format_exc())
            report.errors.append(error_msg)

            self.state.consecutive_failures += 1
            await self._send_error_notification(error_msg)

        finally:
            # Finaliser rapport
            report.execution_time = time.time() - start_time
            report.next_execution = self._calculate_next_execution()

            # Mettre à jour état
            self._update_state(report)
            self._save_state()

            # Sauvegarder rapport
            await self._save_report(report)

        return report

    async def _run_feedly_analysis(self) -> List[Any]:
        """Exécute l'analyse des flux RSS Feedly"""
        try:
            # Limiter selon configuration
            max_articles = AUTOMATION_CONFIG.get('max_articles_per_day', 3)
            articles = self.feedly_analyzer.fetch_and_analyze_articles(max_articles * 2)

            # Exporter résultats pour debug
            if articles:
                export_path = self.feedly_analyzer.export_analysis_results(articles)
                self.logger.info(f"Résultats Feedly exportés: {export_path}")

            return articles[:max_articles]

        except Exception as e:
            raise Exception(f"Erreur analyse Feedly: {e}")

    async def _run_content_generation(self, analyzed_articles: List[Any]) -> List[Any]:
        """Génère le contenu avec Gemini"""
        generated_articles = []

        for i, analyzed_article in enumerate(analyzed_articles, 1):
            try:
                self.logger.info(f"Génération article {i}/{len(analyzed_articles)}: {analyzed_article.title[:50]}...")

                # Générer article
                generated_article = self.content_generator.generate_article_from_analysis([analyzed_article])

                # Sauvegarder immédiatement
                output_path = self.content_generator.save_article(generated_article)
                self.logger.info(f"Article sauvegardé: {output_path}")

                generated_articles.append(generated_article)

                # Pause entre générations pour éviter rate limiting
                await asyncio.sleep(2)

            except Exception as e:
                self.logger.error(f"Erreur génération article {i}: {e}")
                continue

        return generated_articles

    async def _run_quality_validation(self, generated_articles: List[Any]) -> List[Any]:
        """Valide la qualité des articles générés"""
        validated_articles = []

        for article in generated_articles:
            try:
                # Valider avec le filtre de qualité
                validation = self.quality_filter.validate_content(
                    article.content,
                    article.generation_metadata
                )

                if validation.is_valid:
                    # Enrichir l'article avec validation
                    article.quality_score = validation.quality_score
                    article.validation_notes = validation.validation_notes
                    validated_articles.append(article)

                    self.logger.info(f"✅ Article validé: {article.title[:50]} (score: {validation.quality_score.total_score:.2f})")
                else:
                    self.logger.warning(f"❌ Article rejeté: {article.title[:50]} (score: {validation.quality_score.total_score:.2f})")

            except Exception as e:
                self.logger.error(f"Erreur validation article: {e}")
                continue

        # Sauvegarder hashes pour détection doublons
        self.quality_filter.save_content_hashes()

        return validated_articles

    async def _run_blog_generation(self, validated_articles: List[Any]):
        """Génère le blog statique"""
        try:
            # Parser tous les articles (existants + nouveaux)
            all_posts = self.blog_engine.parse_posts()

            # Générer le site complet
            generation_results = self.blog_engine.generate_site(all_posts)

            self.logger.info(f"Site généré: {generation_results['stats'].total_posts} articles total")

        except Exception as e:
            raise Exception(f"Erreur génération blog: {e}")

    async def _send_success_notification(self, report: AutomationReport):
        """Envoie une notification de succès"""
        if not TELEGRAM_CONFIG.get('enabled', False):
            return

        try:
            message = f"""
🎉 Blog AgentBnZo mis à jour automatiquement

📊 Statistiques:
• Articles analysés: {report.articles_analyzed}
• Articles générés: {report.articles_generated}
• Articles publiés: {report.articles_published}
• Temps d'exécution: {report.execution_time:.1f}s

🏆 Score qualité moyen: {sum(report.quality_scores)/len(report.quality_scores):.2f}/1.0

⏰ Prochaine exécution: {report.next_execution}
""".strip()

            await self._send_telegram_message(message)

        except Exception as e:
            self.logger.warning(f"Erreur notification succès: {e}")

    async def _send_error_notification(self, error_msg: str):
        """Envoie une notification d'erreur"""
        if not TELEGRAM_CONFIG.get('enabled', False):
            return

        try:
            message = f"""
❌ Erreur automatisation blog AgentBnZo

🔥 Erreur: {error_msg}
🔢 Échecs consécutifs: {self.state.consecutive_failures}
⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

ℹ️ Vérifiez les logs pour plus de détails.
""".strip()

            await self._send_telegram_message(message)

        except Exception as e:
            self.logger.warning(f"Erreur notification erreur: {e}")

    async def _send_telegram_message(self, message: str):
        """Envoie un message Telegram"""
        import aiohttp

        bot_token = os.getenv(TELEGRAM_CONFIG.get('bot_token_env', ''))
        chat_id = os.getenv(TELEGRAM_CONFIG.get('chat_id_env', ''))

        if not bot_token or not chat_id:
            self.logger.warning("Configuration Telegram incomplète")
            return

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    self.logger.info("📱 Notification Telegram envoyée")
                else:
                    self.logger.warning(f"Erreur Telegram: {response.status}")

    def _calculate_next_execution(self) -> str:
        """Calcule la prochaine exécution"""
        now = datetime.now()
        schedule_time = AUTOMATION_CONFIG.get('schedule_time', '06:00')

        try:
            hour, minute = map(int, schedule_time.split(':'))
            next_exec = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

            # Si l'heure est passée, programmer pour le lendemain
            if next_exec <= now:
                next_exec += timedelta(days=1)

            return next_exec.strftime('%Y-%m-%d %H:%M:%S')

        except:
            # Fallback: dans 24h
            return (now + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')

    def _update_state(self, report: AutomationReport):
        """Met à jour l'état persistant"""
        self.state.last_execution = report.timestamp

        if report.success:
            self.state.total_articles_generated += report.articles_generated

            # Calculer taux de succès (sur les 10 dernières exécutions)
            # Simplification: utiliser consecutive_failures pour estimation
            if self.state.consecutive_failures == 0:
                self.state.success_rate = min(self.state.success_rate + 0.1, 1.0)

            # Mettre à jour score qualité moyen
            if report.quality_scores:
                avg_score = sum(report.quality_scores) / len(report.quality_scores)
                if self.state.average_quality_score == 0:
                    self.state.average_quality_score = avg_score
                else:
                    # Moyenne pondérée
                    self.state.average_quality_score = (
                        self.state.average_quality_score * 0.8 + avg_score * 0.2
                    )

    async def _save_report(self, report: AutomationReport):
        """Sauvegarde le rapport d'exécution"""
        try:
            report_file = self.reports_dir / f"automation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            with open(report_file, 'w') as f:
                # Convertir en dict pour JSON
                report_dict = asdict(report)
                json.dump(report_dict, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Rapport sauvegardé: {report_file}")

            # Nettoyer anciens rapports (garder 30 derniers)
            await self._cleanup_old_reports()

        except Exception as e:
            self.logger.error(f"Erreur sauvegarde rapport: {e}")

    async def _cleanup_old_reports(self):
        """Nettoie les anciens rapports"""
        try:
            reports = sorted(
                self.reports_dir.glob("automation_report_*.json"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )

            # Garder les 30 plus récents
            for old_report in reports[30:]:
                old_report.unlink()
                self.logger.debug(f"Rapport supprimé: {old_report}")

        except Exception as e:
            self.logger.warning(f"Erreur nettoyage rapports: {e}")

    async def run_daemon(self):
        """Exécute le daemon d'automatisation"""
        self.logger.info("🤖 Démarrage daemon automatisation blog AgentBnZo")

        if not self._initialize_components():
            self.logger.error("❌ Échec initialisation, arrêt du daemon")
            return

        self.running = True

        while self.running:
            try:
                # Calculer temps jusqu'à prochaine exécution
                next_exec_str = self._calculate_next_execution()
                next_exec = datetime.strptime(next_exec_str, '%Y-%m-%d %H:%M:%S')
                now = datetime.now()

                time_until_next = (next_exec - now).total_seconds()

                if time_until_next > 0:
                    self.logger.info(f"⏰ Prochaine exécution: {next_exec_str} (dans {time_until_next/3600:.1f}h)")

                    # Attendre avec vérification périodique
                    while time_until_next > 0 and self.running:
                        sleep_time = min(300, time_until_next)  # Max 5 min
                        await asyncio.sleep(sleep_time)
                        time_until_next -= sleep_time

                if self.running:
                    # Exécuter le cycle
                    report = await self.run_automation_cycle()
                    self.logger.info(f"Cycle terminé: {'✅ Succès' if report.success else '❌ Échec'}")

            except Exception as e:
                self.logger.error(f"Erreur daemon: {e}")
                await asyncio.sleep(300)  # Attendre 5 min avant retry

        self.logger.info("🔚 Daemon automatisation arrêté")

    async def run_once(self) -> AutomationReport:
        """Exécute un cycle unique pour test"""
        self.logger.info("🧪 Exécution unique du cycle d'automatisation")

        if not self._initialize_components():
            raise Exception("Échec initialisation composants")

        return await self.run_automation_cycle()

def main():
    """Point d'entrée principal"""
    import argparse

    parser = argparse.ArgumentParser(description="Automatisation blog AgentBnZo")
    parser.add_argument('--daemon', action='store_true', help='Lancer en mode daemon')
    parser.add_argument('--once', action='store_true', help='Exécuter une fois et quitter')
    parser.add_argument('--debug', action='store_true', help='Mode debug verbeux')

    args = parser.parse_args()

    # Configuration logging
    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=level,
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    scheduler = AutomationScheduler()

    try:
        if args.daemon:
            asyncio.run(scheduler.run_daemon())
        elif args.once:
            report = asyncio.run(scheduler.run_once())
            print(f"\n📊 Résultat: {'✅ Succès' if report.success else '❌ Échec'}")
            print(f"Articles générés: {report.articles_generated}")
            print(f"Temps d'exécution: {report.execution_time:.1f}s")
        else:
            print("Usage: python automation_scheduler.py [--daemon|--once] [--debug]")

    except KeyboardInterrupt:
        print("\n🔚 Arrêt demandé par l'utilisateur")
    except Exception as e:
        print(f"❌ Erreur fatale: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())