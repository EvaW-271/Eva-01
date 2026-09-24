import os
import sqlite3
from datetime import datetime, timezone

from flask import Flask, g, jsonify, request, send_from_directory

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(BASE_DIR, "data"))
DB_PATH = os.path.join(DATA_DIR, "guestbook.db")

NAME_MAX_LEN = 40
MESSAGE_MAX_LEN = 280

app = Flask(__name__, static_folder=None)


def get_db():
    if "db" not in g:
        os.makedirs(DATA_DIR, exist_ok=True)
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/api/messages", methods=["GET"])
def list_messages():
    db = get_db()
    rows = db.execute(
        "SELECT id, name, message, created_at FROM messages ORDER BY id DESC LIMIT 200"
    ).fetchall()
    return jsonify([dict(row) for row in rows])


@app.route("/api/messages", methods=["POST"])
def create_message():
    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name", "")).strip()
    message = str(payload.get("message", "")).strip()

    if not name or not message:
        return jsonify({"error": "name and message are required"}), 400
    if len(name) > NAME_MAX_LEN:
        return jsonify({"error": f"name must be at most {NAME_MAX_LEN} characters"}), 400
    if len(message) > MESSAGE_MAX_LEN:
        return jsonify({"error": f"message must be at most {MESSAGE_MAX_LEN} characters"}), 400

    created_at = datetime.now(timezone.utc).isoformat()
    db = get_db()
    cursor = db.execute(
        "INSERT INTO messages (name, message, created_at) VALUES (?, ?, ?)",
        (name, message, created_at),
    )
    db.commit()
    return jsonify(
        {"id": cursor.lastrowid, "name": name, "message": message, "created_at": created_at}
    ), 201


init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
