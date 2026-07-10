from silicon_manganese_inventory.dao.database import DatabaseManager
from silicon_manganese_inventory.dao.seal_dao import SealDAO


class SealStatusError(Exception):
    pass


class SealInsufficientError(Exception):
    pass


ALLOWED_TRANSITIONS = {
    "unused": ["pre_allocated"],
    "pre_allocated": ["unused", "in_stock"],
    "in_stock": ["shipped"],
    "shipped": [],
}


class SealService:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.dao = SealDAO(db)

    def assign_seals(self, batch_id, quantity, pre_inbound_id=None,
                     batch_no="", location_code=""):
        available = self.dao.get_available_seals(batch_id, limit=quantity)
        if len(available) < quantity:
            raise SealInsufficientError(
                f"号段剩余不足：需要 {quantity} 个，仅剩 {len(available)} 个")
        seal_ids = [s["id"] for s in available]
        kwargs = {}
        if pre_inbound_id is not None:
            kwargs["pre_inbound_id"] = pre_inbound_id
        if batch_no:
            kwargs["batch_no"] = batch_no
        if location_code:
            kwargs["location_code"] = location_code
        self._transition(seal_ids, "pre_allocated", **kwargs)
        start = available[0]["seal_code"]
        end = available[-1]["seal_code"]
        return start, end, available

    def release_seals(self, pre_inbound_id):
        with self.db.get_connection() as conn:
            seals = conn.execute(
                "SELECT id FROM seal_numbers WHERE pre_inbound_id=? AND status='pre_allocated'",
                (pre_inbound_id,),
            ).fetchall()
        if seals:
            seal_ids = [s["id"] for s in seals]
            self._transition(seal_ids, "unused",
                             pre_inbound_id=None, batch_no="", location_code="")

    def confirm_seals(self, pre_inbound_id, inbound_id, target_location=None):
        with self.db.get_connection() as conn:
            seals = conn.execute(
                "SELECT id FROM seal_numbers WHERE pre_inbound_id=? AND status='pre_allocated'",
                (pre_inbound_id,),
            ).fetchall()
        if not seals:
            raise SealStatusError("没有可确认入库的铅封号")
        seal_ids = [s["id"] for s in seals]
        extra = {"inbound_id": inbound_id}
        if target_location:
            extra["location_code"] = target_location
        self._transition(seal_ids, "in_stock", **extra)

    def ship_seals(self, quantity, batch_no=None, location_code=None, outbound_id=None):
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
                "SELECT sn.id, sn.seal_code FROM seal_numbers sn "
                "WHERE " + " AND ".join(conditions) +
                " ORDER BY sn.seal_code LIMIT ?"
            )
            params.append(quantity)
            seals = conn.execute(sql, params).fetchall()
        if len(seals) < quantity:
            raise SealInsufficientError(
                f"库存不足：需要 {quantity} 个，当前可用 {len(seals)} 个")
        seal_ids = [s["id"] for s in seals]
        self._transition(seal_ids, "shipped", outbound_id=outbound_id)
        start = seals[0]["seal_code"]
        end = seals[-1]["seal_code"]
        return start, end, [s["seal_code"] for s in seals]

    def ship_seals_by_outbound(self, outbound_id, quantity,
                               batch_no=None, location_code=None):
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
                "SELECT sn.id, sn.seal_code FROM seal_numbers sn "
                "WHERE " + " AND ".join(conditions) +
                " ORDER BY sn.seal_code LIMIT ?"
            )
            params.append(quantity)
            seals = conn.execute(sql, params).fetchall()
        if len(seals) < quantity:
            raise SealInsufficientError(
                f"库存不足：需要 {quantity} 个，当前可用 {len(seals)} 个")
        seal_ids = [s["id"] for s in seals]
        self._transition(seal_ids, "shipped", outbound_id=outbound_id)
        start = seals[0]["seal_code"]
        end = seals[-1]["seal_code"]
        return start, end, [s["seal_code"] for s in seals]

    def _transition(self, seal_ids, new_status, **kwargs):
        if not seal_ids:
            return
        with self.db.get_connection() as conn:
            placeholders = ",".join("?" * len(seal_ids))
            rows = conn.execute(
                f"SELECT id, status FROM seal_numbers WHERE id IN ({placeholders})",
                seal_ids,
            ).fetchall()
            found = {row["id"]: row["status"] for row in rows}
            for seal_id in seal_ids:
                current = found.get(seal_id)
                if current is None:
                    raise SealStatusError(f"铅封号 {seal_id} 不存在")
                if new_status not in ALLOWED_TRANSITIONS.get(current, []):
                    raise SealStatusError(
                        f"不允许状态流转: {current} -> {new_status} (铅封号 {seal_id})")
            self.dao.update_seal_status_batch(seal_ids, new_status, conn=conn, **kwargs)
