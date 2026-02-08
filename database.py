import sqlite3

DB_NAME = "ats.db"

def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def create_tables():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_code TEXT,
        title TEXT,
        department TEXT,
        created_date TEXT,
        closed_date TEXT,
        required_skills TEXT,
        status TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        phone TEXT,
        skills TEXT,
        stage TEXT,
        match_pct REAL,
        job_id INTEGER
    )
    """)

    conn.commit()
    conn.close()
