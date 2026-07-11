from datetime import datetime
from silicon_manganese_inventory.dao.database import DatabaseManager


class OutboundDAO:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def _gen_order_no(self):
        now = datetime.now()
        return f"PO{now.strftime('%y%m%d')}{now.microsecond // 1000:03d}"

    def create_outbound(self, **kwargs):
        order_no = kwargs.pop("order_no", None) or self._gen_order_no()
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO outbound_orders
                   (order_no, date, customer_id, sales_order_no, contract_no, plate_no,
                    spec_id, quantity, batch_nos, seal_start, seal_end, operator, remark)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (order_no, kwargs.get("date", ""), kwargs.get("customer_id"),
                 kwargs.get("sales_order_no", ""), kwargs.get("contract_no", ""),
                 kwargs.get("plate_no", ""), kwargs.get("spec_id"),
                 kwargs.get("quantity", 0), kwargs.get("batch_nos", ""),
                 kwargs.get("seal_start", ""), kwargs.get("seal_end", ""),
                 kwargs.get("operator", ""), kwargs.get("remark", "")),
            )
            return cursor.lastrowid, order_no

    def get_outbound(self, outbound_id):
        with self.db.get_connection() as conn:
            return conn.execute(
                """SELECT oo.*, c.name AS customer_name
                   FROM outbound_orders oo
                   LEFT JOIN customers c ON oo.customer_id=c.id
                   WHERE oo.id=?""",
                (outbound_id,),
            ).fetchone()

    def list_outbound(self, date_from=None, date_to=None, customer_id=None,
                      sales_order_no=None, keyword=None):
        with self.db.get_connection() as conn:
            conditions = []
            params = []
            if date_from:
                conditions.append("oo.date>=?")
                params.append(date_from)
            if date_to:
                conditions.append("oo.date<=?")
                params.append(date_to)
            if customer_id:
                conditions.append("oo.customer_id=?")
                params.append(customer_id)
            if sales_order_no:
                conditions.append("oo.sales_order_no LIKE ?")
                params.append(f"%{sales_order_no}%")
            if keyword:
                conditions.append(
                    "(oo.order_no LIKE ? OR oo.seal_start LIKE ? OR oo.batch_nos LIKE ?)")
                kw = f"%{keyword}%"
                params.extend([kw, kw, kw])
            sql = (
                "SELECT oo.*, c.name AS customer_name, s.name AS spec_name "
                "FROM outbound_orders oo "
                "LEFT JOIN customers c ON oo.customer_id=c.id "
                "LEFT JOIN specs s ON oo.spec_id=s.id"
            )
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
            sql += " ORDER BY oo.date DESC, oo.id DESC"
            return conn.execute(sql, params).fetchall()

    def delete_outbound(self, outbound_id):
        with self.db.get_connection() as conn:
            order = conn.execute(
                "SELECT quantity FROM outbound_orders WHERE id=?",
                (outbound_id,)
            ).fetchone()
            if order:
                count = conn.execute(
                    "SELECT COUNT(*) FROM seal_numbers WHERE outbound_id=? AND status='shipped'",
                    (outbound_id,),
                ).fetchone()[0]
                if count > 0:
                    conn.execute(
                        """UPDATE seal_numbers SET status='in_stock', outbound_id=NULL,
                           updated_at=datetime('now','localtime')
                           WHERE outbound_id=? AND status='shipped'""",
                        (outbound_id,),
                    )
            conn.execute("DELETE FROM daily_shipments WHERE outbound_id=?", (outbound_id,))
            conn.execute("DELETE FROM outbound_orders WHERE id=?", (outbound_id,))
