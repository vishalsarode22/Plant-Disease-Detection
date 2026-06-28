import sqlite3
import os
from datetime import datetime

DB_PATH = 'leafmitra.db'


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_path TEXT NOT NULL,
            label TEXT NOT NULL,
            confidence REAL NOT NULL,
            is_unknown INTEGER DEFAULT 0,
            gemini_text TEXT,
            timestamp TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


def save_prediction(image_path, label, confidence, is_unknown, gemini_text=''):
    conn = get_db()
    conn.execute(
        '''INSERT INTO predictions (image_path, label, confidence, is_unknown, gemini_text, timestamp)
           VALUES (?, ?, ?, ?, ?, ?)''',
        (image_path, label, confidence, int(is_unknown), gemini_text,
         datetime.now().strftime('%B %d, %Y %I:%M %p'))
    )
    conn.commit()
    conn.close()


def get_history(limit=20):
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM predictions ORDER BY id DESC LIMIT ?', (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_prediction_by_filename(filename):
    conn = get_db()
    row = conn.execute(
        'SELECT * FROM predictions WHERE image_path = ? ORDER BY id DESC LIMIT 1',
        (filename,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def __init__():
    pass
