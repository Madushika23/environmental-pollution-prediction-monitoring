
"""
database.py

Manages database operations for the Environmental Pollution
Prediction and Monitoring System.

The database stores air, water, and soil prediction records
in separate tables:
    - air_readings
    - water_readings
    - soil_readings

Each table stores the relevant record ID, source, input values,
prediction result, and timestamp.
"""


import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pollution.db")

TABLES = {"air": "air_readings", "water": "water_readings", "soil": "soil_readings"}


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    for table in TABLES.values():
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {table} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                inputs TEXT NOT NULL,
                prediction TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
    conn.commit()
    conn.close()


def save_reading(domain, source, inputs: dict, prediction: dict):
    table = TABLES[domain]
    conn = get_connection()
    conn.execute(
        f"INSERT INTO {table} (source, inputs, prediction, timestamp) VALUES (?, ?, ?, ?)",
        (source, json.dumps(inputs), json.dumps(prediction), datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def get_history(domain, limit=100):
    table = TABLES[domain]
    conn = get_connection()
    if limit is None:
        rows = conn.execute(f"SELECT * FROM {table} ORDER BY id DESC").fetchall()
    else:
        rows = conn.execute(
            f"SELECT * FROM {table} ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    conn.close()

    return [{
        "id": row["id"],
        "domain": domain,
        "source": row["source"],
        "inputs": json.loads(row["inputs"]),
        "prediction": json.loads(row["prediction"]),
        "timestamp": row["timestamp"],
    } for row in rows]


def get_all_history(limit=200):
    """Used by the admin page -- combines all three tables for display."""
    result = []
    for domain in TABLES:
        result.extend(get_history(domain, limit=limit))
    result.sort(key=lambda r: r["timestamp"], reverse=True)
    return result


def clear_domain(domain):
    table = TABLES[domain]
    conn = get_connection()
    conn.execute(f"DELETE FROM {table}")
    conn.commit()
    conn.close()


def clear_all():
    conn = get_connection()
    for table in TABLES.values():
        conn.execute(f"DELETE FROM {table}")
    conn.commit()
    conn.close()


def delete_reading(domain, reading_id):
    table = TABLES[domain]
    conn = get_connection()
    conn.execute(f"DELETE FROM {table} WHERE id = ?", (reading_id,))
    conn.commit()
    conn.close()
