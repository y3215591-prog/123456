from datetime import datetime
from silicon_manganese_inventory.dao.database import DatabaseManager
from silicon_manganese_inventory.dao.inbound_dao import InboundDAO
from silicon_manganese_inventory.services.seal_service import SealService


class InboundService:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.inbound_dao = InboundDAO(db)
        self.seal_service = SealService(db)

    def create_pre_inbound(self, date, batch_no, quantity, spec_id=None,
                           location_code="", seal_batch_id=None,
                           operator="", remark=""):
        if not date or not batch_no or quantity <= 0:
            raise ValueError("日期、批次号和数量为必填项")
        if not seal_batch_id:
            raise ValueError("请选择铅封号段")
        pid = self.inbound_dao.create_pre_inbound(
            date=date, batch_no=batch_no, quantity=quantity,
            spec_id=spec_id, location_code=location_code,
            seal_batch_id=seal_batch_id, operator=operator, remark=remark,
        )
        try:
            seal_start, seal_end, seals = self.seal_service.assign_seals(
                seal_batch_id, quantity, pre_inbound_id=pid,
                batch_no=batch_no, location_code=location_code,
            )
            self.inbound_dao.update_pre_inbound(
                pid, seal_start=seal_start, seal_end=seal_end,
            )
        except Exception:
            self.inbound_dao.delete_pre_inbound(pid)
            raise
        return pid, seal_start, seal_end

    def cancel_pre_inbound(self, pre_inbound_id):
        row = self.inbound_dao.get_pre_inbound(pre_inbound_id)
        if not row:
            raise ValueError("预入库单不存在")
        if row["lab_status"] == "tested":
            raise ValueError("已化验的预入库单不能作废")
        self.seal_service.release_seals(pre_inbound_id)
        self.inbound_dao.delete_pre_inbound(pre_inbound_id)

    def confirm_inbound(self, pre_inbound_id, operator="", target_location=None):
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM pre_inbound_orders WHERE id=?",
                (pre_inbound_id,),
            ).fetchone()
            if not row:
                raise ValueError("预入库单不存在")
            lab = conn.execute(
                "SELECT overall_result FROM lab_results WHERE pre_inbound_id=?",
                (pre_inbound_id,),
            ).fetchone()
            if not lab or not lab["overall_result"]:
                raise ValueError("化验结果尚未判定，无法入库")
            if lab["overall_result"] != "合格":
                raise ValueError("化验不合格，无法入库")
            location = target_location or row["location_code"] or ""
            inbound_id = self.inbound_dao.create_inbound(
                pre_inbound_id, conn=conn, operator=operator,
                date=datetime.now().strftime("%Y-%m-%d"),
                location_code=location,
            )
        self.seal_service.confirm_seals(pre_inbound_id, inbound_id,
                                        target_location=location)
        return inbound_id

    def get_pre_inbound(self, pre_inbound_id):
        return self.inbound_dao.get_pre_inbound(pre_inbound_id)

    def list_pre_inbound(self, **kwargs):
        return self.inbound_dao.list_pre_inbound(**kwargs)

    def list_inbound(self, **kwargs):
        return self.inbound_dao.list_inbound(**kwargs)
