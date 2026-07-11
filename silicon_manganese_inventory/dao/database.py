import sqlite3
import shutil
import os
from contextlib import contextmanager
from silicon_manganese_inventory import config


class DatabaseManager:
    def __init__(self, db_path=None):
        self.db_path = db_path or config.DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self):
        with self.get_connection() as conn:
            conn.executescript(SCHEMA_SQL)
            cur = conn.execute(
                "SELECT COUNT(*) FROM pragma_table_info('customers') WHERE name='is_archived'"
            )
            row = cur.fetchone()
            if not row or row[0] == 0:
                conn.execute("ALTER TABLE customers ADD COLUMN is_archived INTEGER DEFAULT 0")
            cur2 = conn.execute(
                "SELECT COUNT(*) FROM pragma_table_info('sales_orders') WHERE name='particle_size'"
            )
            row2 = cur2.fetchone()
            if not row2 or row2[0] == 0:
                conn.execute("ALTER TABLE sales_orders ADD COLUMN particle_size TEXT DEFAULT ''")
        self._seed_defaults()

    def backup(self, backup_path):
        dst = os.path.abspath(backup_path).replace("'", "''")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with self.get_connection() as conn:
            conn.execute(f"VACUUM INTO '{dst}'")
        return dst.replace("''", "'")

    def restore(self, backup_path):
        src = os.path.abspath(backup_path)
        if not os.path.exists(src):
            raise FileNotFoundError(f"备份文件不存在: {src}")
        shutil.copy2(src, self.db_path)

    def _seed_defaults(self):
        with self.get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO warehouses (id, name, address) VALUES (1, '成品库', '')"
            )
            for code, name, wh_id in config.DEFAULT_LOCATIONS:
                conn.execute(
                    "INSERT OR IGNORE INTO locations (code, name, warehouse_id) VALUES (?, ?, ?)",
                    (code, name, wh_id),
                )
            for name, mn, si, remark in config.DEFAULT_SPECS:
                conn.execute(
                    "INSERT OR IGNORE INTO specs (name, mn_content, si_content, remark) VALUES (?, ?, ?, ?)",
                    (name, mn, si, remark),
                )
            for element, min_val, max_val in config.DEFAULT_LAB_STANDARDS:
                conn.execute(
                    "INSERT OR IGNORE INTO lab_standards (element, min_value, max_value) VALUES (?, ?, ?)",
                    (element, min_val, max_val),
                )

    def reset_business_data(self):
        with self.get_connection() as conn:
            conn.execute("DELETE FROM daily_shipments")
            conn.execute("DELETE FROM outbound_orders")
            conn.execute("DELETE FROM inbound_orders")
            conn.execute("DELETE FROM pre_inbound_orders")
            conn.execute("DELETE FROM lab_results")
            conn.execute("DELETE FROM seal_numbers")
            conn.execute("DELETE FROM seal_batches")
            conn.execute("DELETE FROM sales_orders")
            conn.execute("DELETE FROM customers")
            conn.execute("DELETE FROM suppliers")
            conn.execute("DELETE FROM operation_logs")


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS seal_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT DEFAULT '',
    start_code TEXT NOT NULL,
    end_code TEXT NOT NULL,
    total_count INTEGER NOT NULL DEFAULT 0,
    import_date TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS seal_numbers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seal_code TEXT UNIQUE NOT NULL,
    seal_batch_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'unused'
        CHECK (status IN ('unused','pre_allocated','in_stock','shipped')),
    pre_inbound_id INTEGER,
    inbound_id INTEGER,
    outbound_id INTEGER,
    batch_no TEXT DEFAULT '',
    location_code TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (seal_batch_id) REFERENCES seal_batches(id)
);

CREATE TABLE IF NOT EXISTS specs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    mn_content REAL DEFAULT 0,
    si_content REAL DEFAULT 0,
    remark TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS warehouses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    address TEXT DEFAULT '',
    remark TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name TEXT DEFAULT '',
    warehouse_id INTEGER DEFAULT 1,
    status TEXT DEFAULT 'active' CHECK (status IN ('active','inactive')),
    remark TEXT DEFAULT '',
    FOREIGN KEY (warehouse_id) REFERENCES warehouses(id)
);

CREATE TABLE IF NOT EXISTS factories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT DEFAULT '',
    name TEXT NOT NULL,
    remark TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE DEFAULT '',
    name TEXT NOT NULL,
    contact_person TEXT DEFAULT '',
    contact_phone TEXT DEFAULT '',
    address TEXT DEFAULT '',
    remark TEXT DEFAULT '',
    is_archived INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE DEFAULT '',
    name TEXT NOT NULL,
    contact_person TEXT DEFAULT '',
    contact_phone TEXT DEFAULT '',
    address TEXT DEFAULT '',
    remark TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS sales_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_no TEXT NOT NULL,
    line_no TEXT DEFAULT '',
    customer_code TEXT DEFAULT '',
    customer_name TEXT DEFAULT '',
    contract_ref TEXT DEFAULT '',
    contract_no TEXT DEFAULT '',
    material_code TEXT DEFAULT '',
    material_desc TEXT DEFAULT '',
    delivery_start TEXT DEFAULT '',
    delivery_end TEXT DEFAULT '',
    delivery_address TEXT DEFAULT '',
    quantity REAL DEFAULT 0,
    unit TEXT DEFAULT 'TO',
    factory_code TEXT DEFAULT '',
    factory_name TEXT DEFAULT '',
    pickup_method TEXT DEFAULT '',
    particle_size TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS pre_inbound_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_no TEXT UNIQUE NOT NULL,
    date TEXT NOT NULL,
    batch_no TEXT NOT NULL,
    spec_id INTEGER,
    quantity REAL NOT NULL DEFAULT 0,
    location_code TEXT DEFAULT '',
    seal_batch_id INTEGER,
    seal_start TEXT DEFAULT '',
    seal_end TEXT DEFAULT '',
    lab_status TEXT DEFAULT 'pending' CHECK (lab_status IN ('pending','tested')),
    operator TEXT DEFAULT '',
    remark TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (spec_id) REFERENCES specs(id),
    FOREIGN KEY (seal_batch_id) REFERENCES seal_batches(id)
);

CREATE TABLE IF NOT EXISTS lab_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pre_inbound_id INTEGER UNIQUE NOT NULL,
    mn_content REAL,
    si_content REAL,
    c_content REAL,
    s_content REAL,
    p_content REAL,
    mn_result TEXT DEFAULT '',
    si_result TEXT DEFAULT '',
    c_result TEXT DEFAULT '',
    s_result TEXT DEFAULT '',
    p_result TEXT DEFAULT '',
    overall_result TEXT DEFAULT '',
    test_date TEXT DEFAULT (datetime('now','localtime')),
    remark TEXT DEFAULT '',
    FOREIGN KEY (pre_inbound_id) REFERENCES pre_inbound_orders(id)
);

CREATE TABLE IF NOT EXISTS lab_standards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    element TEXT UNIQUE NOT NULL,
    min_value REAL DEFAULT 0,
    max_value REAL DEFAULT 0,
    remark TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS inbound_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_no TEXT UNIQUE NOT NULL,
    pre_inbound_id INTEGER UNIQUE NOT NULL,
    date TEXT NOT NULL,
    batch_no TEXT DEFAULT '',
    spec_id INTEGER,
    quantity REAL DEFAULT 0,
    location_code TEXT DEFAULT '',
    operator TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (pre_inbound_id) REFERENCES pre_inbound_orders(id),
    FOREIGN KEY (spec_id) REFERENCES specs(id)
);

CREATE TABLE IF NOT EXISTS outbound_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_no TEXT UNIQUE NOT NULL,
    date TEXT NOT NULL,
    customer_id INTEGER,
    sales_order_no TEXT DEFAULT '',
    contract_no TEXT DEFAULT '',
    plate_no TEXT DEFAULT '',
    spec_id INTEGER,
    quantity REAL DEFAULT 0,
    batch_nos TEXT DEFAULT '',
    seal_start TEXT DEFAULT '',
    seal_end TEXT DEFAULT '',
    operator TEXT DEFAULT '',
    remark TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (spec_id) REFERENCES specs(id)
);

CREATE TABLE IF NOT EXISTS daily_shipments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seq_no INTEGER DEFAULT 0,
    shipment_date TEXT DEFAULT '',
    plate_no TEXT DEFAULT '',
    customer_code TEXT DEFAULT '',
    customer_name TEXT DEFAULT '',
    sales_order_no TEXT DEFAULT '',
    material_name TEXT DEFAULT '',
    spec TEXT DEFAULT '',
    batch_no TEXT DEFAULT '',
    load_quantity REAL DEFAULT 0,
    gross_weight REAL DEFAULT 0,
    tare_weight REAL DEFAULT 0,
    net_weight REAL DEFAULT 0,
    customer_received_weight REAL,
    seal_codes TEXT DEFAULT '',
    remark TEXT DEFAULT '',
    outbound_id INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (outbound_id) REFERENCES outbound_orders(id)
);

CREATE TABLE IF NOT EXISTS operation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_type TEXT NOT NULL DEFAULT '',
    target_table TEXT DEFAULT '',
    target_id INTEGER,
    detail TEXT DEFAULT '',
    operator TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_seal_status ON seal_numbers(status);
CREATE INDEX IF NOT EXISTS idx_seal_batch ON seal_numbers(seal_batch_id);
CREATE INDEX IF NOT EXISTS idx_seal_pre_inbound ON seal_numbers(pre_inbound_id);
CREATE INDEX IF NOT EXISTS idx_seal_inbound ON seal_numbers(inbound_id);
CREATE INDEX IF NOT EXISTS idx_seal_outbound ON seal_numbers(outbound_id);
CREATE INDEX IF NOT EXISTS idx_seal_location ON seal_numbers(location_code);
CREATE INDEX IF NOT EXISTS idx_seal_batch_no ON seal_numbers(batch_no);
CREATE INDEX IF NOT EXISTS idx_seal_code_order ON seal_numbers(seal_code);
CREATE INDEX IF NOT EXISTS idx_pre_inbound_date ON pre_inbound_orders(date);
CREATE INDEX IF NOT EXISTS idx_outbound_date ON outbound_orders(date);
CREATE INDEX IF NOT EXISTS idx_outbound_sales_order ON outbound_orders(sales_order_no);
CREATE INDEX IF NOT EXISTS idx_daily_shipment_date ON daily_shipments(shipment_date);
CREATE INDEX IF NOT EXISTS idx_sales_order_no ON sales_orders(order_no);
"""
