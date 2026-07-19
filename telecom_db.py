import os
import sqlite3
from typing import Dict, Any, Optional

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "telecom.db")

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(force: bool = False):
    """Initializes the database schema and seeds default records."""
    db_exists = os.path.exists(DB_FILE)
    
    if force and db_exists:
        try:
            os.remove(DB_FILE)
        except Exception as e:
            print(f"[DB ERROR] Could not remove existing DB file: {e}")
            # Alternate fallback: just drop tables
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS router_telemetry")
            cursor.execute("DROP TABLE IF EXISTS bills")
            cursor.execute("DROP TABLE IF EXISTS customers")
            conn.commit()
            conn.close()

    conn = get_db_connection()
    cursor = conn.cursor()

    # Create tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        plan_name TEXT NOT NULL,
        speed_tier TEXT NOT NULL,
        ip_address TEXT NOT NULL,
        status TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id TEXT NOT NULL,
        amount REAL NOT NULL,
        due_date TEXT NOT NULL,
        late_fee REAL DEFAULT 0,
        data_overage_fee REAL DEFAULT 0,
        status TEXT NOT NULL,
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS router_telemetry (
        customer_id TEXT PRIMARY KEY,
        snr_db REAL NOT NULL,
        packet_loss_pct REAL NOT NULL,
        port_status TEXT NOT NULL,
        is_online INTEGER NOT NULL DEFAULT 1,
        firmware_version TEXT NOT NULL,
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    )
    """)

    conn.commit()

    # Seed Default Customer data if not exists
    cursor.execute("SELECT id FROM customers WHERE id = ?", ("CUST-9948",))
    if not cursor.fetchone():
        print("[DB INFO] Seeding default customer records...")
        cursor.execute("""
        INSERT INTO customers (id, name, plan_name, speed_tier, ip_address, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """, ("CUST-9948", "Anurag Gupta", "GigaFiber Premium", "500 Mbps", "198.51.100.42", "Online (Degraded Signal)"))

        cursor.execute("""
        INSERT INTO bills (customer_id, amount, due_date, late_fee, data_overage_fee, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """, ("CUST-9948", 124.50, "July 21, 2026", 10.00, 29.50, "overdue"))

        # Default router is in a degraded state for the simulation loop
        cursor.execute("""
        INSERT INTO router_telemetry (customer_id, snr_db, packet_loss_pct, port_status, is_online, firmware_version)
        VALUES (?, ?, ?, ?, ?, ?)
        """, ("CUST-9948", 8.4, 14.5, "degraded", 1, "v4.2.1-r3"))

        conn.commit()
    
    conn.close()

def get_customer(customer_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_bill(customer_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM bills WHERE customer_id = ? ORDER BY id DESC LIMIT 1", (customer_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_router_telemetry(customer_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM router_telemetry WHERE customer_id = ?", (customer_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def update_router_telemetry(customer_id: str, snr_db: float, packet_loss_pct: float, port_status: str, is_online: int = 1):
    conn = get_db_connection()
    conn.execute("""
    UPDATE router_telemetry
    SET snr_db = ?, packet_loss_pct = ?, port_status = ?, is_online = ?
    WHERE customer_id = ?
    """, (snr_db, packet_loss_pct, port_status, is_online, customer_id))
    
    # Also update customer's status string accordingly
    status_str = "Online (Telemetry degraded)" if port_status == "degraded" else "Online (Optimal)"
    conn.execute("UPDATE customers SET status = ? WHERE id = ?", (status_str, customer_id))
    
    conn.commit()
    conn.close()

def reset_db():
    """Forces dropping and re-seeding the data back to simulation default."""
    print("[DB INFO] Resetting database back to initial telemetry values...")
    init_db(force=True)
