import json
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATS_LOG_PATH = os.path.join(BASE_DIR, "stats_log.json")

DIAGRAM_PATHS = {
    "clients": os.path.join(BASE_DIR, "clients_over_time.png"),
    "batches": os.path.join(BASE_DIR, "batches_over_time.png"),
    "primes": os.path.join(BASE_DIR, "primes_over_time.png"),
    "numbers": os.path.join(BASE_DIR, "numbers_processed_over_time.png"),
    "processed_vs_primes": os.path.join(BASE_DIR, "processed_vs_primes.png"),
    "batches_vs_clients": os.path.join(BASE_DIR, "batches_vs_clients.png")
}

def load_stats():
    try:
        with open(STATS_LOG_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Fehler beim Laden der Statistiken: {str(e)}")
        sys.exit(1)

def create_diagram(timestamps, data, diagram_type):
    try:
        plt.style.use("ggplot")
        fig = plt.figure(figsize=(12, 6))
        ax = fig.add_subplot(111)
        
        date_formatter = mdates.DateFormatter("%D %H:%M")
        ax.xaxis.set_major_formatter(date_formatter)
        plt.xticks(rotation=45)
        plt.tight_layout()

        if diagram_type == "clients":
            plt.plot(timestamps, data, "b-o", linewidth=2)
            plt.title("Aktive Clients über die Zeit", fontsize=14)
            plt.ylabel("Anzahl Clients")
        
        elif diagram_type == "batches":
            plt.plot(timestamps, data, "g--s", linewidth=2)
            plt.title("Abgeschlossene Batches", fontsize=14)
            plt.ylabel("Anzahl Batches")
        
        elif diagram_type == "primes":
            plt.plot(timestamps, data, "r-^", linewidth=2)
            plt.title("Gefundene Primzahlen", fontsize=14)
            plt.ylabel("Anzahl Primzahlen")
        
        elif diagram_type == "numbers":
            plt.plot(timestamps, data, "m-D", linewidth=2)
            plt.title("Verarbeitete Zahlen", fontsize=14)
            plt.ylabel("Anzahl Zahlen")
        
        elif diagram_type == "processed_vs_primes":
            plt.plot(timestamps, data["numbers"], "m--", label="Verarbeitete Zahlen", linewidth=2)
            plt.plot(timestamps, data["primes"], "r-", label="Gefundene Primzahlen", linewidth=2)
            plt.title("Effizienzvergleich", fontsize=14)
            plt.ylabel("Anzahl")
            plt.legend()
        
        elif diagram_type == "batches_vs_clients":
            plt.plot(timestamps, data["batches"], "g-", label="Batches", linewidth=2)
            plt.plot(timestamps, data["clients"], "b--", label="Aktive Clients", linewidth=2)
            plt.title("Auslastung der Clients", fontsize=14)
            plt.ylabel("Anzahl")
            plt.legend()

        plt.xlabel("Zeit", fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.savefig(DIAGRAM_PATHS[diagram_type], dpi=100, bbox_inches="tight")
        plt.close(fig)
        return True
    
    except Exception as e:
        print(f"Fehler bei {diagram_type}-Diagramm: {str(e)}")
        return False

def main():
    stats = load_stats()
    
    timestamps = [datetime.strptime(entry["timestamp"], "%Y-%m-%d %H:%M:%S") for entry in stats]
    data = {
        "clients": [entry["active_clients"] for entry in stats],
        "batches": [entry["total_batches_completed"] for entry in stats],
        "primes": [entry["total_primes_found"] for entry in stats],
        "numbers": [entry["total_numbers_processed"] for entry in stats]
    }

    results = {
        "clients": create_diagram(timestamps, data["clients"], "clients"),
        "batches": create_diagram(timestamps, data["batches"], "batches"),
        "primes": create_diagram(timestamps, data["primes"], "primes"),
        "numbers": create_diagram(timestamps, data["numbers"], "numbers"),
        "processed_vs_primes": create_diagram(timestamps, data, "processed_vs_primes"),
        "batches_vs_clients": create_diagram(timestamps, data, "batches_vs_clients")
    }

    successful = sum(results.values())
    print(f"Erfolgreich generierte Diagramme: {successful}/6")
    return successful == 6

if __name__ == "__main__":
    if main():
        print("Alle Diagramme erfolgreich erstellt!")
        sys.exit(0)
    else:
        print("Einige Diagramme konnten nicht generiert werden!")
        sys.exit(1)