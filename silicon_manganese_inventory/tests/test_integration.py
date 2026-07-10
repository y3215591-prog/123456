import os
import tempfile
import pytest
from silicon_manganese_inventory.dao.database import DatabaseManager
from silicon_manganese_inventory.dao.seal_dao import SealDAO
from silicon_manganese_inventory.dao.inbound_dao import InboundDAO
from silicon_manganese_inventory.dao.lab_dao import LabDAO
from silicon_manganese_inventory.dao.base_dao import (
    CustomerDAO, SupplierDAO, SpecDAO, LocationDAO, WarehouseDAO,
    SalesOrderDAO, DailyShipmentDAO,
)
from silicon_manganese_inventory.services.seal_service import SealService
from silicon_manganese_inventory.services.inbound_service import InboundService
from silicon_manganese_inventory.services.outbound_service import OutboundService
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


class TestSealLifecycle:
    """铅封号完整生命周期：号段导入 → 预入库分配 → 化验 → 入库确认 → 出库 → 追溯"""

    def test_full_lifecycle(self, db):
        seal_dao = SealDAO(db)
        inbound_svc = InboundService(db)
        outbound_svc = OutboundService(db)
        lab_dao = LabDAO(db)
        cust_dao = CustomerDAO(db)

        bid = seal_dao.create_batch("20001", "20020")
        available_before = seal_dao.get_available_count(bid)
        assert available_before == 20

        pid, seal_start, seal_end = inbound_svc.create_pre_inbound(
            "2026-07-10", "LC001", quantity=8, location_code="A01",
            seal_batch_id=bid, operator="admin",
        )
        assert seal_start == "20001"
        assert seal_end == "20008"

        seals_pre = seal_dao.get_seals_by_batch(bid, status="pre_allocated")
        assert len(seals_pre) == 8
        assert seal_dao.get_available_count(bid) == 12

        lab_dao.save_result(pid, mn_content=66.9, si_content=17.6,
                            c_content=1.8, s_content=0.03, p_content=0.20,
                            mn_result="合格", si_result="合格",
                            c_result="合格", s_result="合格", p_result="合格",
                            overall_result="合格")

        inbound_id = inbound_svc.confirm_inbound(pid, operator="admin")
        assert inbound_id > 0

        seals_in_stock = seal_dao.get_seals_by_batch(bid, status="in_stock")
        assert len(seals_in_stock) == 8

        cid = cust_dao.create(name="生命周期测试客户")
        oid, ono, shipped_codes = outbound_svc.create_outbound(
            "2026-07-10", quantity=5, customer_id=cid,
            batch_no="LC001", operator="shipper",
        )
        assert oid > 0
        assert len(shipped_codes) == 5
        assert shipped_codes[0] == "20001"
        assert shipped_codes[-1] == "20005"

        shipped_seals = seal_dao.get_seals_by_batch(bid, status="shipped")
        assert len(shipped_seals) == 5

        remaining = seal_dao.get_seals_by_batch(bid, status="in_stock")
        assert len(remaining) == 3

        trace = seal_dao.trace_seal("20001")
        assert trace is not None
        assert trace["status"] == "shipped"
        assert trace["customer_name"] == "生命周期测试客户"

        trace3 = seal_dao.trace_seal("20008")
        assert trace3["status"] == "in_stock"

    def test_multiple_batches(self, db):
        seal_dao = SealDAO(db)
        inbound_svc = InboundService(db)
        cust_dao = CustomerDAO(db)
        outbound_svc = OutboundService(db)
        lab_dao = LabDAO(db)

        bid1 = seal_dao.create_batch("30001", "30010")
        bid2 = seal_dao.create_batch("40001", "40010")

        pid1, _, _ = inbound_svc.create_pre_inbound(
            "2026-07-06", "MB001", 4, location_code="B01", seal_batch_id=bid1)
        pid2, _, _ = inbound_svc.create_pre_inbound(
            "2026-07-07", "MB002", 4, location_code="B02", seal_batch_id=bid2)

        for pid in [pid1, pid2]:
            lab_dao.save_result(pid, mn_content=66.9, overall_result="合格")
            inbound_svc.confirm_inbound(pid)

        cid = cust_dao.create(name="多批次客户")
        oid, _, codes1 = outbound_svc.create_outbound(
            "2026-07-10", 2, customer_id=cid, batch_no="MB001")
        assert len(codes1) == 2

        oid2, _, codes2 = outbound_svc.create_outbound(
            "2026-07-11", 2, customer_id=cid, batch_no="MB002")
        assert len(codes2) == 2

    def test_cancel_and_retry(self, db):
        seal_dao = SealDAO(db)
        inbound_svc = InboundService(db)
        lab_dao = LabDAO(db)
        cust_dao = CustomerDAO(db)
        outbound_svc = OutboundService(db)

        bid = seal_dao.create_batch("50001", "50010")

        pid, s1, e1 = inbound_svc.create_pre_inbound(
            "2026-07-08", "CN001", 3, seal_batch_id=bid, location_code="A01")
        inbound_svc.cancel_pre_inbound(pid)
        assert seal_dao.get_available_count(bid) == 10

        pid2, s2, e2 = inbound_svc.create_pre_inbound(
            "2026-07-08", "CN001-R", 5, seal_batch_id=bid, location_code="A01")
        assert s2 == "50001"
        assert e2 == "50005"

        lab_dao.save_result(pid2, mn_content=67.0, overall_result="合格")
        inbound_svc.confirm_inbound(pid2)

        cid = cust_dao.create(name="重试客户")
        oid, _, codes = outbound_svc.create_outbound(
            "2026-07-10", 3, customer_id=cid, batch_no="CN001-R")
        assert len(codes) == 3
        assert codes[0] == "50001"

    def test_ship_multiple_outbounds_same_batch(self, db):
        seal_dao = SealDAO(db)
        inbound_svc = InboundService(db)
        lab_dao = LabDAO(db)
        cust_dao = CustomerDAO(db)
        outbound_svc = OutboundService(db)

        bid = seal_dao.create_batch("60001", "60010")
        pid, _, _ = inbound_svc.create_pre_inbound(
            "2026-07-10", "SH01", 10, seal_batch_id=bid, location_code="A01")
        lab_dao.save_result(pid, mn_content=66.9, overall_result="合格")
        inbound_svc.confirm_inbound(pid)

        cid = cust_dao.create(name="分批发货客户")
        o1, _, c1 = outbound_svc.create_outbound(
            "2026-07-10", 4, customer_id=cid, batch_no="SH01")
        o2, _, c2 = outbound_svc.create_outbound(
            "2026-07-10", 6, customer_id=cid, batch_no="SH01")
        assert len(c1) == 4
        assert len(c2) == 6

        shipped = seal_dao.get_seals_by_batch(bid, status="shipped")
        assert len(shipped) == 10


class TestExcelIntegration:
    def test_import_sales_orders(self, db):
        import openpyxl
        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "sales_orders.xlsx")
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["销售订单号", "客户代码", "客户名称", "物料描述", "数量", "单位"])
        ws.append(["SO-001", "C-001", "钢铁集团", "硅锰合金", 500, "吨"])
        wb.save(path)

        svc = ExcelService(db)
        result = svc.import_sales_orders(path)
        assert result["imported_orders"] == 1

        cust_dao = CustomerDAO(db)
        custs = cust_dao.list()
        assert any(c["name"] == "钢铁集团" for c in custs)

        sdao = SalesOrderDAO(db)
        orders = sdao.list()
        assert len(orders) >= 1

    def test_import_daily_shipments(self, db):
        import openpyxl
        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "daily_shipments.xlsx")
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["序号", "", "", "", "", "", "", "", "", "", "", "", "", "", ""])
        ws.append([1, "2026-07-10", "沪A12345", "C-001", "钢铁集团",
                    "SO-001", "硅锰合金", "10-60mm", "B001", 33.5,
                    45.2, 11.7, 33.5, 33.2, ""])
        wb.save(path)

        svc = ExcelService(db)
        result = svc.import_daily_shipments(path)
        assert result["imported"] == 1

        ddao = DailyShipmentDAO(db)
        rows = ddao.list()
        assert len(rows) == 1
        assert rows[0]["plate_no"] == "沪A12345"

    def test_export_all_reports(self, db):
        seal_dao = SealDAO(db)
        inbound_svc = InboundService(db)
        lab_dao = LabDAO(db)
        cust_dao = CustomerDAO(db)
        outbound_svc = OutboundService(db)
        sdao = SalesOrderDAO(db)
        ddao = DailyShipmentDAO(db)

        bid = seal_dao.create_batch("70001", "70010")
        pid, _, _ = inbound_svc.create_pre_inbound(
            "2026-07-10", "EXP001", 5, location_code="A01", seal_batch_id=bid)
        lab_dao.save_result(pid, mn_content=66.9, overall_result="合格")
        inbound_svc.confirm_inbound(pid)

        cid = cust_dao.create(name="导出测试客户")
        outbound_svc.create_outbound(
            "2026-07-10", 2, customer_id=cid, batch_no="EXP001")

        sdao.create(order_no="EXP-SO", customer_code="T001",
                    customer_name="导出客户", quantity=200,
                    material_desc="硅锰合金")

        ddao.create(seq_no=1, shipment_date="2026-07-10",
                    plate_no="导出测试", customer_name="导出客户",
                    sales_order_no="EXP-SO", material_name="硅锰合金",
                    load_quantity=30)

        export = ExportService(db)
        tmp = tempfile.mkdtemp()

        inv_path = os.path.join(tmp, "库存.xlsx")
        export.export_inventory(inv_path)
        assert os.path.exists(inv_path)
        assert os.path.getsize(inv_path) > 0

        daily_path = os.path.join(tmp, "发货明细.xlsx")
        export.export_daily_shipments(daily_path)
        assert os.path.exists(daily_path)
        assert os.path.getsize(daily_path) > 0

        order_path = os.path.join(tmp, "订单汇总.xlsx")
        export.export_order_summary(order_path)
        assert os.path.exists(order_path)
        assert os.path.getsize(order_path) > 0

    def test_report_with_filters(self, db):
        seal_dao = SealDAO(db)
        inbound_svc = InboundService(db)
        lab_dao = LabDAO(db)

        bid1 = seal_dao.create_batch("80001", "80005")
        pid1, _, _ = inbound_svc.create_pre_inbound(
            "2026-07-05", "FLT001", 3, location_code="A01", seal_batch_id=bid1)
        lab_dao.save_result(pid1, mn_content=66.9, overall_result="合格")
        inbound_svc.confirm_inbound(pid1)

        bid2 = seal_dao.create_batch("90001", "90005")
        pid2, _, _ = inbound_svc.create_pre_inbound(
            "2026-07-08", "FLT002", 4, location_code="B01", seal_batch_id=bid2)
        lab_dao.save_result(pid2, mn_content=67.0, overall_result="合格")
        inbound_svc.confirm_inbound(pid2)

        svc = ReportService(db)
        all_rows = svc.get_inventory_report()
        assert len(all_rows) >= 2

        filtered = svc.get_inventory_report(location_code="A01")
        assert len(filtered) >= 1
        for r in filtered:
            assert "A01" in r["location_code"]

        total = svc.get_inventory_total()
        assert total >= 7

    def test_order_summary_with_warnings(self, db):
        sdao = SalesOrderDAO(db)
        sdao.create(order_no="WARN-001", customer_name="预警客户",
                    quantity=100, material_desc="硅锰合金",
                    delivery_end="2026-07-15")

        ddao = DailyShipmentDAO(db)
        ddao.create(seq_no=1, shipment_date="2026-07-10",
                    customer_name="预警客户", sales_order_no="WARN-001",
                    material_name="硅锰合金", load_quantity=85)

        svc = ReportService(db)
        rows = svc.get_order_summary()
        assert len(rows) >= 1

        warn_order = [r for r in rows if r["order_no"] == "WARN-001"]
        assert len(warn_order) == 1
        assert warn_order[0]["shipped_quantity"] == 85
        assert warn_order[0]["pending_quantity"] == 15
        assert warn_order[0]["completion_rate"] == 0.85
        assert warn_order[0]["warning"] in ["接近总量提醒", "请按期发货"]


class TestPresetData:
    def test_warehouse_preset(self, db):
        wdao = WarehouseDAO(db)
        whs = wdao.list()
        assert len(whs) >= 1
        assert any(w["name"] == "成品库" for w in whs)

    def test_lab_standards_preset(self, db):
        lab_dao = LabDAO(db)
        standards = lab_dao.get_standards()
        assert len(standards) >= 5
        elements = {s["element"] for s in standards}
        assert "Mn" in elements
        assert "Si" in elements
        assert "P" in elements
        assert "S" in elements
        assert "C" in elements

        mn = next(s for s in standards if s["element"] == "Mn")
        assert mn["min_value"] == 60.0

    def test_common_specs(self, db):
        spec_dao = SpecDAO(db)
        specs = spec_dao.list()
        names = [s["name"] for s in specs]
        assert "SiMn6517" in names
        assert "SiMn6014" in names
        assert "FeMn65Si17" in names


class TestLocationOperations:
    def test_create_location_and_query(self, db):
        loc_dao = LocationDAO(db)
        loc_id = loc_dao.create("Z01", "成品库位1号")
        assert loc_id > 0

        locs = loc_dao.list()
        codes = [l["code"] for l in locs]
        assert "Z01" in codes

        loc = loc_dao.get(loc_id)
        assert loc["name"] == "成品库位1号"

    def test_available_qty(self, db):
        seal_dao = SealDAO(db)
        inbound_svc = InboundService(db)
        lab_dao = LabDAO(db)
        loc_dao = LocationDAO(db)

        loc_id = loc_dao.create("K01", "测试库位")
        bid = seal_dao.create_batch("11111", "11115")
        pid, _, _ = inbound_svc.create_pre_inbound(
            "2026-07-10", "LK01", 4, location_code="K01", seal_batch_id=bid)
        lab_dao.save_result(pid, mn_content=66.9, overall_result="合格")
        inbound_svc.confirm_inbound(pid)

        locs = loc_dao.list()
        k01 = next((l for l in locs if l["code"] == "K01"), None)
        assert k01 is not None
        assert k01["used_qty"] == 4


class TestCustomerSupplier:
    def test_customer_crud(self, db):
        cust_dao = CustomerDAO(db)
        cid = cust_dao.create(name="集成客户A", code="ICA")
        assert cid > 0

        c = cust_dao.get(cid)
        assert c["name"] == "集成客户A"

        cust_dao.update(cid, contact_person="张三", contact_phone="13800000000")
        c = cust_dao.get(cid)
        assert c["contact_person"] == "张三"
        assert c["contact_phone"] == "13800000000"

        customers = cust_dao.list(keyword="集成")
        assert len(customers) >= 1

    def test_supplier_crud(self, db):
        sup_dao = SupplierDAO(db)
        sid = sup_dao.create(name="供应商X", code="SUP-X")
        assert sid > 0

        s = sup_dao.get(sid)
        assert s["name"] == "供应商X"
