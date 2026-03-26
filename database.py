import sqlite3
from sentence_transformers import SentenceTransformer
import json

model = SentenceTransformer('all-MiniLM-L6-v2')


DB_NAME = "policies.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS policies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        category TEXT,
        min_amount REAL,
        max_amount REAL,
        content TEXT,
        embedding TEXT
    )
    """)
    conn.commit()
    conn.close()

def seed_data():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    policies = [
        ("Damaged Item Refund (Low Value)", "refund", 0, 50,
         "If an item arrives damaged and order value is below $50, issue an instant refund."),
        ("Damaged Item Refund (High Value)", "refund", 50, 10000,
         "If an item arrives damaged and value exceeds $50, request photo evidence."),
    ]

    enriched = []

    for title, category, min_a, max_a, content in policies:
        embedding = model.encode(content).tolist()

        enriched.append((
            title,
            category,
            min_a,
            max_a,
            content,
            json.dumps(embedding)
        ))

    c.executemany("""
        INSERT INTO policies (title, category, min_amount, max_amount, content, embedding)
        VALUES (?, ?, ?, ?, ?, ?)
    """, enriched)

    conn.commit()
    conn.close()



def seed_data_doesnotWork():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    policies = [
        ("Damaged Item Refund (Low Value)", "refund", 0, 50,
         "If an item arrives damaged and order value is below $50, issue an instant refund. Return not required."),
        ("Damaged Item Refund (High Value)", "refund", 50, 10000,
         "If an item arrives damaged and value exceeds $50, request photo evidence and arrange return pickup."),
        ("Late Delivery Compensation", "delivery", 0, 10000,
         "If delivery is delayed more than 7 days, offer 10% refund or store credits.")
    ]

    embedding = model.encode(policies).tolist()

    c.executemany("""
        INSERT INTO policies ( title, category, min_amount, max_amount, content, embedding )
        VALUES (?, ?, ?, ?, ?, ?)
    """, policies)
    conn.commit()
    conn.close()

def add_policy_no_embedding(title, category, min_amount, max_amount, content):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        INSERT INTO policies (title, category, min_amount, max_amount, content)
        VALUES (?, ?, ?, ?, ?)
    """, (title, category, min_amount, max_amount, content))
    conn.commit()
    conn.close()


def add_policy(title, category, min_amount, max_amount, content):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    embedding = model.encode(content).tolist()

    c.execute("""
        INSERT INTO policies (title, category, min_amount, max_amount, content, embedding)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (title, category, min_amount, max_amount, content, json.dumps(embedding)))

    conn.commit()
    conn.close()


