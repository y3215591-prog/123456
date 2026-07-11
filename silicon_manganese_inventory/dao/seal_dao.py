from silicon_manganese_inventory.dao.database import DatabaseManager

SEAL_ALLOWED = {"status", "pre_inbound_id", "inbound_id", "outbound_id",
                "batch_no", "location_code"}


class SealDAO:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def create_batch(self, start_code, end_code, name=""):
        total = int(end_code) - int(start_code) + 1
        if total <= 0:
            raise ValueError(f"号段无效：起始编号 {start_code} 大于结束编号 {end_code}")
        if self._check_overlap(start_code, end_code):
            raise ValueError(f"号段 {start_code}~{end_code} 与已有号段重叠")
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO seal_batches (name, start_code, end_code, total_count) VALUES (?, ?, ?, ?)",
                (name, start_code, end_code, total),
            )
            batch_id = cursor.lastrowid
            codes = []
            fmt_len = len(start_code)
            for i in range(int(start_code), int(end_code) + 1):
                code = str(i).zfill(fmt_len)
                codes.append(code)
            conn.executemany(
                "INSERT INTO seal_numbers (seal_code, seal_batch_id) VALUES (?, ?)",
                [(code, batch_id) for code in codes],
            )
        return batch_id

    def _check_overlap(self, start_code, end_code):
        s = int(start_code)
        e = int(end_code)
        with self.db.get_connection() as conn:
            row = conn.execute(
                """SELECT COUNT(*) FROM seal_batches
                   WHERE ? >= CAST(start_code AS INTEGER)
                     AND ? <= CAST(end_code AS INTEGER)""",
                (e, s),
            ).fetchone()
        return row[0] > 0

    def get_batch(self, batch_id):
        with self.db.get_connection() as conn:
            return conn.execute(
                "SELECT * FROM seal_batches WHERE id=?", (batch_id,)
            ).fetchone()

    def list_batches(self):
        with self.db.get_connection() as conn:
            rows = conn.execute(
                """SELECT sb.*,
                   COALESCE(sn.used_count, 0) AS used_count
                   FROM seal_batches sb
                   LEFT JOIN (
                       SELECT seal_batch_id, COUNT(*) AS used_count FROM seal_numbers
                       WHERE status != 'unused' GROUP BY seal_batch_id
                   ) sn ON sb.id = sn.seal_batch_id
                   ORDER BY sb.import_date DESC"""
            ).fetchall()
        return rows

    def delete_batch(self, batch_id):
        with self.db.get_connection() as conn:
            used = conn.execute(
                "SELECT COUNT(*) FROM seal_numbers WHERE seal_batch_id=? AND status!='unused'",
                (batch_id,),
            ).fetchone()[0]
            if used > 0:
                raise ValueError("该号段已有铅封号被使用，无法删除")
            conn.execute("DELETE FROM seal_numbers WHERE seal_batch_id=?", (batch_id,))
            conn.execute("DELETE FROM seal_batches WHERE id=?", (batch_id,))

    def get_seals_by_batch(self, batch_id, status=None, offset=0, limit=None):
        with self.db.get_connection() as conn:
            base_sql = (
                "SELECT sn.*, sb.name AS batch_code, "
                "pio.order_no AS pre_inbound_order, "
                "io.order_no AS inbound_order, "
                "oo.order_no AS outbound_order "
                "FROM seal_numbers sn "
                "LEFT JOIN seal_batches sb ON sn.seal_batch_id=sb.id "
                "LEFT JOIN pre_inbound_orders pio ON sn.pre_inbound_id=pio.id "
                "LEFT JOIN inbound_orders io ON sn.inbound_id=io.id "
                "LEFT JOIN outbound_orders oo ON sn.outbound_id=oo.id "
                "WHERE sn.seal_batch_id=?"
            )
            params = [batch_id]
            count_sql = (
                "SELECT COUNT(*) FROM seal_numbers sn WHERE sn.seal_batch_id=?"
            )
            count_params = [batch_id]
            if status:
                count_sql += " AND sn.status=?"
                count_params.append(status)
                base_sql += " AND sn.status=?"
                params.append(status)
            if limit:
                total = conn.execute(count_sql, count_params).fetchone()[0]
                base_sql += " ORDER BY sn.seal_code LIMIT ? OFFSET ?"
                params.extend([limit, offset])
                return conn.execute(base_sql, params).fetchall(), total
            base_sql += " ORDER BY sn.seal_code"
            return conn.execute(base_sql, params).fetchall()

    def get_available_seals(self, batch_id, limit=None):
        with self.db.get_connection() as conn:
            sql = "SELECT * FROM seal_numbers WHERE seal_batch_id=? AND status='unused' ORDER BY seal_code"
            if limit:
                sql += f" LIMIT {int(limit)}"
            return conn.execute(sql, (batch_id,)).fetchall()

    def get_available_count(self, batch_id):
        with self.db.get_connection() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM seal_numbers WHERE seal_batch_id=? AND status='unused'",
                (batch_id,),
            ).fetchone()[0]

    def get_in_stock_seals(self, batch_no=None, location_code=None, spec_name=None):
        with self.db.get_connection() as conn:
            conditions = ["sn.status='in_stock'"]
            params = []
            if batch_no:
                conditions.append("sn.batch_no=?")
                params.append(batch_no)
            if location_code:
                conditions.append("sn.location_code=?")
                params.append(location_code)
            sql = (
                "SELECT sn.*, pio.date AS inbound_date "
                "FROM seal_numbers sn "
                "JOIN pre_inbound_orders pio ON sn.pre_inbound_id=pio.id "
                "WHERE " + " AND ".join(conditions) + " ORDER BY sn.seal_code"
            )
            return conn.execute(sql, params).fetchall()

    def get_unused_seals(self, batch_id=None):
        with self.db.get_connection() as conn:
            if batch_id:
                return conn.execute(
                    "SELECT * FROM seal_numbers WHERE status='unused' AND seal_batch_id=? ORDER BY seal_code",
                    (batch_id,),
                ).fetchall()
            return conn.execute(
                "SELECT * FROM seal_numbers WHERE status='unused' ORDER BY seal_code"
            ).fetchall()

    def get_used_seals(self):
        with self.db.get_connection() as conn:
            return conn.execute(
                """SELECT sn.*, sb.name AS batch_code,
                   pio.order_no AS pre_inbound_order,
                   io.order_no AS inbound_order,
                   oo.order_no AS outbound_order
                   FROM seal_numbers sn
                   LEFT JOIN seal_batches sb ON sn.seal_batch_id=sb.id
                   LEFT JOIN pre_inbound_orders pio ON sn.pre_inbound_id=pio.id
                   LEFT JOIN inbound_orders io ON sn.inbound_id=io.id
                   LEFT JOIN outbound_orders oo ON sn.outbound_id=oo.id
                   WHERE sn.status='shipped' ORDER BY sn.updated_at DESC"""
            ).fetchall()

    def update_seal_status_batch(self, seal_ids, new_status, conn=None, **kwargs):
        if not seal_ids:
            return
        safe_kwargs = {k: v for k, v in kwargs.items() if k in SEAL_ALLOWED}
        setters = ["status=?", "updated_at=datetime('now','localtime')"]
        values = [new_status]
        for key, val in safe_kwargs.items():
            setters.append(f"{key}=?")
            values.append(val)
        updates = [tuple(values + [sid]) for sid in seal_ids]
        if conn is not None:
            conn.executemany(
                f"UPDATE seal_numbers SET {', '.join(setters)} WHERE id=?",
                updates,
            )
        else:
            with self.db.get_connection() as conn:
                conn.executemany(
                    f"UPDATE seal_numbers SET {', '.join(setters)} WHERE id=?",
                    updates,
                )

    def update_seal_status(self, seal_ids, new_status, **kwargs):
        self.update_seal_status_batch(seal_ids, new_status, **kwargs)

    def get_seal_by_code(self, seal_code):
        with self.db.get_connection() as conn:
            return conn.execute(
                "SELECT * FROM seal_numbers WHERE seal_code=?", (seal_code,)
            ).fetchone()

    def trace_seal(self, seal_code):
        with self.db.get_connection() as conn:
            row = conn.execute(
                """SELECT sn.*, sb.name AS batch_name,
                   pio.order_no AS pre_inbound_no, pio.date AS pre_inbound_date,
                   pio.batch_no AS pre_inbound_batch,
                   io.order_no AS inbound_no, io.date AS inbound_date,
                   oo.order_no AS outbound_no, oo.date AS outbound_date,
                   oo.sales_order_no, c.name AS customer_name
                    FROM seal_numbers sn
                    LEFT JOIN seal_batches sb ON sn.seal_batch_id=sb.id
                    LEFT JOIN pre_inbound_orders pio ON sn.pre_inbound_id=pio.id
                   LEFT JOIN inbound_orders io ON sn.inbound_id=io.id
                   LEFT JOIN outbound_orders oo ON sn.outbound_id=oo.id
                   LEFT JOIN customers c ON oo.customer_id=c.id
                   WHERE sn.seal_code=?""",
                (seal_code,),
            ).fetchone()
        return row

    def import_range(self, start_int, end_int, batch_code=None):
        return self.create_batch(str(start_int), str(end_int), name=batch_code or "")

    def list_all(self, status=None, offset=0, limit=None):
        base_sql = (
            "SELECT sn.*, sb.name AS batch_code, "
            "pio.order_no AS pre_inbound_order, "
            "io.order_no AS inbound_order, "
            "oo.order_no AS outbound_order "
            "FROM seal_numbers sn "
            "LEFT JOIN seal_batches sb ON sn.seal_batch_id=sb.id "
            "LEFT JOIN pre_inbound_orders pio ON sn.pre_inbound_id=pio.id "
            "LEFT JOIN inbound_orders io ON sn.inbound_id=io.id "
            "LEFT JOIN outbound_orders oo ON sn.outbound_id=oo.id"
        )
        with self.db.get_connection() as conn:
            count_sql = "SELECT COUNT(*) FROM seal_numbers sn"
            params = []
            if status:
                count_sql += " WHERE sn.status=?"
                base_sql += " WHERE sn.status=?"
                params = [status]
            if limit:
                total = conn.execute(count_sql, params).fetchone()[0]
                base_sql += " ORDER BY sn.seal_code LIMIT ? OFFSET ?"
                params.extend([limit, offset])
                return conn.execute(base_sql, params).fetchall(), total
            base_sql += " ORDER BY sn.seal_code"
            return conn.execute(base_sql, params).fetchall()
