from silicon_manganese_inventory.dao.database import DatabaseManager


def _safe_update(conn, table, record_id, allowed_columns, **kwargs):
    safe = {k: v for k, v in kwargs.items() if k in allowed_columns}
    if not safe:
        return
    sets = [f"{k}=?" for k in safe]
    params = list(safe.values()) + [record_id]
    conn.execute(f"UPDATE {table} SET {', '.join(sets)} WHERE id=?", params)


class CustomerDAO:
    _ALLOWED = {"code", "name", "contact_person", "contact_phone", "address", "remark"}

    def __init__(self, db: DatabaseManager):
        self.db = db

    def create(self, **kwargs):
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO customers (code, name, contact_person, contact_phone, address, remark) VALUES (?, ?, ?, ?, ?, ?)",
                (kwargs.get("code", ""), kwargs.get("name", ""),
                 kwargs.get("contact_person", ""), kwargs.get("contact_phone", ""),
                 kwargs.get("address", ""), kwargs.get("remark", "")),
            )
            return cursor.lastrowid

    def update(self, customer_id, **kwargs):
        with self.db.get_connection() as conn:
            _safe_update(conn, "customers", customer_id, self._ALLOWED, **kwargs)

    def delete(self, customer_id):
        with self.db.get_connection() as conn:
            conn.execute("DELETE FROM customers WHERE id=?", (customer_id,))

    def get(self, customer_id):
        with self.db.get_connection() as conn:
            return conn.execute("SELECT * FROM customers WHERE id=?", (customer_id,)).fetchone()

    def get_by_code(self, code):
        with self.db.get_connection() as conn:
            return conn.execute("SELECT * FROM customers WHERE code=?", (code,)).fetchone()

    def list(self, keyword=None):
        with self.db.get_connection() as conn:
            if keyword:
                kw = f"%{keyword}%"
                return conn.execute(
                    "SELECT * FROM customers WHERE name LIKE ? OR code LIKE ? ORDER BY code",
                    (kw, kw),
                ).fetchall()
            return conn.execute("SELECT * FROM customers ORDER BY code").fetchall()


class SupplierDAO:
    _ALLOWED = {"code", "name", "contact_person", "contact_phone", "address", "remark"}

    def __init__(self, db: DatabaseManager):
        self.db = db

    def create(self, **kwargs):
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO suppliers (code, name, contact_person, contact_phone, address, remark) VALUES (?, ?, ?, ?, ?, ?)",
                (kwargs.get("code", ""), kwargs.get("name", ""),
                 kwargs.get("contact_person", ""), kwargs.get("contact_phone", ""),
                 kwargs.get("address", ""), kwargs.get("remark", "")),
            )
            return cursor.lastrowid

    def update(self, supplier_id, **kwargs):
        with self.db.get_connection() as conn:
            _safe_update(conn, "suppliers", supplier_id, self._ALLOWED, **kwargs)

    def delete(self, supplier_id):
        with self.db.get_connection() as conn:
            conn.execute("DELETE FROM suppliers WHERE id=?", (supplier_id,))

    def get(self, supplier_id):
        with self.db.get_connection() as conn:
            return conn.execute("SELECT * FROM suppliers WHERE id=?", (supplier_id,)).fetchone()

    def list(self, keyword=None):
        with self.db.get_connection() as conn:
            if keyword:
                kw = f"%{keyword}%"
                return conn.execute(
                    "SELECT * FROM suppliers WHERE name LIKE ? OR code LIKE ? ORDER BY code",
                    (kw, kw),
                ).fetchall()
            return conn.execute("SELECT * FROM suppliers ORDER BY code").fetchall()


class LocationDAO:
    _ALLOWED = {"code", "name", "warehouse_id", "remark"}

    def __init__(self, db: DatabaseManager):
        self.db = db

    def create(self, code, name="", warehouse_id=1, remark=""):
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO locations (code, name, warehouse_id, remark) VALUES (?, ?, ?, ?)",
                (code, name, warehouse_id, remark),
            )
            return cursor.lastrowid

    def get_or_create(self, code, warehouse_id=1):
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM locations WHERE code=?", (code,)
            ).fetchone()
            if row:
                return row["code"]
            conn.execute(
                "INSERT OR IGNORE INTO locations (code, name, warehouse_id) VALUES (?, ?, ?)",
                (code, f"{code}库位", warehouse_id),
            )
            return code

    def get_by_code(self, code):
        with self.db.get_connection() as conn:
            return conn.execute(
                "SELECT * FROM locations WHERE code=?", (code,)
            ).fetchone()

    def update(self, location_id, **kwargs):
        with self.db.get_connection() as conn:
            _safe_update(conn, "locations", location_id, self._ALLOWED, **kwargs)

    def delete(self, location_id):
        with self.db.get_connection() as conn:
            code_row = conn.execute("SELECT code FROM locations WHERE id=?", (location_id,)).fetchone()
            if code_row:
                has = conn.execute(
                    "SELECT COUNT(*) FROM seal_numbers WHERE location_code=? AND status='in_stock'",
                    (code_row["code"],),
                ).fetchone()[0]
                if has > 0:
                    raise ValueError("该库位存在库存记录，无法删除")
                conn.execute("DELETE FROM locations WHERE id=?", (location_id,))

    def get(self, location_id):
        with self.db.get_connection() as conn:
            return conn.execute("SELECT * FROM locations WHERE id=?", (location_id,)).fetchone()

    def list(self, warehouse_id=None, code_prefix=None):
        with self.db.get_connection() as conn:
            base_sql = (
                "SELECT l.*, w.name AS warehouse_name, "
                "COALESCE((SELECT SUM(pio.quantity) FROM pre_inbound_orders pio "
                "JOIN inbound_orders io ON pio.id=io.pre_inbound_id "
                "WHERE pio.location_code=l.code), 0) AS used_qty "
                "FROM locations l LEFT JOIN warehouses w ON l.warehouse_id=w.id"
            )
            conditions = []
            params = []
            if warehouse_id:
                conditions.append("l.warehouse_id=?")
                params.append(warehouse_id)
            if code_prefix:
                conditions.append("l.code LIKE ?")
                params.append(f"{code_prefix}%")
            where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
            return conn.execute(
                base_sql + where_clause + " ORDER BY l.code",
                params,
            ).fetchall()

    def get_available_qty(self, code):
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM seal_numbers WHERE location_code=? AND status='in_stock'",
                (code,),
            ).fetchone()
            return row[0]


class SpecDAO:
    _ALLOWED = {"name", "mn_content", "si_content", "remark"}

    def __init__(self, db: DatabaseManager):
        self.db = db

    def create(self, name, mn_content=0, si_content=0, remark=""):
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO specs (name, mn_content, si_content, remark) VALUES (?, ?, ?, ?)",
                (name, mn_content, si_content, remark),
            )
            return cursor.lastrowid

    def update(self, spec_id, **kwargs):
        with self.db.get_connection() as conn:
            _safe_update(conn, "specs", spec_id, self._ALLOWED, **kwargs)

    def delete(self, spec_id):
        with self.db.get_connection() as conn:
            has = conn.execute(
                "SELECT COUNT(*) FROM pre_inbound_orders WHERE spec_id=?",
                (spec_id,),
            ).fetchone()[0]
            if has > 0:
                raise ValueError("该规格存在业务记录，无法删除")
            conn.execute("DELETE FROM specs WHERE id=?", (spec_id,))

    def get(self, spec_id):
        with self.db.get_connection() as conn:
            return conn.execute("SELECT * FROM specs WHERE id=?", (spec_id,)).fetchone()

    def get_by_name(self, name):
        with self.db.get_connection() as conn:
            return conn.execute("SELECT * FROM specs WHERE name=?", (name,)).fetchone()

    def list(self, keyword=None):
        with self.db.get_connection() as conn:
            if keyword:
                kw = f"%{keyword}%"
                return conn.execute(
                    "SELECT * FROM specs WHERE name LIKE ? ORDER BY name",
                    (kw,),
                ).fetchall()
            return conn.execute("SELECT * FROM specs ORDER BY name").fetchall()


class WarehouseDAO:
    _ALLOWED = {"name", "address", "remark"}

    def __init__(self, db: DatabaseManager):
        self.db = db

    def create(self, name, address="", remark=""):
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO warehouses (name, address, remark) VALUES (?, ?, ?)",
                (name, address, remark),
            )
            return cursor.lastrowid

    def update(self, warehouse_id, **kwargs):
        with self.db.get_connection() as conn:
            _safe_update(conn, "warehouses", warehouse_id, self._ALLOWED, **kwargs)

    def delete(self, warehouse_id):
        with self.db.get_connection() as conn:
            has = conn.execute(
                "SELECT COUNT(*) FROM seal_numbers WHERE location_code IN (SELECT code FROM locations WHERE warehouse_id=?) AND status='in_stock'",
                (warehouse_id,),
            ).fetchone()[0]
            if has > 0:
                raise ValueError("该仓库存在库存记录，无法删除")
            conn.execute("DELETE FROM warehouses WHERE id=?", (warehouse_id,))

    def list(self):
        with self.db.get_connection() as conn:
            return conn.execute("SELECT * FROM warehouses ORDER BY id").fetchall()


class SalesOrderDAO:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def create(self, **kwargs):
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO sales_orders
                   (order_no, line_no, customer_code, customer_name, contract_ref,
                    contract_no, material_code, material_desc, delivery_start,
                    delivery_end, delivery_address, quantity, unit, factory_code,
                    factory_name, pickup_method)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (kwargs.get("order_no", ""), kwargs.get("line_no", ""),
                 kwargs.get("customer_code", ""), kwargs.get("customer_name", ""),
                 kwargs.get("contract_ref", ""), kwargs.get("contract_no", ""),
                 kwargs.get("material_code", ""), kwargs.get("material_desc", ""),
                 kwargs.get("delivery_start", ""), kwargs.get("delivery_end", ""),
                 kwargs.get("delivery_address", ""), kwargs.get("quantity", 0),
                 kwargs.get("unit", "TO"), kwargs.get("factory_code", ""),
                 kwargs.get("factory_name", ""), kwargs.get("pickup_method", "")),
            )
            return cursor.lastrowid

    def get_by_order_no(self, order_no):
        with self.db.get_connection() as conn:
            return conn.execute(
                "SELECT * FROM sales_orders WHERE order_no=? ORDER BY id",
                (order_no,),
            ).fetchone()

    def list(self, keyword=None, customer_code=None):
        with self.db.get_connection() as conn:
            conditions = []
            params = []
            if keyword:
                conditions.append("(order_no LIKE ? OR customer_name LIKE ? OR material_desc LIKE ?)")
                kw = f"%{keyword}%"
                params.extend([kw, kw, kw])
            if customer_code:
                conditions.append("customer_code=?")
                params.append(customer_code)
            sql = "SELECT * FROM sales_orders"
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
            sql += " ORDER BY order_no DESC"
            return conn.execute(sql, params).fetchall()

    def delete_all(self):
        with self.db.get_connection() as conn:
            conn.execute("DELETE FROM sales_orders")


class DailyShipmentDAO:
    _ALLOWED = {"seq_no", "shipment_date", "plate_no", "customer_code",
                "customer_name", "sales_order_no", "material_name", "spec",
                "batch_no", "load_quantity", "gross_weight", "tare_weight",
                "net_weight", "customer_received_weight", "seal_codes", "remark",
                "outbound_id"}

    def __init__(self, db: DatabaseManager):
        self.db = db

    def create(self, **kwargs):
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO daily_shipments
                   (seq_no, shipment_date, plate_no, customer_code, customer_name,
                    sales_order_no, material_name, spec, batch_no, load_quantity,
                    gross_weight, tare_weight, net_weight, customer_received_weight,
                    seal_codes, remark, outbound_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (kwargs.get("seq_no", 0), kwargs.get("shipment_date", ""),
                 kwargs.get("plate_no", ""), kwargs.get("customer_code", ""),
                 kwargs.get("customer_name", ""), kwargs.get("sales_order_no", ""),
                 kwargs.get("material_name", ""), kwargs.get("spec", ""),
                 kwargs.get("batch_no", ""), kwargs.get("load_quantity", 0),
                 kwargs.get("gross_weight", 0), kwargs.get("tare_weight", 0),
                 kwargs.get("net_weight", 0),
                 kwargs.get("customer_received_weight"),
                 kwargs.get("seal_codes", ""), kwargs.get("remark", ""),
                 kwargs.get("outbound_id")),
            )
            return cursor.lastrowid

    def update(self, shipment_id, **kwargs):
        with self.db.get_connection() as conn:
            _safe_update(conn, "daily_shipments", shipment_id, self._ALLOWED, **kwargs)

    def delete(self, shipment_id):
        with self.db.get_connection() as conn:
            conn.execute("DELETE FROM daily_shipments WHERE id=?", (shipment_id,))

    def get(self, shipment_id):
        with self.db.get_connection() as conn:
            return conn.execute("SELECT * FROM daily_shipments WHERE id=?", (shipment_id,)).fetchone()

    def list(self, date_from=None, date_to=None, customer_code=None,
             sales_order_no=None, plate_no=None):
        with self.db.get_connection() as conn:
            conditions = []
            params = []
            if date_from:
                conditions.append("shipment_date>=?")
                params.append(date_from)
            if date_to:
                conditions.append("shipment_date<=?")
                params.append(date_to)
            if customer_code:
                conditions.append("customer_code LIKE ?")
                params.append(f"%{customer_code}%")
            if sales_order_no:
                conditions.append("sales_order_no LIKE ?")
                params.append(f"%{sales_order_no}%")
            if plate_no:
                conditions.append("plate_no LIKE ?")
                params.append(f"%{plate_no}%")
            sql = "SELECT * FROM daily_shipments"
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
            sql += " ORDER BY shipment_date DESC, seq_no"
            return conn.execute(sql, params).fetchall()

    def get_max_seq_no(self):
        with self.db.get_connection() as conn:
            row = conn.execute("SELECT MAX(seq_no) FROM daily_shipments").fetchone()
            return row[0] or 0
