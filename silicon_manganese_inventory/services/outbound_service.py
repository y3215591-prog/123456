from datetime import datetime
from silicon_manganese_inventory.dao.database import DatabaseManager
from silicon_manganese_inventory.dao.outbound_dao import OutboundDAO
from silicon_manganese_inventory.services.seal_service import SealService


class StockInsufficientError(Exception):
    pass


class OutboundService:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.outbound_dao = OutboundDAO(db)
        self.seal_service = SealService(db)

    def create_outbound(self, date, quantity, customer_id=None,
                        sales_order_no="", spec_id=None, operator="",
                        remark="", batch_no=None, location_code=None,
                        contract_no=None, plate_no=None):
        if not date or quantity <= 0:
            raise ValueError("日期和数量为必填项")
        if not customer_id:
            raise ValueError("请选择客户")
        outbound_id, order_no = self.outbound_dao.create_outbound(
            date=date, customer_id=customer_id,
            sales_order_no=sales_order_no, spec_id=spec_id,
            quantity=quantity, operator=operator, remark=remark,
            contract_no=contract_no, plate_no=plate_no,
        )
        seal_start, seal_end, seal_codes = self.seal_service.ship_seals_by_outbound(
            outbound_id, quantity, batch_no=batch_no, location_code=location_code,
        )
        batch_nos = self._collect_batch_nos(seal_codes)
        with self.db.get_connection() as conn:
            conn.execute(
                "UPDATE outbound_orders SET seal_start=?, seal_end=?, batch_nos=? WHERE id=?",
                (seal_start, seal_end, batch_nos, outbound_id),
            )
        return outbound_id, order_no, seal_codes

    def _collect_batch_nos(self, seal_codes):
        if not seal_codes:
            return ""
        with self.db.get_connection() as conn:
            placeholders = ",".join("?" for _ in seal_codes)
            rows = conn.execute(
                f"SELECT DISTINCT batch_no FROM seal_numbers WHERE seal_code IN ({placeholders}) AND batch_no != ''",
                seal_codes,
            ).fetchall()
        return ",".join(r["batch_no"] for r in rows if r["batch_no"])

    def get_outbound(self, outbound_id):
        return self.outbound_dao.get_outbound(outbound_id)

    def list_outbound(self, **kwargs):
        return self.outbound_dao.list_outbound(**kwargs)

    def get_outbound_seals(self, outbound_id):
        with self.db.get_connection() as conn:
            return conn.execute(
                "SELECT seal_code FROM seal_numbers WHERE outbound_id=? ORDER BY seal_code",
                (outbound_id,),
            ).fetchall()
