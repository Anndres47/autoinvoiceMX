import psycopg2
import os
import json
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        database=os.getenv('DB_NAME', 'autoinvoice'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD')
    )

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id SERIAL PRIMARY KEY,
            chat_id BIGINT,
            photo_path TEXT,
            vendor TEXT,
            folio TEXT,
            total DECIMAL,
            date TEXT,
            extra_data JSONB,
            status TEXT DEFAULT 'PENDING',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    conn.commit()
    cur.close()
    conn.close()

def add_ticket(chat_id, photo_path, vendor, folio, total, date, extra_data=None):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO tickets (chat_id, photo_path, vendor, folio, total, date, extra_data, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
    ''', (chat_id, photo_path, vendor, folio, total, date, json.dumps(extra_data) if extra_data else None, 'PENDING'))
    ticket_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return ticket_id

def update_ticket_status(ticket_id, status):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('UPDATE tickets SET status = %s WHERE id = %s', (status, ticket_id))
    conn.commit()
    cur.close()
    conn.close()

def get_user_history(chat_id, limit=5):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT vendor, folio, total, status, created_at 
        FROM tickets 
        WHERE chat_id = %s 
        ORDER BY created_at DESC 
        LIMIT %s
    ''', (chat_id, limit))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

if __name__ == '__main__':
    init_db()
    print("Database initialized.")
