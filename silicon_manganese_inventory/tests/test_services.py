import os
import tempfile
import pytest
from silicon_manganese_inventory.dao.database import DatabaseManager
from silicon_manganese_inventory.dao.seal_dao import SealDAO
from silicon_manganese_inventory.dao.inbound_dao import InboundDAO
from silicon_manganese_inventory.dao.lab_dao import LabDAO
from silicon_manganese_inventory.dao.base_dao import (
    CustomerDAO, SalesOrderDAO, DailyShipmentDAO,
)
from silicon_manganese_inventory.services.seal_service import (
    SealService, SealStatusError, SealInsufficientError,
)
from silicon_manganese_inventory.services.inbound_service import InboundService
from silicon_manganese_inventory.services.outbound_service import (
    OutboundService, StockInsufficientError,
)
from silicon_manganese_inventory.services.lab_service import LabService
from silicon_manganese_inventory.services.report_service import ReportService
from silicon_manganese_inventory.services.excel_service import ExcelService, ExportService


@pytest.fixture
def db():
    tmp = tempfile.mkdtemp()
    db_path = os.path.join(tmp, "test.db")
    mgr = DatabaseManager(db_path)
    mgr.initialize()
    yield mgr
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


class TestSealService:
    @pytest.fixture
    def svc(self, db):
        return SealService(db)

    def test_assign_seals(self, svc, db):
        dao = SealDAO(db)
        bid = dao.create_batch("10001", "10010")
        start, end, seals = svc.assign_seals(bid, 5, batch_no="B001", location_code="A01")
        assert start == "10001"
        assert end == "10005"
        assert len(seals) == 5

    def test_assign_insufficient(self, svc, db):
        dao = SealDAO(db)
        bid = dao.create_batch("20001", "20003")
        with pytest.raises(SealInsufficientError):
            svc.assign_seals(bid, 10)

    def test_release_seals(self, svc, db):
        dao = SealDAO(db)
        bid = dao.create_batch("30001", "30005")
        svc.assign_seals(bid, 3, pre_inbound_id=1)
        svc.release_seals(1)
        count = dao.get_available_count(bid)
        assert count == 5

    def test_confirm_seals(self, svc, db):
        dao = SealDAO(db)
        bid = dao.create_batch("40001", "40005")
        svc.assign_seals(bid, 2, pre_inbound_id=99)
        svc.confirm_seals(99, inbound_id=1)
        seals = dao.get_seals_by_batch(bid, status="in_stock")
        assert len(seals) == 2

    def test_ship_seals(self, svc, db):
        dao = SealDAO(db)
        bid = dao.create_batch("50001", "50005")
        svc.assign_seals(bid, 5, pre_inbound_id=100, batch_no="B001")
        svc.confirm_seals(100, inbound_id=1)
        start, end, codes = svc.ship_seals(3, batch_no="B001")
        assert len(codes) == 3
        assert start == "50001"
        assert end == "50003"

    def test_ship_insufficient(self, svc, db):
        dao = SealDAO(db)
        bid = dao.create_batch("60001", "60002")
        svc.assign_seals(bid, 2, pre_inbound_id=200, batch_no="B002")
        svc.confirm_seals(200, inbound_id=2)
        with pytest.raises(SealInsufficientError):
            svc.ship_seals(10, batch_no="B002")

    def test_invalid_transition(self, svc, db):
        dao = SealDAO(db)
        bid = dao.create_batch("70001", "70001")
        seals = dao.get_available_seals(bid, limit=1)
        with pytest.raises(SealStatusError):
            svc._transition([seals[0]["id"]], "shipped")


class TestInboundService:
    @pytest.fixture
    def svc(self, db):
        return InboundService(db)

    def test_create_pre_inbound(self, svc, db):
        dao = SealDAO(db)
        bid = dao.create_batch("80001", "80020")
        pid, start, end = svc.create_pre_inbound(
            "2026-07-10", "BATCH001", 10, location_code="A01", seal_batch_id=bid)
        assert pid > 0
        assert start == "80001"
        assert end == "80010"

    def test_cancel_pre_inbound(self, svc, db):
        dao = SealDAO(db)
        bid = dao.create_batch("90001", "90010")
        pid, _, _ = svc.create_pre_inbound(
            "2026-07-10", "BATCH002", 5, location_code="A01", seal_batch_id=bid)
        svc.cancel_pre_inbound(pid)
        assert svc.get_pre_inbound(pid) is None
        assert dao.get_available_count(bid) == 10

    def test_confirm_inbound(self, svc, db):
        dao = SealDAO(db)
        lab_dao = LabDAO(db)
        bid = dao.create_batch("10001", "10005")
        pid, _, _ = svc.create_pre_inbound(
            "2026-07-10", "BATCH003", 3, location_code="A01", seal_batch_id=bid)
        lab_dao.save_result(pid, mn_content=66.9, si_content=17.6,
                            mn_result="合格", si_result="合格",
                            overall_result="合格")
        inbound_id = svc.confirm_inbound(pid, operator="admin")
        assert inbound_id > 0
        seals = dao.get_seals_by_batch(bid, status="in_stock")
        assert len(seals) == 3

    def test_confirm_unqualified_rejected(self, svc, db):
        dao = SealDAO(db)
        lab_dao = LabDAO(db)
        bid = dao.create_batch("11001", "11005")
        pid, _, _ = svc.create_pre_inbound(
            "2026-07-10", "BATCH004", 3, location_code="A01", seal_batch_id=bid)
        lab_dao.save_result(pid, mn_content=50.0,
                            mn_result="不合格", overall_result="不合格")
        with pytest.raises(ValueError, match="不合格"):
            svc.confirm_inbound(pid)


class TestOutboundService:
    @pytest.fixture
    def svc(self, db):
        return OutboundService(db)

    def test_create_outbound(self, svc, db):
        seal_dao = SealDAO(db)
        customer_dao = CustomerDAO(db)
        inbound_svc = InboundService(db)
        lab_dao = LabDAO(db)

        cid = customer_dao.create(code="C001", name="测试客户")
        bid = seal_dao.create_batch("12001", "12010")
        pid, _, _ = inbound_svc.create_pre_inbound(
            "2026-07-10", "BATCH005", 5, location_code="A01", seal_batch_id=bid)
        lab_dao.save_result(pid, mn_content=66.9, overall_result="合格")
        inbound_svc.confirm_inbound(pid)

        oid, ono, codes = svc.create_outbound(
            "2026-07-10", 3, customer_id=cid, batch_no="BATCH005")
        assert oid > 0
        assert len(codes) == 3
        assert ono.startswith("PO")

    def test_insufficient_stock(self, svc, db):
        customer_dao = CustomerDAO(db)
        cid = customer_dao.create(code="C002", name="客户二")
        with pytest.raises(SealInsufficientError):
            svc.create_outbound("2026-07-10", 100, customer_id=cid)


class TestLabService:
    @pytest.fixture
    def svc(self, db):
        return LabService(db)

    def test_auto_judge_qualified(self, svc, db):
        inbound_dao = InboundDAO(db)
        pid = inbound_dao.create_pre_inbound(
            date="2026-07-10", batch_no="TEST", quantity=10)
        lid = svc.record_result(pid, mn_content=66.9, si_content=17.6,
                                c_content=1.8, s_content=0.03, p_content=0.10)
        result = svc.get_result(pid)
        assert result["overall_result"] == "合格"

    def test_auto_judge_unqualified(self, svc, db):
        inbound_dao = InboundDAO(db)
        pid = inbound_dao.create_pre_inbound(
            date="2026-07-10", batch_no="TEST2", quantity=10)
        svc.record_result(pid, mn_content=50.0, si_content=17.6,
                          c_content=1.8, s_content=0.03, p_content=0.10)
        result = svc.get_result(pid)
        assert result["overall_result"] == "不合格"

    def test_manual_override(self, svc, db):
        inbound_dao = InboundDAO(db)
        pid = inbound_dao.create_pre_inbound(
            date="2026-07-10", batch_no="TEST3", quantity=10)
        svc.record_result(pid, mn_content=50.0, overall_result="合格")
        result = svc.get_result(pid)
        assert result["overall_result"] == "合格"

    def test_format_lab_string(self, svc, db):
        inbound_dao = InboundDAO(db)
        pid = inbound_dao.create_pre_inbound(
            date="2026-07-10", batch_no="TEST4", quantity=10)
        svc.record_result(pid, mn_content=66.9, si_content=17.6,
                          c_content=1.8, s_content=0.03, p_content=0.10)
        formatted = svc.format_lab_string(pid)
        assert "Mn含量" in formatted
        assert "合格" in formatted


class TestReportService:
    @pytest.fixture
    def svc(self, db):
        return ReportService(db)

    def test_inventory_report(self, svc, db):
        seal_dao = SealDAO(db)
        inbound_svc = InboundService(db)
        lab_dao = LabDAO(db)
        bid = seal_dao.create_batch("13001", "13010")
        pid, _, _ = inbound_svc.create_pre_inbound(
            "2026-07-10", "BATCH-R1", 5, location_code="A01", seal_batch_id=bid)
        lab_dao.save_result(pid, mn_content=66.9, overall_result="合格")
        inbound_svc.confirm_inbound(pid)
        rows = svc.get_inventory_report()
        assert len(rows) == 1
        assert rows[0]["batch_no"] == "BATCH-R1"
        assert rows[0]["balance"] == 5

    def test_order_summary(self, svc, db):
        from silicon_manganese_inventory.dao.base_dao import SalesOrderDAO
        sdao = SalesOrderDAO(db)
        sdao.create(order_no="SO-TEST", customer_code="C100",
                    customer_name="测试公司", quantity=100,
                    material_desc="普碳锰硅合金")
        rows = svc.get_order_summary()
        assert len(rows) == 1
        assert rows[0]["order_quantity"] == 100


class TestExcelService:
    @pytest.fixture
    def svc(self, db):
        return ExcelService(db)

    def test_export_inventory(self, db):
        es = ExportService(db)
        path = os.path.join(tempfile.mkdtemp(), "inventory.xlsx")
        es.export_inventory(path)
        assert os.path.exists(path)

    def test_export_daily_shipments(self, db):
        ddao = DailyShipmentDAO(db)
        ddao.create(seq_no=1, shipment_date="2026-07-10", plate_no="测试",
                    customer_name="测试公司", sales_order_no="SO001",
                    material_name="普碳锰硅合金", load_quantity=33)
        es = ExportService(db)
        path = os.path.join(tempfile.mkdtemp(), "shipments.xlsx")
        es.export_daily_shipments(path)
        assert os.path.exists(path)

    def test_export_order_summary(self, db):
        es = ExportService(db)
        path = os.path.join(tempfile.mkdtemp(), "orders.xlsx")
        es.export_order_summary(path)
        assert os.path.exists(path)
