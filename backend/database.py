import os
import sqlite3
import datetime
from typing import List

# Database configuration
DB_FILE = os.getenv("DATABASE_PATH", "ig_int_vault.db")

def init_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS cases 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS findings 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, case_name TEXT, category TEXT, label TEXT, value TEXT, timestamp TEXT)''')
    conn.commit()
    conn.close()

def create_case(case_name: str) -> bool:
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    success = False
    try:
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO cases (name, created_at) VALUES (?, ?)", (case_name.strip(), ts))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        pass
    conn.close()
    return success

def get_cases() -> List[str]:
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT name FROM cases ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

def save_finding(case_name: str, category: str, label: str, value: str):
    if not case_name or case_name == "-- Select Active Case --":
        return
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO findings (case_name, category, label, value, timestamp) VALUES (?, ?, ?, ?, ?)",
              (case_name, category, label, str(value), ts))
    conn.commit()
    conn.close()

def get_findings(case_name: str) -> List[dict]:
    if not case_name or case_name == "-- Select Active Case --":
        return []
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT category, label, value, timestamp FROM findings WHERE case_name = ? ORDER BY id DESC", (case_name,))
    rows = c.fetchall()
    conn.close()
    return [{"category": r[0], "label": r[1], "value": r[2], "timestamp": r[3]} for r in rows]
