let isRunning = false;
let remainingBatches = 0;
let leaderboardVisible = false;

function logMessage(message) {
    let logDiv = document.getElementById("log");
    logDiv.innerHTML += "<p>" + message + "</p>";
    logDiv.scrollTop = logDiv.scrollHeight;
}

function updateStatus(message) {
    document.getElementById("status").innerText = message;
}

function startSingleBatch() {
    if (isRunning) return;
    calculateBatch();
}

function startContinuous() {
    if (isRunning) return;
    isRunning = true;
    remainingBatches = -1;
    updateStatus("Dauerberechnung gestartet...");
    processBatches();
}

function startBatchCount() {
    if (isRunning) return;
    let count = parseInt(document.getElementById("batchCount").value);
    if (count > 0) {
        isRunning = true;
        remainingBatches = count;
        updateStatus(`Berechne ${count} Batches...`);
        processBatches();
    }
}

function stopCalculation() {
    isRunning = false;
    remainingBatches = 0;
    updateStatus("Berechnung gestoppt.");
    logMessage("⛔ Berechnung wurde gestoppt.");
}

function processBatches() {
    if (!isRunning || (remainingBatches === 0)) {
        stopCalculation();
        return;
    }

    calculateBatch(() => {
        if (remainingBatches > 0) {
            remainingBatches--;
            updateStatus(`Noch ${remainingBatches} Batches...`);
        }

        if (isRunning && (remainingBatches > 0 || remainingBatches === -1)) {
            setTimeout(processBatches, 100);
        } else {
            stopCalculation();
        }
    });
}

function calculateBatch(callback) {
    fetch("/get_batch")
        .then(response => response.json())
        .then(data => {
            const [start, end] = data.range;
            document.getElementById('currentBatchSize').textContent = data.size;
            logMessage(`Erhaltenes Batch (${data.size} Zahlen): ${start} bis ${end}`);
            const primes = findPrimes(start, end);
            logMessage("Gefundene Primzahlen: " + primes.length);
            submitPrimes(primes, callback);
        })
        .catch(error => {
            console.error("Fehler beim Abrufen des Batches:", error);
            updateStatus("Fehler beim Abrufen des Batches!");
            if (callback) callback();
        });
}

function findPrimes(start, end) {
    let primes = [];
    for (let num = start; num <= end; num++) {
        if (isPrime(num)) {
            primes.push(num);
        }
    }
    return primes;
}

function isPrime(n) {
    if (n <= 1) return false;
    if (n <= 3) return true;
    if (n % 2 === 0 || n % 3 === 0) return false;
    for (let i = 5; i * i <= n; i += 6) {
        if (n % i === 0 || n % (i + 2) === 0) return false;
    }
    return true;
}

function submitPrimes(primes, callback) {
    if (!Array.isArray(primes) || primes.length === 0) {
        logMessage("Keine Primzahlen gefunden.");
        updateStatus("Keine Primzahlen gefunden.");
        if (callback) callback();
        return;
    }

    updateStatus("Primzahlen werden gesendet...");
    fetch("/submit_primes", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(primes)
    })
        .then(response => response.json())
        .then(data => {
            logMessage("Server-Antwort: " + JSON.stringify(data));
            updateStatus("Berechnung abgeschlossen!");
            updateUserPanel();
            updateHighestPrime();
            if (callback) callback();
        })
        .catch(error => {
            console.error("Fehler beim Senden der Primzahlen:", error);
            updateStatus("Fehler beim Senden der Primzahlen!");
            if (callback) callback();
        });
}

function generateAndDownloadDiagrams() {
    updateStatus("Diagramme werden generiert...");
    fetch("/generate_diagrams")
        .then(response => response.blob())
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'diagramme.zip';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            updateStatus("Diagramme ready zum Download!");
        })
        .catch(error => {
            console.error("Fehler:", error);
            updateStatus("Fehler beim Generieren!");
        });
}

function showLogin() {
    document.getElementById('modalTitle').textContent = 'Anmelden';
    document.getElementById('authAction').textContent = 'Anmelden';
    document.getElementById('authAction').onclick = login;
    showModal();
}

function showRegister() {
    document.getElementById('modalTitle').textContent = 'Registrieren';
    document.getElementById('authAction').textContent = 'Registrieren';
    document.getElementById('authAction').onclick = register;
    showModal();
}

function showModal() {
    document.getElementById('authModal').style.display = 'flex';
}

function hideModal() {
    document.getElementById('authModal').style.display = 'none';
}

function updateUserPanel() {
    fetch('/user/progress')
        .then(response => response.json())
        .then(data => {
            if (!data.error) {
                document.getElementById('userPrimes').textContent = data.total_primes_found;
                document.getElementById('userNumbersProcessed').textContent = data.total_numbers_processed.toLocaleString();

                document.getElementById('userPanel').style.display = 'block';
                document.querySelector('.auth-buttons').style.display = 'none';
            }
        });
}
function login() {
    const username = document.getElementById('authUsername').value;
    const password = document.getElementById('authPassword').value;

    fetch('/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({username, password})
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                hideModal();
                updateUserPanel();
            } else {
                alert(data.error);
            }
        });
}

function register() {
    const username = document.getElementById('authUsername').value;
    const password = document.getElementById('authPassword').value;

    fetch('/register', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({username, password})
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                alert('Registrierung erfolgreich! Bitte anmelden.');
                hideModal();
            } else {
                alert(data.error);
            }
        });
}

function logout() {
    fetch('/logout')
        .then(() => {
            document.getElementById('userPanel').style.display = 'none';
            document.querySelector('.auth-buttons').style.display = 'flex';
        });
}

function toggleLeaderboard() {
    leaderboardVisible = !leaderboardVisible;
    const leaderboard = document.getElementById('leaderboard');
    const leaderboardBtn = document.getElementById("leaderboard-toggle");
    leaderboard.style.display = leaderboardVisible ? 'block' : 'none';
    leaderboardBtn.innerHTML = "Leaderboard anzeigen"
    if (leaderboardVisible) {
        updateLeaderboard();
        leaderboardBtn.innerHTML = "Leaderboard ausblenden"
    }
}
function updateLeaderboard() {
    fetch('/leaderboard')
        .then(response => response.json())
        .then(data => {
            const leaderboardList = document.getElementById('leaderboardList');
            leaderboardList.innerHTML = data.map((user, index) => `
                <li>
                    ${user.username}
                    <br>
                    <small>Geprüfte Zahlen: ${user.numbers_processed.toLocaleString()} | 
                    Gefundene Primzahlen: ${user.primes_found.toLocaleString()}</small>
                </li>
            `).join('');
        });
}

function updateHighestPrime() {
    fetch('/get_stats')
        .then(response => response.json())
        .then(data => {
            document.getElementById('highestPrime').textContent = data.highest_prime_found;
        });
}

setInterval(updateHighestPrime, 5000);

updateHighestPrime();

setInterval(() => {
    if (leaderboardVisible) {
        updateLeaderboard();
    }
}, 30000);

function updateBatchSize() {
    const size = parseInt(document.getElementById('batchSizeSelect').value);

    fetch('/set_batch_size', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({size})
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                updateStatus(`Batch-Größe auf ${size} Zahlen aktualisiert`);
                document.getElementById('currentBatchSize').textContent = size;

            } else {
                alert('Fehler beim Aktualisieren der Batch-Größe');
            }
        });
}

async function loadAllDiagrams() {
    const res = await fetch("/diagram_live_all");
    const data = await res.json();
    const container = document.getElementById("diagram-container");
    container.innerHTML = "";

    if (data.error) {
        container.innerText = "Fehler: " + data.error;
        return;
    }

    for (const [key, base64] of Object.entries(data)) {
        const title = document.createElement("h3");
        title.innerText = key.replace(/_/g, " ");
        const img = document.createElement("img");
        img.src = "data:image/png;base64," + base64;
        img.style.maxWidth = "100%";
        img.style.border = "1px solid #ccc";
        img.style.marginBottom = "20px";
        container.appendChild(title);
        container.appendChild(img);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    updateUserPanel();
    updateBatchSize();
});