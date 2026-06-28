import socket, os, time
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "girkaaa-secret-key")

USE_PG = bool(os.environ.get("DATABASE_URL", ""))

if USE_PG:
    import psycopg2, psycopg2.extras

    def get_db():
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        conn.autocommit = True
        return conn

    def init_db():
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS visits (
                    id SERIAL PRIMARY KEY,
                    ip TEXT, page TEXT,
                    timestamp DOUBLE PRECISION
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS comments (
                    id SERIAL PRIMARY KEY,
                    page TEXT, author TEXT, text TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            cur.close()

    def query(sql, params=()):
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql.replace("?", "%s"), params)
        rows = [dict(r) for r in cur.fetchall()]
        cur.close()
        conn.close()
        return rows

    def execute(sql, params=()):
        conn = get_db()
        cur = conn.cursor()
        cur.execute(sql.replace("?", "%s"), params)
        cur.close()
        conn.close()

else:
    import sqlite3

    def get_db():
        conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), "site.db"))
        conn.row_factory = sqlite3.Row
        return conn

    def init_db():
        with get_db() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS visits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip TEXT, page TEXT, timestamp REAL
                );
                CREATE TABLE IF NOT EXISTS comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    page TEXT, author TEXT, text TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );
            """)

    def query(sql, params=()):
        with get_db() as conn:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]

    def execute(sql, params=()):
        with get_db() as conn:
            conn.execute(sql, params)

init_db()

def record_visit(page):
    ip = request.remote_addr or "unknown"
    now = time.time()
    existing = query("SELECT id FROM visits WHERE ip=? AND page=?", (ip, page))
    if existing:
        execute("UPDATE visits SET timestamp=? WHERE id=?", (now, existing[0]["id"]))
    else:
        execute("INSERT INTO visits (ip, page, timestamp) VALUES (?, ?, ?)", (ip, page, now))

def get_stats(page):
    total = query("SELECT COUNT(*) as c FROM visits WHERE page=?", (page,))[0]["c"]
    cutoff = time.time() - 300
    online = query("SELECT COUNT(DISTINCT ip) as c FROM visits WHERE page=? AND timestamp>?", (page, cutoff))[0]["c"]
    return {"total": total, "online": online}

def get_comments(page):
    return query("SELECT * FROM comments WHERE page=? ORDER BY created_at DESC", (page,))

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
    text = request.form.get("text", "").strip()
    if not text:
        return jsonify({"error": "Пустой комментарий"}), 400
    execute("INSERT INTO comments (page, author, text) VALUES (?, ?, ?)",
            (request.form.get("page", "/"), request.form.get("author", "Аноним").strip() or "Аноним", text))
    return jsonify({"ok": True})

@app.route("/admin/delete-comment", methods=["POST"])
def delete_comment():
    if request.form.get("key") != "girkaaa-adm":
        return jsonify({"error": "no"}), 403
    cid = request.form.get("id")
    if not cid:
        return jsonify({"error": "no id"}), 400
    execute("DELETE FROM comments WHERE id=?", (cid,))
    return jsonify({"ok": True, "deleted": cid})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    print(f"Сайт girkaaa запущен! http://0.0.0.0:{port} | DB: {'PostgreSQL' if USE_PG else 'SQLite'}")
    app.run(host="0.0.0.0", port=port, debug=debug)
