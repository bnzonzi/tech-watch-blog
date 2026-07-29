#!/usr/bin/env python3
"""
API Flask simple pour sauvegarder la configuration category_manager.html
Endpoint: POST /api/save_config
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import logging
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Autoriser les requêtes depuis le fichier HTML local

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Chemins configuration
CONFIG_FILE = 'agentbnzo_blog_config.json'
BACKUP_DIR = 'config_backups'

# Créer répertoire backups
os.makedirs(BACKUP_DIR, exist_ok=True)

@app.route('/api/save_config', methods=['POST'])
def save_config():
    """
    Sauvegarde la configuration des catégories blog
    """
    try:
        config_data = request.get_json()

        if not config_data:
            return jsonify({'error': 'No data provided'}), 400

        # Backup ancienne config
        if os.path.exists(CONFIG_FILE):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(BACKUP_DIR, f"config_backup_{timestamp}.json")
            with open(CONFIG_FILE, 'r') as f:
                old_config = json.load(f)
            with open(backup_file, 'w') as f:
                json.dump(old_config, f, indent=2)
            logger.info(f"✅ Backup ancien config : {backup_file}")

        # Sauvegarder nouvelle config
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ Configuration sauvegardée : {CONFIG_FILE}")

        # Déclencher redémarrage feeder (optionnel)
        # os.system("systemctl restart blog-feeder.service")

        return jsonify({
            'success': True,
            'message': 'Configuration sauvegardée avec succès',
            'config_file': CONFIG_FILE
        })

    except Exception as e:
        logger.error(f"❌ Erreur sauvegarde config : {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/load_config', methods=['GET'])
def load_config():
    """
    Charge la configuration actuelle
    """
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return jsonify({
                'success': True,
                'config': config
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No configuration file found'
            }), 404

    except Exception as e:
        logger.error(f"❌ Erreur chargement config : {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Health check endpoint
    """
    return jsonify({
        'status': 'ok',
        'service': 'category-config-api',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    logger.info("🚀 Démarrage API Category Manager")
    logger.info(f"📁 Config file: {CONFIG_FILE}")
    logger.info(f"📂 Backup dir: {BACKUP_DIR}")
    logger.info("🌐 Endpoints disponibles:")
    logger.info("   - POST /api/save_config")
    logger.info("   - GET  /api/load_config")
    logger.info("   - GET  /api/health")

    app.run(host='127.0.0.1', port=5002, debug=True)
