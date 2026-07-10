import random
from datetime import datetime
from silicon_manganese_inventory.dao.database import DatabaseManager

INBOUND_PRE_ALLOWED = {"batch_no", "quantity", "location_code", "seal_batch_id",
                       "seal_start", "seal_end", "spec_id", "operator", "remark",
                       "date", "lab_status"}


class InboundDAO:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def _gen_order_no(self, prefix):
        now = datetime.now()
        suffix = f"{now.microsecond // 1000:03d}{random.randint(0, 9)}"
        return f"{prefix}{now.strftime('%y%m%d%H%M%S')}{suffix}"

    def create_pre_inbound(self, **kwargs):
        order_no = kwargs.get("order_no") or self._gen_order_no("PI")
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO pre_inbound_orders
                   (order_no, date, batch_no, spec_id, quantity, location_code,
                    seal_batch_id, seal_start, seal_end, operator, remark)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (order_no, kwargs.get("date", ""), kwargs.get("batch_no", ""),
                 kwargs.get("spec_id"), kwargs.get("quantity", 0),
                 kwargs.get("location_code", ""), kwargs.get("seal_batch_id"),
                 kwargs.get("seal_start", ""), kwargs.get("seal_end", ""),
                 kwargs.get("operator", ""), kwargs.get("remark", "")),
            )
            return cursor.lastrowid

    def update_pre_inbound(self, pre_id, **kwargs):
        safe = {k: v for k, v in kwargs.items() if k in INBOUND_PRE_ALLOWED}
        if not safe:
            return
        with self.db.get_connection() as conn:
            sets = [f"{k}=?" for k in safe]
            params = list(safe.values())
            sets.append("updated_at=datetime('now','localtime')")
            params.append(pre_id)
            conn.execute(
                f"UPDATE pre_inbound_orders SET {', '.join(sets)} WHERE id=?",
                params,
            )

    def get_pre_inbound(self, pre_id):
        with self.db.get_connection() as conn:
            return conn.execute(
                "SELECT * FROM pre_inbound_orders WHERE id=?", (pre_id,)
            ).fetchone()

    def get_pre_inbound_by_order_no(self, order_no):
        with self.db.get_connection() as conn:
            return conn.execute(
                "SELECT * FROM pre_inbound_orders WHERE order_no=?", (order_no,)
            ).fetchone()

    def delete_pre_inbound(self, pre_id):
        with self.db.get_connection() as conn:
            conn.execute(
                """UPDATE seal_numbers SET status='unused', pre_inbound_id=NULL,
                   batch_no='', location_code='', inbound_id=NULL,
                   updated_at=datetime('now','localtime')
                   WHERE pre_inbound_id=?""",
                (pre_id,),
            )
            conn.execute("DELETE FROM lab_results WHERE pre_inbound_id=?", (pre_id,))
            conn.execute("DELETE FROM pre_inbound_orders WHERE id=?", (pre_id,))

    def list_pre_inbound(self, date_from=None, date_to=None, batch_no=None,
                         location_code=None, lab_status=None, keyword=None,
                         inbound_status=None):
        with self.db.get_connection() as conn:
            conditions = []
            params = []
            if date_from:
                conditions.append("pio.date>=?")
                params.append(date_from)
            if date_to:
                conditions.append("pio.date<=?")
                params.append(date_to)
            if batch_no:
                conditions.append("pio.batch_no LIKE ?")
                params.append(f"%{batch_no}%")
            if location_code:
                conditions.append("pio.location_code LIKE ?")
                params.append(f"%{location_code}%")
            if lab_status:
                conditions.append("pio.lab_status=?")
                params.append(lab_status)
            if inbound_status == "confirmed":
                conditions.append("io.id IS NOT NULL")
            elif inbound_status == "unconfirmed":
                conditions.append("io.id IS NULL")
            if keyword:
                conditions.append(
                    "(pio.order_no LIKE ? OR pio.seal_start LIKE ? OR pio.seal_end LIKE ?)")
                kw = f"%{keyword}%"
                params.extend([kw, kw, kw])
            sql = (
                "SELECT pio.*, CASE WHEN io.id IS NOT NULL THEN 'confirmed' ELSE 'unconfirmed' END AS inbound_status "
                "FROM pre_inbound_orders pio "
                "LEFT JOIN inbound_orders io ON pio.id = io.pre_inbound_id"
            )
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
            sql += " ORDER BY pio.date DESC, pio.id DESC"
            return conn.execute(sql, params).fetchall()

    def create_inbound(self, pre_inbound_id, conn=None, **kwargs):
        order_no = kwargs.pop("order_no", None) or self._gen_order_no("IN")
        location_code = kwargs.pop("location_code", None)
        if conn is not None:
            row = conn.execute(
                "SELECT * FROM pre_inbound_orders WHERE id=?",
                (pre_inbound_id,)
            ).fetchone()
            if not row:
                raise ValueError(f"预入库单 {pre_inbound_id} 不存在")
            date_val = kwargs.get("date", datetime.now().strftime("%Y-%m-%d"))
            cursor = conn.execute(
                """INSERT INTO inbound_orders
                   (order_no, pre_inbound_id, date, batch_no, spec_id,
                    quantity, location_code, operator)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (order_no, pre_inbound_id, date_val,
                 row["batch_no"], row["spec_id"], row["quantity"],
                 location_code or row["location_code"],
                 kwargs.get("operator", "")),
            )
            return cursor.lastrowid
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM pre_inbound_orders WHERE id=?",
                (pre_inbound_id,)
            ).fetchone()
            if not row:
                raise ValueError(f"预入库单 {pre_inbound_id} 不存在")
            date_val = kwargs.get("date", datetime.now().strftime("%Y-%m-%d"))
            cursor = conn.execute(
                """INSERT INTO inbound_orders
                   (order_no, pre_inbound_id, date, batch_no, spec_id,
                    quantity, location_code, operator)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (order_no, pre_inbound_id, date_val,
                 row["batch_no"], row["spec_id"], row["quantity"],
                 location_code or row["location_code"],
                 kwargs.get("operator", "")),
            )
            return cursor.lastrowid

    def get_inbound(self, inbound_id):
        with self.db.get_connection() as conn:
            return conn.execute(
                "SELECT * FROM inbound_orders WHERE id=?", (inbound_id,)
            ).fetchone()

    def list_inbound(self, date_from=None, date_to=None, batch_no=None):
        with self.db.get_connection() as conn:
            conditions = []
            params = []
            if date_from:
                conditions.append("date>=?")
                params.append(date_from)
            if date_to:
                conditions.append("date<=?")
                params.append(date_to)
            if batch_no:
                conditions.append("batch_no LIKE ?")
                params.append(f"%{batch_no}%")
            sql = "SELECT * FROM inbound_orders"
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
            sql += " ORDER BY date DESC, id DESC"
            return conn.execute(sql, params).fetchall()
