import pytest
from silicon_manganese_inventory.models.models import (
    SealStatus, LabStatus, SealBatch, SealNumber, Spec, Customer,
    PreInboundOrder, OutboundOrder, LabResult, SalesOrder, DailyShipment,
    InventoryRow, OrderSummaryRow, row_to_dataclass,
)


class TestSealStatus:
    def test_enum_values(self):
        assert SealStatus.UNUSED == "unused"
        assert SealStatus.PRE_ALLOCATED == "pre_allocated"
        assert SealStatus.IN_STOCK == "in_stock"
        assert SealStatus.SHIPPED == "shipped"


class TestSealBatch:
    def test_available(self):
        b = SealBatch(total_count=100, used_count=30)
        assert b.available == 70

    def test_from_row(self):
        row = {"id": 1, "start_code": "10001", "end_code": "10010",
               "total_count": 10, "used_count": 3}
        b = row_to_dataclass(SealBatch, row)
        assert b.start_code == "10001"
        assert b.available == 7


class TestPreInboundOrder:
    def test_defaults(self):
        o = PreInboundOrder()
        assert o.lab_status == LabStatus.PENDING

    def test_quantity(self):
        o = PreInboundOrder(quantity=33.5, batch_no="B001",
                           date="2026-07-10", location_code="A01")
        assert o.quantity == 33.5


class TestOutboundOrder:
    def test_fields(self):
        o = OutboundOrder(order_no="PO001", date="2026-07-10",
                         customer_name="测试客户", quantity=10.0,
                         contract_no="CON-001", plate_no="沪A12345")
        assert o.plate_no == "沪A12345"
        assert o.contract_no == "CON-001"


class TestLabResult:
    def test_complete(self):
        r = LabResult(pre_inbound_id=1, mn_content=66.9, si_content=17.6,
                      overall_result="合格")
        assert r.overall_result == "合格"
        assert r.mn_content == 66.9

    def test_from_row_dict(self):
        row = dict(id=1, pre_inbound_id=5, mn_content=65.0, overall_result="合格")
        r = row_to_dataclass(LabResult, row)
        assert r.pre_inbound_id == 5


class TestDailyShipment:
    def test_fields(self):
        s = DailyShipment(seq_no=1, shipment_date="2026-07-10",
                         plate_no="沪B67890", customer_name="客户A",
                         load_quantity=33.5)
        assert s.load_quantity == 33.5


class TestInventoryRow:
    def test_row(self):
        r = InventoryRow(batch_no="B001", balance=100.0,
                        location_code="A01")
        assert r.balance == 100.0


class TestOrderSummaryRow:
    def test_warning(self):
        r = OrderSummaryRow(order_quantity=100, shipped_quantity=85,
                           warning="接近总量提醒")
        assert r.warning == "接近总量提醒"
        assert r.pending_quantity == 0
        assert r.completion_rate == 0.0


class TestRowToDataclass:
    def test_none_row(self):
        assert row_to_dataclass(Customer, None) is None

    def test_extra_fields_ignored(self):
        row = {"id": 1, "name": "测试", "extra_field": "should be ignored"}
        c = row_to_dataclass(Customer, row)
        assert c.name == "测试"
        assert not hasattr(c, "extra_field")
