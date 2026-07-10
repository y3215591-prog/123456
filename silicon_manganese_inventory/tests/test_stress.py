import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from silicon_manganese_inventory.dao.database import DatabaseManager
from silicon_manganese_inventory.dao.seal_dao import SealDAO
from silicon_manganese_inventory.dao.inbound_dao import InboundDAO
from silicon_manganese_inventory.dao.base_dao import LocationDAO, SalesOrderDAO
from silicon_manganese_inventory.services.seal_service import SealService
from silicon_manganese_inventory.services.inbound_service import InboundService
from silicon_manganese_inventory.services.outbound_service import OutboundService


def test_stress():
    db = DatabaseManager(db_path="/tmp/test_stress.db")
    if os.path.exists(db.db_path):
        os.remove(db.db_path)
    db.initialize()

    seal_dao = SealDAO(db)
    inbound_dao = InboundDAO(db)
    loc_dao = LocationDAO(db)
    seal_svc = SealService(db)
    inbound_svc = InboundService(db)

    loc_dao.get_or_create("Z01")
    loc_dao.get_or_create("A01-7月")

    print("=" * 50)
    print("1. 导入 25000 个铅封号")
    t0 = time.time()
    batch_id = seal_dao.create_batch(str(25001).zfill(5), str(50000).zfill(5))
    t1 = time.time()
    count = seal_dao.get_available_count(batch_id)
    print(f"   号段ID={batch_id}, 可用={count}, 耗时={t1 - t0:.2f}s")

    assert count == 25000, f"Expected 25000, got {count}"

    print("\n2. 预入库 20000 吨 (20000个铅封号)")
    t0 = time.time()
    pre_inbound_id, seal_start, seal_end = inbound_svc.create_pre_inbound(
        date="2026-07-10",
        batch_no="BATCH-20000T",
        quantity=20000,
        location_code="Z01",
        seal_batch_id=batch_id,
    )
    t1 = time.time()
    print(f"   预入库ID={pre_inbound_id}, 耗时={t1 - t0:.2f}s")

    print("\n3. 录入化验结果 (20000吨)")
    from silicon_manganese_inventory.services.lab_service import LabService
    lab_svc = LabService(db)
    lab_svc.record_result(pre_inbound_id, mn_content=65.0, si_content=17.0,
                          c_content=2.0, s_content=0.03, p_content=0.25)

    print("\n4. 入库确认 20000 吨 -> A01-7月")
    t0 = time.time()
    inbound_id = inbound_svc.confirm_inbound(pre_inbound_id, target_location="A01-7月")
    t1 = time.time()
    with db.get_connection() as conn:
        in_stock = conn.execute(
            "SELECT COUNT(*) FROM seal_numbers WHERE status='in_stock'"
        ).fetchone()[0]
    print(f"   入库ID={inbound_id}, in_stock={in_stock}, 耗时={t1 - t0:.2f}s")
    assert in_stock == 20000

    print("\n5. 出库 1000 吨")
    t0 = time.time()
    with db.get_connection() as conn:
        outbound_id = conn.execute(
            """INSERT INTO outbound_orders (order_no, date, quantity)
               VALUES ('OUT-STRESS-001', '2026-07-10', 1000)"""
        ).lastrowid
    start, end, _ = seal_svc.ship_seals_by_outbound(outbound_id, 1000)
    t1 = time.time()
    with db.get_connection() as conn:
        in_stock_after = conn.execute(
            "SELECT COUNT(*) FROM seal_numbers WHERE status='in_stock'"
        ).fetchone()[0]
        shipped = conn.execute(
            "SELECT COUNT(*) FROM seal_numbers WHERE status='shipped'"
        ).fetchone()[0]
    print(f"   出库: {start}~{end}, in_stock={in_stock_after}, shipped={shipped}, 耗时={t1 - t0:.2f}s")
    assert in_stock_after == 19000
    assert shipped == 1000

    print("\n6. 二次出库 1000 吨")
    t0 = time.time()
    with db.get_connection() as conn:
        outbound_id2 = conn.execute(
            """INSERT INTO outbound_orders (order_no, date, quantity)
               VALUES ('OUT-STRESS-002', '2026-07-10', 1000)"""
        ).lastrowid
    start2, end2, _ = seal_svc.ship_seals_by_outbound(outbound_id2, 1000)
    t1 = time.time()
    with db.get_connection() as conn:
        in_stock_after2 = conn.execute(
            "SELECT COUNT(*) FROM seal_numbers WHERE status='in_stock'"
        ).fetchone()[0]
        shipped2 = conn.execute(
            "SELECT COUNT(*) FROM seal_numbers WHERE status='shipped'"
        ).fetchone()[0]
    print(f"   出库: {start2}~{end2}, in_stock={in_stock_after2}, shipped={shipped2}, 耗时={t1 - t0:.2f}s")
    assert in_stock_after2 == 18000
    assert shipped2 == 2000

    print("\n7. 分页查询 200 条/页")
    t0 = time.time()
    seals, total = seal_dao.get_seals_by_batch(batch_id, offset=0, limit=200)
    t1 = time.time()
    print(f"   第1页: {len(seals)} 条, 总计={total}, 耗时={t1 - t0:.2f}s")

    total_pages = (total - 1) // 200 + 1
    t0 = time.time()
    seals_last, total2 = seal_dao.get_seals_by_batch(
        batch_id, offset=(total_pages - 1) * 200, limit=200)
    t1 = time.time()
    print(f"   第{total_pages}页: {len(seals_last)} 条, 耗时={t1 - t0:.2f}s")

    print("\n8. 库存报表 (GROUP_CONCAT)")
    from silicon_manganese_inventory.services.report_service import ReportService
    report_svc = ReportService(db)
    t0 = time.time()
    report = report_svc.get_inventory_report()
    t1 = time.time()
    for r in report:
        seal_len = len(r.get("seal_list", "") or "")
        print(f"   批次={r['batch_no']}, 库位={r['location_code']}, "
              f"结存={r['balance']}吨, seal_list长度={seal_len}")
    print(f"   报表查询耗时={t1 - t0:.2f}s")

    print("\n9. 并发入库模拟 (1000吨入库+1000吨出库)")
    with db.get_connection() as conn:
        conn.execute(
            "INSERT INTO sales_orders (order_no, quantity, material_desc) VALUES ('SO-STRESS', 5000, '硅锰合金')"
        )
    t0 = time.time()
    pre_id2, _, _ = inbound_svc.create_pre_inbound(
        date="2026-07-10",
        batch_no="BATCH-1000T",
        quantity=1000,
        location_code="Z01",
        seal_batch_id=batch_id,
    )
    lab_svc.record_result(pre_id2, mn_content=65.0, si_content=17.0,
                          c_content=2.0, s_content=0.03, p_content=0.25)
    inbound_svc.confirm_inbound(pre_id2, target_location="A01-7月")
    with db.get_connection() as conn:
        outbound_id3 = conn.execute(
            "INSERT INTO outbound_orders (order_no, date, quantity, sales_order_no) VALUES ('OUT-STRESS-003', '2026-07-10', 1000, 'SO-STRESS')"
        ).lastrowid
    seal_svc.ship_seals_by_outbound(outbound_id3, 1000)
    outbound_svc = OutboundService(db)
    order_summary = outbound_svc.list_outbound()
    t1 = time.time()
    print(f"   完整入库出库链路耗时={t1 - t0:.2f}s")

    with db.get_connection() as conn:
        remaining = conn.execute(
            "SELECT COUNT(*) FROM seal_numbers WHERE status='in_stock'"
        ).fetchone()[0]
    unused = seal_dao.get_available_count(batch_id)
    print(f"   最终库存={remaining}吨, 未使用={unused}个")
    assert remaining == 18000

    print("\n" + "=" * 50)
    print("ALL STRESS TESTS PASSED")
    print("=" * 50)


if __name__ == "__main__":
    test_stress()
