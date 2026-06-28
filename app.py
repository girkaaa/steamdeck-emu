import socket, sqlite3, os, time
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
app.secret_key = "girkaaa-secret-key"

DB_PATH = os.path.join(os.path.dirname(__file__), "site.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS visits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT,
                page TEXT,
                timestamp REAL
            );
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page TEXT,
                author TEXT,
                text TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
        """)

init_db()

def record_visit(page):
    ip = request.remote_addr or "unknown"
    now = time.time()
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM visits WHERE ip=? AND page=?", (ip, page)).fetchone()
        if existing:
            conn.execute("UPDATE visits SET timestamp=? WHERE id=?", (now, existing["id"]))
        else:
            conn.execute("INSERT INTO visits (ip, page, timestamp) VALUES (?, ?, ?)", (ip, page, now))

def get_stats(page):
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) as c FROM visits WHERE page=?", (page,)).fetchone()["c"]
        cutoff = time.time() - 300
        online = conn.execute("SELECT COUNT(DISTINCT ip) as c FROM visits WHERE page=? AND timestamp>?",
                              (page, cutoff)).fetchone()["c"]
        return {"total": total, "online": online}

def get_comments(page):
    with get_db() as conn:
        return conn.execute("SELECT * FROM comments WHERE page=? ORDER BY created_at DESC", (page,)).fetchall()

@app.route("/")
def index():
    record_visit("/")
    return render_template("index.html", stats=get_stats("/"), comments=get_comments("/"), page="/")

@app.route("/emulators")
def emulators():
    record_visit("/emulators")
    return render_template("emulators.html", stats=get_stats("/emulators"), comments=get_comments("/emulators"), page="/emulators")

@app.route("/bios")
def bios():
    record_visit("/bios")
    return render_template("bios.html", stats=get_stats("/bios"), comments=get_comments("/bios"), page="/bios")

@app.route("/setup")
def setup():
    record_visit("/setup")
    return render_template("setup.html", stats=get_stats("/setup"), comments=get_comments("/setup"), page="/setup")

@app.route("/tips")
def tips():
    record_visit("/tips")
    return render_template("tips.html", stats=get_stats("/tips"), comments=get_comments("/tips"), page="/tips")

@app.route("/comment", methods=["POST"])
def add_comment():
    data = request.form
    page = data.get("page", "/")
    author = data.get("author", "Аноним").strip() or "Аноним"
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "Пустой комментарий"}), 400
    with get_db() as conn:
        conn.execute("INSERT INTO comments (page, author, text) VALUES (?, ?, ?)",
                     (page, author, text))
    return jsonify({"ok": True})

if __name__ == "__main__":
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print(f"Сайт girkaaa запущен!")
    print(f"Локально:    http://127.0.0.1:5000")
    print(f"В сети:      http://{local_ip}:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
