from flask import Flask, jsonify, request, send_file, session, redirect, url_for
from threading import Lock, Timer
import json
import time
import signal
import sys
import os
import zipfile
import tempfile
import subprocess
from database import *
from datetime import datetime
import io
import base64
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, "server_state.json")
STATS_LOG_FILE = os.path.join(BASE_DIR, "stats_log.json")
PRIMES_FILE = os.path.join(BASE_DIR, "all_primes.txt")

DIAGRAM_FILES = [
    "clients_over_time.png",
    "batches_over_time.png",
    "primes_over_time.png",
    "numbers_processed_over_time.png",
    "processed_vs_primes.png",
    "batches_vs_clients.png"
]

app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, "static"),
    static_url_path=""
)

app.secret_key = 'ieu:DNMf<#k0g)r'

BATCH_SIZE = 100000  
CLIENT_TIMEOUT = 20  # in Sek
lock = Lock()
current_number = 0 
active_clients = {}  
unique_clients = set()  

stats = {
    "total_primes_found": 0,
    "highest_prime_found": 0,
    "total_batches_completed": 0,
    "total_clients": 0,
    "active_clients": 0,
    "total_numbers_processed": 0,
    "last_update": None
}

if os.path.exists(STATS_LOG_FILE):
    with open(STATS_LOG_FILE, "r") as f:
        stats_log = json.load(f)
else:
    stats_log = []

if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r") as f:
        state_data = json.load(f)
        current_number = state_data.get("current_number", 0)
        loaded_stats = state_data.get("stats", {})
        for key in stats:
            if key in loaded_stats and key != "total_clients":
                stats[key] = loaded_stats[key]


def save_state():
    with open(STATE_FILE, "w") as f:
        json.dump({"current_number": current_number, "stats": stats}, f)


def save_stats_log():
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    if stats_log and stats_log[-1]["timestamp"][:16] == timestamp[:16]: 
        return  

    stats_log.append({
        "timestamp": timestamp,
        "total_primes_found": stats["total_primes_found"],
        "total_batches_completed": stats["total_batches_completed"],
        "active_clients": stats["active_clients"],
        "total_numbers_processed": stats["total_numbers_processed"]
    })
    
    with open(STATS_LOG_FILE, "w") as f:
        json.dump(stats_log, f, indent=4)


def cleanup_inactive_clients():
    current_time = time.time()
    with lock:
        inactive = [ip for ip, last in active_clients.items() if current_time - last > CLIENT_TIMEOUT]
        for ip in inactive:
            del active_clients[ip]
        
        stats["active_clients"] = len(active_clients)
    
    Timer(60, cleanup_inactive_clients).start()


def periodic_save():
    save_stats_log()
    Timer(60, periodic_save).start()


@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"error": "Username und Passwort werden benötigt"}), 400
    
    if create_user(username, password):
        return jsonify({"status": "success"})
    else:
        return jsonify({"error": "Benutzername bereits vergeben"}), 400

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    user_id = verify_user(username, password)
    if user_id:
        session['user_id'] = user_id
        return jsonify({"status": "success"})
    else:
        return jsonify({"error": "Ungültige Anmeldedaten"}), 401

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/user/progress')
def user_progress():
    if 'user_id' not in session:
        return jsonify({"error": "Nicht angemeldet"}), 401
    
    progress = get_user_progress(session['user_id'])
    if progress:
        return jsonify({
            "total_primes_found": progress[0],
            "total_numbers_processed": progress[1]
        })
    return jsonify({"error": "Fortschritt nicht gefunden"}), 404

@app.route('/get_batch')
def get_batch():
    global current_number
    with lock:
        batch_size = session.get('batch_size', BATCH_SIZE)
        
        batch_range = (current_number, current_number + batch_size - 1)
        current_number += batch_size

        client_ip = request.remote_addr
        if client_ip:
            active_clients[client_ip] = time.time()
            stats["active_clients"] = len(active_clients)

        save_state()
        return jsonify({
            "range": batch_range,
            "size": batch_size
        })


@app.route('/submit_primes', methods=['POST'])
def submit_primes():
    global unique_clients
    data = request.get_json()
    if not data or not isinstance(data, list):
        return jsonify({"error": "Invalid data format. Expected a JSON array."}), 400

    with lock:
        stats["total_primes_found"] += len(data)
        if data: 
            stats["highest_prime_found"] = max(data)
        
        batch_size = session.get('batch_size', BATCH_SIZE)
        stats["total_numbers_processed"] += batch_size
        stats["total_batches_completed"] += 1

        client_ip = request.remote_addr
        if client_ip:
            active_clients[client_ip] = time.time()
            stats["active_clients"] = len(active_clients)

        client_ip = request.remote_addr
        if client_ip:
            if client_ip not in unique_clients:
                unique_clients.add(client_ip)
                stats["total_clients"] = len(unique_clients)
    
        stats["last_update"] = time.strftime("%Y-%m-%d %H:%M:%S")

        save_state()
        save_stats_log()

        with open(PRIMES_FILE, "a") as f:
            for prime in data:
                f.write(f"{prime}\n")

        if 'user_id' in session:
            update_user_progress(session['user_id'], len(data), batch_size)

    return jsonify({"status": "success"})


@app.route('/get_stats')
def get_stats():
    return jsonify(stats)


@app.route('/get_stats_log')
def get_stats_log():
    return jsonify(stats_log)

@app.route('/leaderboard')
def leaderboard():
    leaderboard_data = get_leaderboard()
    return jsonify([{
        "username": row[0],
        "numbers_processed": row[1],
        "primes_found": row[2]
    } for row in leaderboard_data])

@app.route('/generate_diagrams')
def generate_diagrams():
    try:
        result = subprocess.run(
            ["python", "create_diagrams.py"],
            capture_output=True,
            text=True,
            cwd=BASE_DIR
        )
        
        if result.returncode != 0:
            return f"Fehler: {result.stderr}", 500

        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        zip_path = temp_zip.name

        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for diagram in DIAGRAM_FILES:
                full_path = os.path.join(BASE_DIR, diagram)
                if os.path.exists(full_path):
                    zipf.write(full_path, diagram)

        def cleanup():
            try:
                if os.path.exists(zip_path):
                    os.remove(zip_path)
                
                for diagram in DIAGRAM_FILES:
                    file_path = os.path.join(BASE_DIR, diagram)
                    if os.path.exists(file_path):
                        os.remove(file_path)
            except Exception as e:
                print(f"Cleanup error: {str(e)}")

        response = send_file(
            zip_path,
            mimetype='application/zip',
            as_attachment=True,
            download_name='diagramme.zip'
        )

        response.call_on_close(cleanup)
        return response

    except Exception as e:
        return f"Kritischer Fehler: {str(e)}", 500
    
@app.route('/set_batch_size', methods=['POST'])
def set_batch_size():
    data = request.get_json()
    size = data.get('size')
    
    if size not in [100, 500, 1000, 5000, 10000, 50000, 100000, 500000, 1000000, 1500000, 2000000, 2500000, 3000000, 3500000, 4000000, 4500000, 5000000]:
        return jsonify({"error": "Ungültige Batch-Größe"}), 400
    
    session['batch_size'] = size
    return jsonify({"status": "success"})


@app.route('/diagram_live_all')
def diagram_live_all():
    import io
    import base64
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib import rcParams

    try:
        with open(STATS_LOG_FILE, "r") as f:
            stats = json.load(f)

        timestamps = [datetime.strptime(entry["timestamp"], "%Y-%m-%d %H:%M:%S") for entry in stats]
        data = {
            "clients": [entry["active_clients"] for entry in stats],
            "batches": [entry["total_batches_completed"] for entry in stats],
            "primes": [entry["total_primes_found"] for entry in stats],
            "numbers": [entry["total_numbers_processed"] for entry in stats]
        }

        diagram_types = [
            "clients",
            "batches",
            "primes",
            "numbers",
            "processed_vs_primes",
            "batches_vs_clients"
        ]

        def create_diagram(diagram_type):
            fig = plt.figure(figsize=(10, 5))
            ax = fig.add_subplot(111)
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m %H:%M"))
            plt.xticks(rotation=45)
            plt.tight_layout()
            rcParams.update({'figure.autolayout': True})
            plt.autoscale()


            if diagram_type == "clients":
                ax.plot(timestamps, data["clients"], "b-o", linewidth=2)
                ax.set_title("Aktive Clients über die Zeit")
                ax.set_ylabel("Anzahl Clients")

            elif diagram_type == "batches":
                ax.plot(timestamps, data["batches"], "g--s", linewidth=2)
                ax.set_title("Abgeschlossene Batches")
                ax.set_ylabel("Anzahl Batches")

            elif diagram_type == "primes":
                ax.plot(timestamps, data["primes"], "r-^", linewidth=2)
                ax.set_title("Gefundene Primzahlen")
                ax.set_ylabel("Anzahl Primzahlen")

            elif diagram_type == "numbers":
                ax.plot(timestamps, data["numbers"], "m-D", linewidth=2)
                ax.set_title("Verarbeitete Zahlen")
                ax.set_ylabel("Anzahl Zahlen")

            elif diagram_type == "processed_vs_primes":
                ax.plot(timestamps, data["numbers"], "m--", label="Verarbeitete Zahlen", linewidth=2)
                ax.plot(timestamps, data["primes"], "r-", label="Gefundene Primzahlen", linewidth=2)
                ax.set_title("Effizienzvergleich")
                ax.set_ylabel("Anzahl")
                ax.legend()

            elif diagram_type == "batches_vs_clients":
                ax.plot(timestamps, data["batches"], "g-", label="Batches", linewidth=2)
                ax.plot(timestamps, data["clients"], "b--", label="Aktive Clients", linewidth=2)
                ax.set_title("Auslastung der Clients")
                ax.set_ylabel("Anzahl")
                ax.legend()

            ax.set_xlabel("Zeit")
            ax.grid(True, alpha=0.3)

            buf = io.BytesIO()
            plt.savefig(buf, format="png", bbox_inches="tight")
            plt.close(fig)
            buf.seek(0)
            return base64.b64encode(buf.read()).decode("utf-8")

        images = {dtype: create_diagram(dtype) for dtype in diagram_types}
        return jsonify(images)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def signal_handler(sig, frame):
    print("\nFlask-Server wird beendet...")
    save_state()
    save_stats_log()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

periodic_save()
cleanup_inactive_clients()

if __name__ == '__main__':
    print("Flask wurde gestartet!")
    app.run(host="0.0.0.0", debug=False, use_reloader=False)