from mysql.connector import pooling
from typing import List
import asyncio
from datetime import datetime

# Global database connection pool
db_pool = None

def init_db_pool():
    """Initialize the database connection pool."""
    global db_pool
    db_pool = pooling.MySQLConnectionPool(
        pool_name="monitoring_pool",
        pool_size=20,
        host="localhost",
        user="root",
        password="",
        database="monitoring_system"
    )
    return db_pool

def get_connection():
    """Get a connection from the pool."""
    if db_pool is None:
        init_db_pool()
    return db_pool.get_connection()

def insert_logs(logs, notify_clients_func=None):
    """Inserts logs into the database and optionally notifies WebSocket clients."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        sql = """
        INSERT INTO activity_logs (pc_id, active_window, active_process, status, timestamp)
        VALUES (%s, %s, %s, %s, %s)
        """
        values = [(log.pc_id, log.active_window, log.active_process, log.status, log.timestamp) for log in logs]

        cursor.executemany(sql, values)  
        conn.commit()
        print(f"✅ {len(logs)} logs inserted successfully.")

        # Run WebSocket notification if provided
        if notify_clients_func:
            try:
                asyncio.run(notify_clients_func(logs))
            except RuntimeError:
                print("❌ Async function was called in an existing event loop.")

    except Exception as e:
        conn.rollback()
        print(f"❌ DB Error: {e}")

    finally:
        cursor.close()
        conn.close()

def fetch_logs(pc_id=None, start_time=None, end_time=None):
    """Fetch logs with optional filters."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = "SELECT * FROM activity_logs WHERE 1=1"
    values = []

    if pc_id:
        query += " AND pc_id = %s"
        values.append(pc_id)
    
    if start_time:
        query += " AND timestamp >= %s"
        values.append(start_time)
    
    if end_time:
        query += " AND timestamp <= %s"
        values.append(end_time)

    cursor.execute(query, values)
    logs = cursor.fetchall()

    cursor.close()
    conn.close()

    return logs