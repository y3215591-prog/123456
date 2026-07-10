from silicon_manganese_inventory.dao.database import DatabaseManager
from silicon_manganese_inventory.dao.base_dao import DailyShipmentDAO


class ReportService:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def get_inventory_report(self, location_code=None, batch_no=None):
        with self.db.get_connection() as conn:
            conditions = ["sn.status='in_stock'"]
            params = []
            if location_code:
                conditions.append("sn.location_code LIKE ?")
                params.append(f"%{location_code}%")
            if batch_no:
                conditions.append("sn.batch_no LIKE ?")
                params.append(f"%{batch_no}%")
            sql = (
                "SELECT sn.batch_no, sn.location_code, COUNT(*) AS balance, "
                "pio.date AS last_inbound_date, lr.overall_result, "
                "GROUP_CONCAT(DISTINCT sn.seal_code) AS seal_list "
                "FROM seal_numbers sn "
                "JOIN pre_inbound_orders pio ON sn.pre_inbound_id=pio.id "
                "LEFT JOIN lab_results lr ON pio.id=lr.pre_inbound_id "
                "WHERE " + " AND ".join(conditions) +
                " GROUP BY sn.batch_no, sn.location_code "
                "ORDER BY sn.batch_no, sn.location_code"
            )
            return conn.execute(sql, params).fetchall()

    def get_inventory_total(self):
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS total FROM seal_numbers WHERE status='in_stock'"
            ).fetchone()
        return row["total"] if row else 0

    def get_daily_shipment_report(self, **kwargs):
        dao = DailyShipmentDAO(self.db)
        return dao.list(**kwargs)

    def get_order_summary(self):
        with self.db.get_connection() as conn:
            rows = conn.execute(
                """SELECT so.order_no, so.customer_code, so.customer_name,
                   so.material_desc AS material_name, '10-60mm' AS spec,
                   '吨' AS unit, so.quantity AS order_quantity,
                   so.delivery_end, so.pickup_method,
                   COALESCE(SUM(ds.load_quantity), 0) AS shipped_quantity,
                   so.quantity - COALESCE(SUM(ds.load_quantity), 0) AS pending_quantity,
                   CASE WHEN so.quantity > 0
                        THEN ROUND(COALESCE(SUM(ds.load_quantity), 0) * 1.0 / so.quantity, 3)
                        ELSE 0 END AS completion_rate
                   FROM sales_orders so
                   LEFT JOIN daily_shipments ds ON so.order_no=ds.sales_order_no
                   GROUP BY so.order_no
                   ORDER BY so.order_no DESC"""
            ).fetchall()
        results = []
        for row in rows:
            row_dict = dict(row)
            rate = row_dict.get("completion_rate", 0)
            if rate >= 0.95:
                row_dict["warning"] = "即将发完"
            elif rate >= 0.80:
                row_dict["warning"] = "接近总量提醒"
            elif row_dict.get("pending_quantity", 0) > 0 and row_dict.get("delivery_end"):
                row_dict["warning"] = "请按期发货"
            else:
                row_dict["warning"] = ""
            results.append(row_dict)
        return results
