"""边缘场景集成测试：取消恢复、删除清理、并发、边界值"""
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import tempfile
import shutil

from silicon_manganese_inventory.dao.database import DatabaseManager
from silicon_manganese_inventory.dao.seal_dao import SealDAO
from silicon_manganese_inventory.dao.inbound_dao import InboundDAO
from silicon_manganese_inventory.dao.outbound_dao import OutboundDAO
from silicon_manganese_inventory.dao.base_dao import LocationDAO, CustomerDAO
from silicon_manganese_inventory.dao.lab_dao import LabDAO
from silicon_manganese_inventory.services.seal_service import SealService, SealStatusError, SealInsufficientError
from silicon_manganese_inventory.services.inbound_service import InboundService
from silicon_manganese_inventory.services.outbound_service import OutboundService
from silicon_manganese_inventory.services.report_service import ReportService


@pytest.fixture
def db():
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test.db")
    dbm = DatabaseManager(db_path)
    dbm.initialize()
    yield dbm
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def setup_batch(db):
    dao = SealDAO(db)
    batch_id = dao.create_batch("210001", "210100", name="TEST-BATCH")
    return batch_id


def _ensure_loc(db, code):
    loc_dao = LocationDAO(db)
    return loc_dao.get_or_create(code)


class TestCancelPreInbound:
    def test_cancel_releases_seals(self, db, setup_batch):
        svc = InboundService(db)
        loc = _ensure_loc(db, "Z991")

        pid, start, end = svc.create_pre_inbound(
            date="2026-07-01", batch_no="B001", quantity=10,
            location_code=loc, seal_batch_id=setup_batch,
        )
        assert start == "210001"
        assert end == "210010"

        svc.cancel_pre_inbound(pid)
        with db.get_connection() as conn:
            seals = conn.execute(
                "SELECT status FROM seal_numbers WHERE seal_code BETWEEN '210001' AND '210010'"
            ).fetchall()
            for s in seals:
                assert s["status"] == "unused"
            pre = conn.execute("SELECT * FROM pre_inbound_orders WHERE id=?", (pid,)).fetchone()
            assert pre is None


class TestDeleteOutbound:
    def test_delete_outbound_restores_seals(self, db, setup_batch):
        loc_nature = _ensure_loc(db, "Z992")
        loc_finished = _ensure_loc(db, "A99-DEL")
        cust_dao = CustomerDAO(db)
        cust_id = cust_dao.create(code="C001", name="测试客户")

        inbound_svc = InboundService(db)
        pid, _, _ = inbound_svc.create_pre_inbound(
            date="2026-07-01", batch_no="B001", quantity=10,
            location_code=loc_nature, seal_batch_id=setup_batch,
        )
        lab_dao = LabDAO(db)
        lab_dao.save_result(pid, mn_content=65.0, si_content=17.0,
                            mn_result="合格", si_result="合格", overall_result="合格")
        iid = inbound_svc.confirm_inbound(pid, target_location=loc_finished)

        outbound_svc = OutboundService(db)
        oid, _, _ = outbound_svc.create_outbound(
            date="2026-07-02", batch_no="B001", quantity=5,
            location_code=loc_finished, customer_id=cust_id,
        )

        dao = OutboundDAO(db)
        dao.delete_outbound(oid)
        with db.get_connection() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM seal_numbers WHERE status='in_stock' AND outbound_id IS NULL"
            ).fetchone()[0]
            assert count == 10
            shipped = conn.execute(
                "SELECT COUNT(*) FROM seal_numbers WHERE status='shipped'"
            ).fetchone()[0]
            assert shipped == 0


class TestConfirmWithoutLab:
    def test_confirm_without_lab_fails(self, db, setup_batch):
        loc = _ensure_loc(db, "Z993")
        target = _ensure_loc(db, "A99-CONFIRM")
        svc = InboundService(db)
        pid, _, _ = svc.create_pre_inbound(
            date="2026-07-01", batch_no="B001", quantity=10,
            location_code=loc, seal_batch_id=setup_batch,
        )
        with pytest.raises(ValueError, match="尚未判定"):
            svc.confirm_inbound(pid, target_location=target)

    def test_confirm_failed_lab_fails(self, db, setup_batch):
        loc = _ensure_loc(db, "Z994")
        target = _ensure_loc(db, "A99-FAIL")
        svc = InboundService(db)
        pid, _, _ = svc.create_pre_inbound(
            date="2026-07-01", batch_no="B001", quantity=10,
            location_code=loc, seal_batch_id=setup_batch,
        )
        lab_dao = LabDAO(db)
        lab_dao.save_result(pid, overall_result="不合格")
        with pytest.raises(ValueError, match="不合格"):
            svc.confirm_inbound(pid, target_location=target)


class TestInvalidTransitions:
    def test_shipped_to_in_stock_not_allowed(self, db, setup_batch):
        loc = _ensure_loc(db, "Z995")
        target = _ensure_loc(db, "A99-TRANS")
        cust_dao = CustomerDAO(db)
        cust_id = cust_dao.create(code="C002", name="客户2")

        inbound_svc = InboundService(db)
        pid, _, _ = inbound_svc.create_pre_inbound(
            date="2026-07-01", batch_no="B001", quantity=5,
            location_code=loc, seal_batch_id=setup_batch,
        )
        lab_dao = LabDAO(db)
        lab_dao.save_result(pid, overall_result="合格")
        inbound_svc.confirm_inbound(pid, target_location=target)

        outbound_svc = OutboundService(db)
        outbound_svc.create_outbound(
            date="2026-07-02", batch_no="B001", quantity=2,
            location_code=target, customer_id=cust_id,
        )

        with db.get_connection() as conn:
            seals = conn.execute(
                "SELECT id FROM seal_numbers WHERE status='shipped' LIMIT 1"
            ).fetchall()
        seal_svc = SealService(db)
        with pytest.raises(SealStatusError, match="不允许"):
            seal_svc._transition([seals[0]["id"]], "in_stock")

    def test_unused_to_in_stock_not_allowed(self, db, setup_batch):
        with db.get_connection() as conn:
            seals = conn.execute(
                "SELECT id FROM seal_numbers WHERE status='unused' LIMIT 1"
            ).fetchall()
        seal_svc = SealService(db)
        with pytest.raises(SealStatusError, match="不允许"):
            seal_svc._transition([seals[0]["id"]], "in_stock")


class TestBoundaryValues:
    def test_zero_quantity_rejected(self, db, setup_batch):
        loc = _ensure_loc(db, "Z996")
        svc = InboundService(db)
        with pytest.raises(ValueError, match="数量"):
            svc.create_pre_inbound(
                date="2026-07-01", batch_no="B001", quantity=0,
                location_code=loc, seal_batch_id=setup_batch,
            )

    def test_negative_quantity_rejected(self, db, setup_batch):
        loc = _ensure_loc(db, "Z997")
        svc = InboundService(db)
        with pytest.raises(ValueError, match="数量"):
            svc.create_pre_inbound(
                date="2026-07-01", batch_no="B001", quantity=-5,
                location_code=loc, seal_batch_id=setup_batch,
            )

    def test_over_assign_rejected(self, db, setup_batch):
        loc = _ensure_loc(db, "Z998")
        svc = InboundService(db)
        with pytest.raises(SealInsufficientError, match="不足"):
            svc.create_pre_inbound(
                date="2026-07-01", batch_no="B001", quantity=200,
                location_code=loc, seal_batch_id=setup_batch,
            )

    def test_pre_inbound_rollback_on_assign_failure(self, db, setup_batch):
        loc = _ensure_loc(db, "Z999")
        svc = InboundService(db)
        with pytest.raises(SealInsufficientError):
            svc.create_pre_inbound(
                date="2026-07-01", batch_no="B001", quantity=200,
                location_code=loc, seal_batch_id=setup_batch,
            )
        with db.get_connection() as conn:
            pre_count = conn.execute(
                "SELECT COUNT(*) FROM pre_inbound_orders"
            ).fetchone()[0]
            assert pre_count == 0


class TestLocationAutoCreate:
    def test_auto_created_location_works(self, db):
        code = _ensure_loc(db, "A99-8月")
        assert code == "A99-8月"
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM locations WHERE code='A99-8月'"
            ).fetchone()
            assert row is not None

    def test_existing_location_not_duplicated(self, db):
        _ensure_loc(db, "EXIST")
        code = _ensure_loc(db, "EXIST")
        assert code == "EXIST"
        with db.get_connection() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM locations WHERE code='EXIST'"
            ).fetchone()[0]
            assert count == 1


class TestReportService:
    def test_empty_inventory_report(self, db):
        svc = ReportService(db)
        rows = svc.get_inventory_report()
        assert rows == []

    def test_empty_order_summary(self, db):
        svc = ReportService(db)
        rows = svc.get_order_summary()
        assert rows == []


class TestSensitiveSeals:
    def test_shipped_seal_cannot_be_resold(self, db, setup_batch):
        loc = _ensure_loc(db, "Z888")
        target = _ensure_loc(db, "A99-SENS")
        cust_dao = CustomerDAO(db)
        cust_id = cust_dao.create(code="C003", name="客户3")

        svc = InboundService(db)
        pid, _, _ = svc.create_pre_inbound(
            date="2026-07-01", batch_no="B001", quantity=5,
            location_code=loc, seal_batch_id=setup_batch,
        )
        lab_dao = LabDAO(db)
        lab_dao.save_result(pid, overall_result="合格")
        svc.confirm_inbound(pid, target_location=target)

        outbound_svc = OutboundService(db)
        outbound_svc.create_outbound(
            date="2026-07-02", batch_no="B001", quantity=3,
            location_code=target, customer_id=cust_id,
        )

        with db.get_connection() as conn:
            shipped = conn.execute(
                "SELECT COUNT(*) FROM seal_numbers WHERE status='shipped'"
            ).fetchone()[0]
            assert shipped == 3
            in_stock = conn.execute(
                "SELECT COUNT(*) FROM seal_numbers WHERE status='in_stock'"
            ).fetchone()[0]
            assert in_stock == 2

        with db.get_connection() as conn:
            reuse_in = conn.execute(
                "SELECT id FROM seal_numbers WHERE status='shipped' LIMIT 1"
            ).fetchone()
        seal_svc = SealService(db)
        with pytest.raises(SealStatusError):
            seal_svc._transition([reuse_in["id"]], "in_stock")
