import os
import tempfile
import pytest
from silicon_manganese_inventory.dao.database import DatabaseManager
from silicon_manganese_inventory.dao.inbound_dao import InboundDAO
from silicon_manganese_inventory.dao.outbound_dao import OutboundDAO
from silicon_manganese_inventory.dao.lab_dao import LabDAO
from silicon_manganese_inventory.dao.seal_dao import SealDAO
from silicon_manganese_inventory.dao.base_dao import (
    CustomerDAO, SupplierDAO, LocationDAO, SpecDAO,
    WarehouseDAO, SalesOrderDAO, DailyShipmentDAO,
)


@pytest.fixture
def db():
    tmp = tempfile.mkdtemp()
    db_path = os.path.join(tmp, "test.db")
    mgr = DatabaseManager(db_path)
    mgr.initialize()
    yield mgr
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def seal_dao(db):
    return SealDAO(db)


class TestInboundDAO:
    @pytest.fixture
    def dao(self, db):
        return InboundDAO(db)

    def test_create_pre_inbound(self, dao):
        pid = dao.create_pre_inbound(date="2026-07-10", batch_no="1226062111",
                                     quantity=34, location_code="A01")
        assert pid > 0
        row = dao.get_pre_inbound(pid)
        assert row["batch_no"] == "1226062111"
        assert row["quantity"] == 34

    def test_create_pre_inbound_custom_order_no(self, dao):
        pid = dao.create_pre_inbound(order_no="PI-CUSTOM-001", date="2026-07-10",
                                     batch_no="B001", quantity=10)
        row = dao.get_pre_inbound(pid)
        assert row["order_no"] == "PI-CUSTOM-001"

    def test_update_pre_inbound(self, dao):
        pid = dao.create_pre_inbound(date="2026-07-10", batch_no="OLD", quantity=5)
        dao.update_pre_inbound(pid, batch_no="NEW", quantity=10)
        row = dao.get_pre_inbound(pid)
        assert row["batch_no"] == "NEW"
        assert row["quantity"] == 10

    def test_delete_pre_inbound(self, dao):
        pid = dao.create_pre_inbound(date="2026-07-10", batch_no="TODEL", quantity=1)
        dao.delete_pre_inbound(pid)
        assert dao.get_pre_inbound(pid) is None

    def test_list_pre_inbound_filter(self, dao):
        dao.create_pre_inbound(date="2026-07-01", batch_no="B001", quantity=10, location_code="A01")
        dao.create_pre_inbound(date="2026-07-02", batch_no="B002", quantity=20, location_code="A02")
        results = dao.list_pre_inbound(batch_no="B001")
        assert len(results) == 1
        results = dao.list_pre_inbound(location_code="A02")
        assert len(results) == 1
        results = dao.list_pre_inbound(lab_status="pending")
        assert len(results) == 2

    def test_create_inbound_from_pre_inbound(self, dao, seal_dao):
        batch_id = seal_dao.create_batch("20001", "20010")
        pid = dao.create_pre_inbound(date="2026-07-10", batch_no="B001",
                                     quantity=5, location_code="A01",
                                     seal_batch_id=batch_id,
                                     seal_start="20001", seal_end="20005")
        inbound_id = dao.create_inbound(pid, operator="admin")
        assert inbound_id > 0
        row = dao.get_inbound(inbound_id)
        assert row["batch_no"] == "B001"

    def test_create_inbound_nonexistent_pre(self, dao):
        with pytest.raises(ValueError, match="不存在"):
            dao.create_inbound(9999)


class TestOutboundDAO:
    @pytest.fixture
    def dao(self, db):
        return OutboundDAO(db)

    def test_create_outbound(self, dao, db):
        cdao = CustomerDAO(db)
        cid = cdao.create(code="C001", name="测试客户")
        oid, ono = dao.create_outbound(date="2026-07-10", customer_id=cid,
                                       sales_order_no="SO001", quantity=33,
                                       seal_start="10001", seal_end="10033")
        assert oid > 0
        assert ono.startswith("PO")
        row = dao.get_outbound(oid)
        assert row["customer_name"] == "测试客户"

    def test_list_outbound_filter(self, dao, db):
        cdao = CustomerDAO(db)
        cid = cdao.create(code="C002", name="客户二")
        dao.create_outbound(date="2026-07-01", customer_id=cid, quantity=10,
                            sales_order_no="SO-A")
        dao.create_outbound(date="2026-07-02", customer_id=cid, quantity=20,
                            sales_order_no="SO-B")
        results = dao.list_outbound(sales_order_no="SO-A")
        assert len(results) == 1


class TestLabDAO:
    @pytest.fixture
    def dao(self, db):
        return LabDAO(db)

    def test_save_and_get_result(self, dao, db):
        inbound_dao = InboundDAO(db)
        pid = inbound_dao.create_pre_inbound(date="2026-07-10", batch_no="TEST", quantity=10)
        lid = dao.save_result(pid, mn_content=66.9, si_content=17.6,
                              mn_result="合格", si_result="合格",
                              overall_result="合格")
        assert lid > 0
        result = dao.get_result(pid)
        assert result["mn_content"] == 66.9
        assert result["overall_result"] == "合格"

    def test_update_result(self, dao, db):
        inbound_dao = InboundDAO(db)
        pid = inbound_dao.create_pre_inbound(date="2026-07-10", batch_no="TEST2", quantity=5)
        dao.save_result(pid, mn_content=60.0, overall_result="不合格")
        dao.save_result(pid, mn_content=66.5, overall_result="合格")
        result = dao.get_result(pid)
        assert result["mn_content"] == 66.5

    def test_get_standards(self, dao):
        standards = dao.get_standards()
        assert len(standards) == 5

    def test_update_standard(self, dao):
        dao.update_standard("Mn", 62.0, 75.0)
        standards = dao.get_standards()
        mn = [s for s in standards if s["element"] == "Mn"][0]
        assert mn["min_value"] == 62.0


class TestCustomerDAO:
    @pytest.fixture
    def dao(self, db):
        return CustomerDAO(db)

    def test_create_and_get(self, dao):
        cid = dao.create(code="C100", name="测试公司", contact_person="张三",
                         contact_phone="13800138000")
        assert cid > 0
        row = dao.get(cid)
        assert row["name"] == "测试公司"

    def test_get_by_code(self, dao):
        dao.create(code="C101", name="按代码查")
        row = dao.get_by_code("C101")
        assert row["name"] == "按代码查"

    def test_list_with_keyword(self, dao):
        dao.create(code="C102", name="杭州创达")
        dao.create(code="C103", name="厦门象屿")
        results = dao.list(keyword="厦门")
        assert len(results) == 1
        assert results[0]["name"] == "厦门象屿"

    def test_update(self, dao):
        cid = dao.create(code="C104", name="旧名称")
        dao.update(cid, name="新名称", contact_phone="13900000000")
        row = dao.get(cid)
        assert row["name"] == "新名称"


class TestLocationDAO:
    @pytest.fixture
    def dao(self, db):
        return LocationDAO(db)

    def test_create_and_list(self, dao):
        before = len(dao.list())
        dao.create("A01", "库位A01")
        dao.create("A02", "库位A02")
        results = dao.list()
        assert len(results) == before + 2

    def test_delete_with_inventory_blocked(self, dao, db):
        from silicon_manganese_inventory.dao.seal_dao import SealDAO
        seal_dao = SealDAO(db)
        dao.create("B01")
        batch_id = seal_dao.create_batch("30001", "30005")
        seals = seal_dao.get_available_seals(batch_id, limit=1)
        seal_dao.update_seal_status([seals[0]["id"]], "in_stock",
                                    location_code="B01")
        loc = dao.get_by_code("B01")
        with pytest.raises(ValueError, match="库存"):
            dao.delete(loc["id"])


class TestSalesOrderDAO:
    @pytest.fixture
    def dao(self, db):
        return SalesOrderDAO(db)

    def test_create_and_query(self, dao):
        dao.create(order_no="110000023", customer_code="15845",
                   customer_name="浙江浙冶亚新贸易有限公司",
                   material_desc="FeMn65Si17,普碳锰硅合金", quantity=1000,
                   delivery_end="2026-06-16", pickup_method="EXW(客户自提)")
        row = dao.get_by_order_no("110000023")
        assert row["customer_name"] == "浙江浙冶亚新贸易有限公司"
        assert row["quantity"] == 1000

    def test_list_with_keyword(self, dao):
        dao.create(order_no="SO-A", customer_name="公司A", quantity=100)
        dao.create(order_no="SO-B", customer_name="公司B", quantity=200)
        results = dao.list(keyword="公司B")
        assert len(results) == 1


class TestDailyShipmentDAO:
    @pytest.fixture
    def dao(self, db):
        return DailyShipmentDAO(db)

    def test_create_and_list(self, dao):
        dao.create(seq_no=1, shipment_date="2026-06-29", plate_no="蒙C24230",
                   customer_code="15783", customer_name="天津津鑫实业有限公司",
                   sales_order_no="110000001", material_name="普碳锰硅合金",
                   spec="10-60mm", batch_no="1026051501", load_quantity=32,
                   gross_weight=47.56, tare_weight=15.5, net_weight=32.06)
        results = dao.list()
        assert len(results) == 1
        assert results[0]["plate_no"] == "蒙C24230"
        assert results[0]["load_quantity"] == 32

    def test_update(self, dao):
        sid = dao.create(seq_no=1)
        dao.update(sid, customer_received_weight=31.5, remark="已确认")
        row = dao.get(sid)
        assert row["customer_received_weight"] == 31.5
        assert row["remark"] == "已确认"

    def test_filter_by_plate(self, dao):
        dao.create(seq_no=1, shipment_date="2026-07-01", plate_no="晋M57363")
        dao.create(seq_no=2, shipment_date="2026-07-01", plate_no="鲁RR2962")
        results = dao.list(plate_no="晋M")
        assert len(results) == 1
