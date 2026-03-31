import os
import datetime
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

def get_conn():
    url = os.getenv("DATABASE_URL", "")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return psycopg2.connect(url)

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            entry_type TEXT,
            status TEXT,
            rating INTEGER,
            poster_url TEXT,
            added_on TEXT
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

def add_entry(title, entry_type, status, rating, poster_url):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO entries (title, entry_type, status, rating, poster_url, added_on) VALUES (%s, %s, %s, %s, %s, %s)",
        (title, entry_type, status, rating, poster_url, str(datetime.date.today()))
    )
    conn.commit()
    cur.close()
    conn.close()

def get_all():
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM entries ORDER BY id DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]

def update_entry(entry_id, status, rating):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE entries SET status = %s, rating = %s WHERE id = %s",
        (status, rating, entry_id)
    )
    conn.commit()
    cur.close()
    conn.close()

def delete_entry(entry_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM entries WHERE id = %s", (entry_id,))
    conn.commit()
    cur.close()
    conn.close()

init_db()