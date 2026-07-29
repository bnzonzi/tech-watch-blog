#!/usr/bin/env python3
"""
Feeder Control API - Backend pour contrôle temps réel des feeders
Besoins: Visibilité + Actions immédiates sur processus feeders
Solutions: API REST + gestion locks + métriques
"""

from flask import Flask, jsonify, request, render_template_string
import os
import subprocess
import json
import psutil
import time
from datetime import datetime, timedelta
from pathlib import Path
import threading
import signal
import fcntl

app = Flask(__name__)

# Configuration
BLOG_DIR = Path(__file__).parent.resolve()  # Use current project directory for logs and status
LOCK_FILE = Path("/tmp/blog_feeder.lock")
LOG_FILE = BLOG_DIR / "logs/enhanced_blog_feeder.log"
STATUS_FILE = BLOG_DIR / "feeder_status.json"

class FeederController:
    def __init__(self):
        self.feeders = {}
        self.update_status()

    def get_lock_status(self):
        """Vérifie status du lock file"""
        if not LOCK_FILE.exists():
            return {"status": "unlocked", "pid": None, "age": 0}

        try:
            stat = LOCK_FILE.stat()
            age_seconds = time.time() - stat.st_mtime

            # Lire PID si possible
            try:
                with open(LOCK_FILE, 'r') as f:
                    content = f.read().strip()
                    pid = int(content) if content.isdigit() else None
            except:
                pid = None

            return {
                "status": "locked",
                "pid": pid,
                "age": age_seconds,
                "age_human": str(timedelta(seconds=int(age_seconds)))
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_process_info(self):
        """Infos processus feeder actif"""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_info']):
            try:
                if 'enhanced_blog_feeder.py' in ' '.join(proc.info['cmdline'] or []):
                    processes.append({
                        'pid': proc.info['pid'],
                        'cpu': proc.info['cpu_percent'],
                        'memory': proc.info['memory_info'].rss / 1024 / 1024,  # MB
                        'cmdline': ' '.join(proc.info['cmdline'])
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return processes

    def get_log_tail(self, lines=20):
        """Dernières lignes du log"""
        try:
            result = subprocess.run(['tail', '-n', str(lines), str(LOG_FILE)],
                                  capture_output=True, text=True)
            return result.stdout.split('\n')
        except:
            return ["Log non accessible"]

    def get_recent_stats(self):
        """Statistiques récentes depuis les logs"""
        try:
            # Analyser dernière heure de logs
            result = subprocess.run(['tail', '-n', '1000', str(LOG_FILE)],
                                  capture_output=True, text=True)
            lines = result.stdout.split('\n')

            articles_generated = len([l for l in lines if "Article généré:" in l])
            errors = len([l for l in lines if "ERROR" in l])

            return {
                "articles_last_hour": articles_generated,
                "errors_last_hour": errors,
                "last_activity": self.get_last_activity()
            }
        except:
            return {"articles_last_hour": 0, "errors_last_hour": 0, "last_activity": "Unknown"}

    def get_last_activity(self):
        """Dernière activité dans les logs"""
        try:
            result = subprocess.run(['tail', '-n', '1', str(LOG_FILE)],
                                  capture_output=True, text=True)
            last_line = result.stdout.strip()
            if last_line:
                # Extraire timestamp
                parts = last_line.split(' - ')
                if len(parts) > 0:
                    return parts[0]
            return "No activity"
        except:
            return "Unknown"

    def update_status(self):
        """Met à jour le status global"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "lock": self.get_lock_status(),
            "processes": self.get_process_info(),
            "stats": self.get_recent_stats(),
            "logs": self.get_log_tail(10)
        }

        # Sauvegarder status
        with open(STATUS_FILE, 'w') as f:
            json.dump(status, f, indent=2)

        return status

    def force_unlock(self):
        """Force suppression du lock"""
        try:
            if LOCK_FILE.exists():
                LOCK_FILE.unlink()
            return {"success": True, "message": "Lock supprimé"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def kill_process(self, pid):
        """Tue un processus feeder"""
        try:
            os.kill(int(pid), signal.SIGTERM)
            time.sleep(2)
            # Vérifier si toujours vivant
            try:
                os.kill(int(pid), 0)
                # Toujours vivant, SIGKILL
                os.kill(int(pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
            return {"success": True, "message": f"Processus {pid} terminé"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def start_feeder(self):
        """Lance le feeder"""
        try:
            subprocess.Popen([
                'bash', '-c',
                f'cd {BLOG_DIR} && ./resume_blog.sh'
            ])
            return {"success": True, "message": "Feeder lancé"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def stop_feeder(self):
        """Arrête le feeder"""
        try:
            subprocess.run([
                'bash', '-c',
                f'cd {BLOG_DIR} && ./hold_blog.sh'
            ])
            return {"success": True, "message": "Feeder arrêté"}
        except Exception as e:
            return {"success": False, "error": str(e)}

# Instance globale
controller = FeederController()

# Routes API
@app.route('/api/status')
def get_status():
    """Status complet du feeder"""
    return jsonify(controller.update_status())

@app.route('/api/action/<action>', methods=['POST'])
def execute_action(action):
    """Exécute une action"""
    if action == 'start':
        return jsonify(controller.start_feeder())
    elif action == 'stop':
        return jsonify(controller.stop_feeder())
    elif action == 'unlock':
        return jsonify(controller.force_unlock())
    elif action == 'kill':
        pid = request.json.get('pid')
        if pid:
            return jsonify(controller.kill_process(pid))
        return jsonify({"success": False, "error": "PID requis"})
    else:
        return jsonify({"success": False, "error": "Action inconnue"})

@app.route('/api/logs/<int:lines>')
def get_logs(lines):
    """Récupère N dernières lignes de logs"""
    logs = controller.get_log_tail(lines)
    return jsonify({"logs": logs})

@app.route('/')
def dashboard():
    """Interface web principale"""
    return render_template_string(DASHBOARD_HTML)

# Interface HTML intégrée
DASHBOARD_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Feeder Control Center</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .card { background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .status-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
        .metric { text-align: center; }
        .metric-value { font-size: 2em; font-weight: bold; margin: 10px 0; }
        .metric-label { color: #666; font-size: 0.9em; }
        .btn { padding: 10px 20px; margin: 5px; border: none; border-radius: 4px; cursor: pointer; }
        .btn-success { background: #28a745; color: white; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-warning { background: #ffc107; color: black; }
        .logs { background: #1e1e1e; color: #0f0; font-family: monospace; padding: 15px; border-radius: 4px; max-height: 300px; overflow-y: auto; }
        .status-ok { color: #28a745; }
        .status-error { color: #dc3545; }
        .status-warning { color: #ffc107; }
        .auto-refresh { position: fixed; top: 10px; right: 10px; background: rgba(0,0,0,0.8); color: white; padding: 5px 10px; border-radius: 4px; font-size: 0.8em; }
    </style>
</head>
<body>
    <div class="auto-refresh">🔄 Auto-refresh: <span id="countdown">5</span>s</div>

    <div class="container">
        <h1>🎛️ Feeder Control Center</h1>

        <div class="card">
            <h3>Actions Rapides</h3>
            <button class="btn btn-success" onclick="action('start')">▶️ Start Feeder</button>
            <button class="btn btn-danger" onclick="action('stop')">⏹️ Stop Feeder</button>
            <button class="btn btn-warning" onclick="action('unlock')">🔓 Force Unlock</button>
            <button class="btn btn-warning" onclick="refreshStatus()">🔄 Refresh</button>
        </div>

        <div class="card">
            <h3>Status en Temps Réel</h3>
            <div class="status-grid" id="status-grid">
                <!-- Rempli par JavaScript -->
            </div>
        </div>

        <div class="card">
            <h3>Processus Actifs</h3>
            <div id="processes">
                <!-- Rempli par JavaScript -->
            </div>
        </div>

        <div class="card">
            <h3>Logs Temps Réel</h3>
            <div class="logs" id="logs">
                <!-- Rempli par JavaScript -->
            </div>
        </div>
    </div>

    <script>
        let refreshCounter = 5;

        function refreshStatus() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    updateStatusGrid(data);
                    updateProcesses(data.processes);
                    updateLogs(data.logs);
                });
        }

        function updateStatusGrid(data) {
            const grid = document.getElementById('status-grid');
            const lock = data.lock;
            const stats = data.stats;

            grid.innerHTML = `
                <div class="metric">
                    <div class="metric-label">Lock Status</div>
                    <div class="metric-value ${lock.status === 'unlocked' ? 'status-ok' : 'status-error'}">
                        ${lock.status.toUpperCase()}
                    </div>
                    ${lock.age ? `<div>Age: ${lock.age_human}</div>` : ''}
                </div>
                <div class="metric">
                    <div class="metric-label">Articles/Heure</div>
                    <div class="metric-value">${stats.articles_last_hour}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Erreurs/Heure</div>
                    <div class="metric-value ${stats.errors_last_hour > 0 ? 'status-warning' : 'status-ok'}">
                        ${stats.errors_last_hour}
                    </div>
                </div>
                <div class="metric">
                    <div class="metric-label">Dernière Activité</div>
                    <div class="metric-value" style="font-size: 0.8em;">
                        ${stats.last_activity}
                    </div>
                </div>
            `;
        }

        function updateProcesses(processes) {
            const container = document.getElementById('processes');
            if (processes.length === 0) {
                container.innerHTML = '<p>Aucun processus feeder actif</p>';
                return;
            }

            container.innerHTML = processes.map(proc => `
                <div style="border: 1px solid #ddd; padding: 10px; margin: 5px 0; border-radius: 4px;">
                    <strong>PID:</strong> ${proc.pid} |
                    <strong>CPU:</strong> ${proc.cpu}% |
                    <strong>Memory:</strong> ${proc.memory.toFixed(1)}MB
                    <button class="btn btn-danger" onclick="killProcess(${proc.pid})" style="float: right;">❌ Kill</button>
                    <div style="font-family: monospace; font-size: 0.8em; margin-top: 5px;">
                        ${proc.cmdline}
                    </div>
                </div>
            `).join('');
        }

        function updateLogs(logs) {
            const container = document.getElementById('logs');
            container.innerHTML = logs.join('\\n');
            container.scrollTop = container.scrollHeight;
        }

        function action(actionType) {
            fetch(`/api/action/${actionType}`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            })
            .then(response => response.json())
            .then(data => {
                alert(data.message || data.error);
                refreshStatus();
            });
        }

        function killProcess(pid) {
            if (confirm(`Vraiment tuer le processus ${pid}?`)) {
                fetch('/api/action/kill', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({pid: pid})
                })
                .then(response => response.json())
                .then(data => {
                    alert(data.message || data.error);
                    refreshStatus();
                });
            }
        }

        function countdown() {
            document.getElementById('countdown').textContent = refreshCounter;
            refreshCounter--;
            if (refreshCounter < 0) {
                refreshCounter = 5;
                refreshStatus();
            }
        }

        // Init
        refreshStatus();
        setInterval(countdown, 1000);
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
