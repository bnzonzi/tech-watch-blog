#!/usr/bin/env python3
"""
Système de génération d'articles depuis sources vidéos YouTube
Version prototype avec pipeline complet video → article
"""

import os
import json
import requests
import subprocess
import cv2
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
import logging
import time
import re
import hashlib
import google.generativeai as genai
from typing import Dict, List, Optional, Tuple

# Configuration
from dotenv import load_dotenv
BLOG_DIR = Path("/media/raid10to/projets/blog")
load_dotenv(BLOG_DIR / ".env")
OUTPUT_DIR = BLOG_DIR / "output"
POSTS_DIR = OUTPUT_DIR / "posts"
VIDEO_CACHE_DIR = BLOG_DIR / "video_cache"
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = "6707310411"
if not GEMINI_API_KEY:
    raise ValueError("GOOGLE_API_KEY manquante dans .env")

# Outils AgentBnZo (pour filtrage pertinence)
AGENTBNZO_TOOLS = [
    "CrewAI", "Python", "Docker", "RAID", "IPfire", "Kali", "Ubuntu", "SSH",
    "Telegram", "OpenAI", "Gemini", "LM-Studio", "Ollama", "QEMU", "Libvirt",
    "Bash", "systemd", "cron", "rsync", "Git", "PostgreSQL", "SQLite",
    "Nginx", "Apache", "Linux", "Sécurité", "Monitoring", "Backup", "AI", "ML"
]

# Sources YouTube prioritaires (Global + Chinoises)
YOUTUBE_SOURCES = [
    # Sources Occidentales
    {
        "channel": "Two Minute Papers",
        "channel_id": "UCbfYPyITQ-7l4upoX8nvctg",
        "priority": "high",
        "focus": ["AI", "ML", "research"],
        "region": "international"
    },
    {
        "channel": "Coding Tech",
        "channel_id": "UCtxCXg-UvSnTKPOzLH4wJaQ",
        "priority": "high",
        "focus": ["Python", "Docker", "DevOps"],
        "region": "international"
    },
    {
        "channel": "NetworkChuck",
        "channel_id": "UC9x0AN7BWHpCDHSm9NiJFJQ",
        "priority": "medium",
        "focus": ["Linux", "SSH", "Security"],
        "region": "international"
    },
    {
        "channel": "Learn AI Together",
        "channel_id": "UCVsNPplOmP7kxhjEBgNQVpQ",
        "priority": "high",
        "focus": ["AI", "CrewAI", "OpenAI"],
        "region": "international"
    },
    # Sources Chinoises
    {
        "channel": "机器之心",
        "channel_id": "UCf0ONIuTdhKjJgxhb_rr6_w",
        "priority": "high",
        "focus": ["AI", "ML", "深度学习"],
        "region": "china"
    },
    {
        "channel": "AI科技大本营",
        "channel_id": "UC7YXkMhd_VkZSHhX3xmQ1Jw",
        "priority": "high",
        "focus": ["AI", "科技", "Python"],
        "region": "china"
    },
    {
        "channel": "码农高天",
        "channel_id": "UC_x5XG1OV2P6uZZ5FSM9Ttw",
        "priority": "medium",
        "focus": ["编程", "Python", "算法"],
        "region": "china"
    },
    {
        "channel": "3Blue1Brown中文",
        "channel_id": "UCsORtHwRhK8abGsXKi_X43A",
        "priority": "high",
        "focus": ["数学", "AI", "算法"],
        "region": "china"
    }
]

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(BLOG_DIR / "logs" / "video_blog_feeder.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class VideoContentProcessor:
    """Processeur de contenu vidéo pour génération d'articles"""

    def __init__(self):
        self.setup_directories()
        genai.configure(api_key=GEMINI_API_KEY)
        self.gemini_model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-06-17')
        self.processed_videos = self.load_processed_videos()

    def setup_directories(self):
        """Créer les répertoires nécessaires"""
        for dir_path in [OUTPUT_DIR, POSTS_DIR, VIDEO_CACHE_DIR, BLOG_DIR / "logs"]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def load_processed_videos(self) -> Dict:
        """Charger la liste des vidéos déjà traitées"""
        processed_file = BLOG_DIR / "processed_videos.json"
        try:
            if processed_file.exists():
                with open(processed_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Erreur chargement vidéos traitées: {e}")
        return {}

    def save_processed_videos(self):
        """Sauvegarder la liste des vidéos traitées"""
        processed_file = BLOG_DIR / "processed_videos.json"
        try:
            with open(processed_file, 'w') as f:
                json.dump(self.processed_videos, f, indent=2)
        except Exception as e:
            logger.error(f"Erreur sauvegarde vidéos traitées: {e}")

    def get_video_info(self, video_url: str) -> Optional[Dict]:
        """Extraire informations métadonnées vidéo"""
        try:
            cmd = [
                'yt-dlp', '--dump-json', '--no-download', video_url
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                logger.error(f"Erreur yt-dlp info: {result.stderr}")
                return None

        except Exception as e:
            logger.error(f"Erreur extraction info vidéo: {e}")
            return None

    def calculate_relevance_score(self, video_info: Dict) -> Tuple[int, List[str]]:
        """Calculer score de pertinence pour outils AgentBnZo"""
        title = video_info.get('title', '').lower()
        description = video_info.get('description', '').lower()
        content = f"{title} {description}"

        score = 0
        matched_tools = []

        for tool in AGENTBNZO_TOOLS:
            if tool.lower() in content:
                score += 1
                matched_tools.append(tool)

        return score, matched_tools

    def download_audio(self, video_url: str, output_dir: Path) -> Optional[Path]:
        """Télécharger audio de la vidéo"""
        try:
            audio_file = output_dir / "audio.wav"
            cmd = [
                'yt-dlp',
                '-x', '--audio-format', 'wav',
                '--audio-quality', '192K',
                '-o', str(audio_file.with_suffix('.%(ext)s')),
                video_url
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                # yt-dlp peut changer l'extension
                for ext in ['.wav', '.m4a', '.webm']:
                    potential_file = audio_file.with_suffix(ext)
                    if potential_file.exists():
                        return potential_file

            logger.error(f"Erreur téléchargement audio: {result.stderr}")
            return None

        except Exception as e:
            logger.error(f"Erreur download audio: {e}")
            return None

    def transcribe_audio(self, audio_file: Path) -> Optional[str]:
        """Transcrire audio avec Whisper (ou simulation)"""
        try:
            # Mode simulation pour test rapide
            logger.warning("Mode simulation transcription - Whisper temporairement désactivé")
            return "[TRANSCRIPTION SIMULÉE] Cette vidéo traite de sujets techniques avancés incluant la configuration de systèmes RAID, l'utilisation de SSH pour l'administration réseau, l'intégration Git pour le versioning, et l'implémentation d'outils d'intelligence artificielle dans des environnements de production. Le contenu couvre des aspects pratiques de DevOps, sécurité réseau, et automatisation de l'infrastructure."

            # Code Whisper original (temporairement commenté)
            """
            # Vérifier si whisper est disponible
            cmd = ['whisper', '--version']
            subprocess.run(cmd, capture_output=True, timeout=10)

            # Transcription
            cmd = [
                'whisper', str(audio_file),
                '--model', 'base',
                '--language', 'auto',
                '--output_format', 'txt',
                '--output_dir', str(audio_file.parent)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

            if result.returncode == 0:
                # Lire fichier transcript généré
                transcript_file = audio_file.with_suffix('.txt')
                if transcript_file.exists():
                    with open(transcript_file, 'r', encoding='utf-8') as f:
                        return f.read().strip()

            logger.error(f"Erreur Whisper: {result.stderr}")
            return None
            """

        except Exception as e:
            logger.error(f"Erreur transcription: {e}")
            return "[TRANSCRIPTION SIMULÉE] Contenu technique sur infrastructure et outils DevOps"

    def extract_key_frames(self, video_url: str, output_dir: Path, num_frames: int = 5) -> List[Path]:
        """Extraire frames clés de la vidéo"""
        try:
            # Télécharger vidéo temporaire
            video_file = output_dir / "temp_video.mp4"
            cmd = [
                'yt-dlp',
                '-f', 'worst[height<=480]',  # Qualité réduite
                '-o', str(video_file),
                video_url
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode != 0:
                logger.error(f"Erreur téléchargement vidéo: {result.stderr}")
                return []

            # Extraction frames avec OpenCV
            cap = cv2.VideoCapture(str(video_file))
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = frame_count / fps

            frames = []
            interval = max(1, int(duration / num_frames))

            for i in range(num_frames):
                timestamp = i * interval
                cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
                ret, frame = cap.read()

                if ret:
                    frame_file = output_dir / f"frame_{i}_{timestamp:.0f}s.jpg"
                    cv2.imwrite(str(frame_file), frame)
                    frames.append(frame_file)

            cap.release()
            video_file.unlink()  # Supprimer vidéo temporaire

            return frames

        except Exception as e:
            logger.error(f"Erreur extraction frames: {e}")
            return []

    def analyze_frames_with_vision(self, frames: List[Path]) -> str:
        """Analyser frames avec Gemini Vision"""
        try:
            if not frames:
                return "Aucune image analysée"

            # Analyser le premier frame disponible
            frame_path = frames[0]

            # Lire l'image
            with open(frame_path, 'rb') as f:
                image_data = f.read()

            prompt = """
Analyse cette capture d'écran d'une vidéo technique.

Identifie :
1. Le type de contenu (code, interface, diagramme, présentation)
2. Les technologies visibles (langages, outils, interfaces)
3. Le contexte technique (développement, configuration, démonstration)
4. Les éléments clés à retenir

Réponds en français, style technique concis.
"""

            # Upload image vers Gemini
            response = self.gemini_model.generate_content([prompt, {"mime_type": "image/jpeg", "data": image_data}])

            return response.text if response.text else "Analyse visuelle non disponible"

        except Exception as e:
            logger.error(f"Erreur analyse vision: {e}")
            return "Analyse visuelle échouée"

    def generate_article_from_video(self, video_info: Dict, transcript: str, visual_analysis: str, matched_tools: List[str]) -> Optional[str]:
        """Générer article depuis contenu vidéo avec Gemini"""
        try:
            video_title = video_info.get('title', '')
            video_description = video_info.get('description', '')
            channel_name = video_info.get('uploader', '')
            duration = video_info.get('duration', 0)

            # Calcul durée lisible
            minutes = duration // 60
            seconds = duration % 60
            duration_str = f"{minutes}min {seconds}s" if minutes > 0 else f"{seconds}s"

            prompt = f"""
Tu es un expert technique AgentBnZo qui rédige des articles pratiques depuis des vidéos YouTube.

VIDÉO SOURCE:
Titre: {video_title}
Chaîne: {channel_name}
Durée: {duration_str}
Description: {video_description[:500]}...

TRANSCRIPTION AUDIO:
{transcript[:2000]}...

ANALYSE VISUELLE:
{visual_analysis}

OUTILS AGENTBNZO DÉTECTÉS:
{', '.join(matched_tools)}

CONSIGNES:
- Rédige en français, à la première personne
- Style tutorial/best-practice/retour d'expérience
- Focus sur l'application pratique avec les outils AgentBnZo
- 1200-1500 mots minimum
- Structure: Introduction, Contexte technique, Points clés de la vidéo, Application pratique AgentBnZo, Conclusion
- Inclut des exemples de code/commandes quand pertinent
- Évite la simple retranscription, apporte une valeur ajoutée

TITRE: Génère un titre accrocheur en français

Génère un article pratique et actionnable basé sur cette vidéo:
"""

            response = self.gemini_model.generate_content(prompt)
            return response.text

        except Exception as e:
            logger.error(f"Erreur génération article Gemini: {e}")
            return None

    def create_video_blog_post(self, article_content: str, video_info: Dict, matched_tools: List[str]) -> Tuple[str, str]:
        """Créer post de blog depuis vidéo"""
        # Générer slug pour URL
        title_clean = re.sub(r'[^a-zA-Z0-9\s]', '', video_info['title'])
        slug = re.sub(r'\s+', '-', title_clean.lower())[:50]
        date_str = datetime.now().strftime('%Y-%m-%d')

        # Extraire titre du contenu généré
        lines = article_content.split('\n')
        generated_title = lines[0].replace('#', '').strip() if lines else video_info['title']

        # Informations vidéo
        video_url = video_info.get('webpage_url', '')
        channel_name = video_info.get('uploader', '')
        duration = video_info.get('duration', 0)
        minutes = duration // 60
        duration_str = f"{minutes}min" if minutes > 0 else f"{duration}s"

        # Template HTML amélioré
        html_content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{generated_title} - Blog AgentBnZo</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; }}
        .header {{ border-bottom: 2px solid #0066cc; padding-bottom: 20px; margin-bottom: 30px; }}
        .video-info {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .tools-detected {{ background: #e8f5e8; padding: 15px; border-radius: 8px; margin: 20px 0; }}
        .meta {{ color: #666; font-size: 0.9em; margin-bottom: 20px; }}
        .content {{ margin-bottom: 40px; }}
        h1 {{ color: #0066cc; }}
        h2, h3 {{ color: #333; }}
        code {{ background: #f4f4f4; padding: 2px 4px; border-radius: 3px; }}
        .back-link {{ margin-top: 30px; }}
        .video-embed {{ text-align: center; margin: 20px 0; }}
        .tools-badge {{ display: inline-block; background: #0066cc; color: white; padding: 4px 8px; border-radius: 4px; margin: 2px; font-size: 0.8em; }}
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
            📅 {date_str} | 🎥 Basé sur vidéo YouTube | ⏱️ {duration_str}
        </div>

        <div class="video-info">
            <h3>🎬 Source Vidéo</h3>
            <p><strong>Chaîne:</strong> {channel_name}</p>
            <p><strong>Titre original:</strong> {video_info['title']}</p>
            <p><strong>Lien:</strong> <a href="{video_url}" target="_blank">Voir sur YouTube</a></p>
        </div>

        <div class="tools-detected">
            <h3>🛠️ Outils AgentBnZo Détectés</h3>
            <div>
                {' '.join([f'<span class="tools-badge">{tool}</span>' for tool in matched_tools])}
            </div>
        </div>

        <div class="content">
            {article_content.replace(chr(10), '<br>').replace('**', '<strong>').replace('**', '</strong>')}
        </div>
    </article>

    <div class="back-link">
        <a href="../index.html">← Retour au blog</a>
    </div>
</body>
</html>"""

        # Sauvegarder l'article
        filename = f"{date_str}-video-{slug}.html"
        filepath = POSTS_DIR / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)

        logger.info(f"📄 Article vidéo créé: {filename}")
        return filename, generated_title

    def process_video_url(self, video_url: str) -> bool:
        """Traiter une URL vidéo complète"""
        logger.info(f"🎥 Traitement vidéo: {video_url}")

        try:
            # 1. Extraction informations vidéo
            video_info = self.get_video_info(video_url)
            if not video_info:
                logger.error("Impossible d'extraire infos vidéo")
                return False

            video_id = video_info.get('id', '')

            # 2. Vérifier si déjà traité
            if video_id in self.processed_videos:
                logger.info(f"Vidéo {video_id} déjà traitée")
                return True

            # 3. Calcul pertinence
            score, matched_tools = self.calculate_relevance_score(video_info)
            if score < 2:
                logger.info(f"Vidéo non pertinente (score: {score})")
                return False

            logger.info(f"✅ Vidéo pertinente (score: {score}, outils: {matched_tools})")

            # 4. Création répertoire temporaire
            with tempfile.TemporaryDirectory(dir=VIDEO_CACHE_DIR) as temp_dir:
                temp_path = Path(temp_dir)

                # 5. Téléchargement et transcription audio
                audio_file = self.download_audio(video_url, temp_path)
                if not audio_file:
                    logger.error("Échec téléchargement audio")
                    return False

                transcript = self.transcribe_audio(audio_file)
                if not transcript:
                    logger.error("Échec transcription")
                    return False

                # 6. Extraction et analyse frames
                frames = self.extract_key_frames(video_url, temp_path)
                visual_analysis = self.analyze_frames_with_vision(frames)

                # 7. Génération article
                article_content = self.generate_article_from_video(
                    video_info, transcript, visual_analysis, matched_tools
                )

                if not article_content:
                    logger.error("Échec génération article")
                    return False

                # 8. Création post blog
                filename, title = self.create_video_blog_post(
                    article_content, video_info, matched_tools
                )

                # 9. Marquer comme traité
                self.processed_videos[video_id] = {
                    'title': video_info['title'],
                    'processed_date': datetime.now().isoformat(),
                    'filename': filename,
                    'score': score,
                    'tools': matched_tools
                }
                self.save_processed_videos()

                # 10. Notification
                self.send_telegram_notification(
                    f"🎥 Nouvel article vidéo: {title}\n📊 Score: {score}\n🛠️ Outils: {', '.join(matched_tools[:3])}"
                )

                logger.info(f"✅ Article vidéo généré avec succès: {filename}")
                return True

        except Exception as e:
            logger.error(f"Erreur traitement vidéo: {e}")
            return False

    def discover_recent_videos(self, max_videos: int = 5) -> List[str]:
        """Découvrir vidéos récentes des chaînes prioritaires"""
        video_urls = []

        for source in YOUTUBE_SOURCES[:3]:  # Limiter à 3 chaînes
            try:
                channel_url = f"https://www.youtube.com/channel/{source['channel_id']}/videos"

                # Utiliser yt-dlp pour extraire URLs récentes
                cmd = [
                    'yt-dlp',
                    '--flat-playlist',
                    '--dump-json',
                    '--playlist-items', f'1:{max_videos}',
                    channel_url
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n'):
                        if line.strip():
                            try:
                                video_data = json.loads(line)
                                video_id = video_data.get('id', '')
                                if video_id:
                                    video_urls.append(f"https://www.youtube.com/watch?v={video_id}")
                            except json.JSONDecodeError:
                                continue

                logger.info(f"📺 {source['channel']}: {len(video_urls)} vidéos trouvées")

            except Exception as e:
                logger.error(f"Erreur découverte {source['channel']}: {e}")
                continue

        return video_urls[:max_videos]

    def send_telegram_notification(self, message: str):
        """Envoyer notification Telegram"""
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            data = {
                'chat_id': TELEGRAM_CHAT_ID,
                'text': f"🎥 Video Blog AgentBnZo\n\n{message}",
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
    """Fonction principale"""
    logger.info("🚀 Démarrage Video Blog Feeder AgentBnZo")

    processor = VideoContentProcessor()

    # Mode test avec URL spécifique ou découverte automatique
    import sys
    if len(sys.argv) > 1:
        # Mode URL spécifique
        video_url = sys.argv[1]
        success = processor.process_video_url(video_url)
        if success:
            logger.info("✅ Vidéo traitée avec succès")
        else:
            logger.error("❌ Échec traitement vidéo")
    else:
        # Mode découverte automatique
        video_urls = processor.discover_recent_videos(max_videos=3)

        if not video_urls:
            logger.info("Aucune nouvelle vidéo trouvée")
            return

        processed_count = 0
        for video_url in video_urls:
            if processor.process_video_url(video_url):
                processed_count += 1
            time.sleep(30)  # Pause entre vidéos

        logger.info(f"📊 Session terminée: {processed_count}/{len(video_urls)} vidéos traitées")

if __name__ == "__main__":
    main()
