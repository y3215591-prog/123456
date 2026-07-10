import os
import tempfile
import pytest
from silicon_manganese_inventory.dao.database import DatabaseManager
from silicon_manganese_inventory.dao.seal_dao import SealDAO


@pytest.fixture
def seal_dao():
    tmp = tempfile.mkdtemp()
    db_path = os.path.join(tmp, "test.db")
    mgr = DatabaseManager(db_path)
    mgr.initialize()
    dao = SealDAO(mgr)
    yield dao
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


class TestSealBatchOperations:
    def test_create_batch_generates_seals(self, seal_dao):
        batch_id = seal_dao.create_batch("0000014101", "0000014110", "测试号段")
        assert batch_id > 0
        batch = seal_dao.get_batch(batch_id)
        assert batch["total_count"] == 10

    def test_create_batch_overlap_rejected(self, seal_dao):
        seal_dao.create_batch("00001", "00010")
        with pytest.raises(ValueError, match="重叠"):
            seal_dao.create_batch("00005", "00015")

    def test_create_batch_no_overlap(self, seal_dao):
        seal_dao.create_batch("00001", "00010")
        batch_id = seal_dao.create_batch("00011", "00020")
        assert batch_id > 0

    def test_create_batch_invalid_range(self, seal_dao):
        with pytest.raises(ValueError):
            seal_dao.create_batch("00010", "00001")

    def test_list_batches(self, seal_dao):
        seal_dao.create_batch("10001", "10005", "A")
        seal_dao.create_batch("20001", "20003", "B")
        batches = seal_dao.list_batches()
        assert len(batches) == 2

    def test_delete_unused_batch(self, seal_dao):
        batch_id = seal_dao.create_batch("30001", "30005")
        seal_dao.delete_batch(batch_id)
        assert seal_dao.list_batches() == []

    def test_delete_used_batch_rejected(self, seal_dao):
        batch_id = seal_dao.create_batch("40001", "40005")
        seals = seal_dao.get_available_seals(batch_id, limit=1)
        seal_dao.update_seal_status([seals[0]["id"]], "pre_allocated")
        with pytest.raises(ValueError, match="使用"):
            seal_dao.delete_batch(batch_id)


class TestSealQueryOperations:
    def test_get_available_seals(self, seal_dao):
        batch_id = seal_dao.create_batch("50001", "50010")
        seals = seal_dao.get_available_seals(batch_id)
        assert len(seals) == 10
        assert seals[0]["seal_code"] == "50001"
        assert seals[-1]["seal_code"] == "50010"

    def test_get_available_seals_limited(self, seal_dao):
        batch_id = seal_dao.create_batch("60001", "60010")
        seals = seal_dao.get_available_seals(batch_id, limit=3)
        assert len(seals) == 3

    def test_available_count(self, seal_dao):
        batch_id = seal_dao.create_batch("70001", "70005")
        assert seal_dao.get_available_count(batch_id) == 5

    def test_get_seals_by_status(self, seal_dao):
        batch_id = seal_dao.create_batch("80001", "80005")
        seals = seal_dao.get_seals_by_batch(batch_id, status="unused")
        assert len(seals) == 5

    def test_get_unused_seals(self, seal_dao):
        seal_dao.create_batch("90001", "90003")
        seals = seal_dao.get_unused_seals()
        assert len(seals) == 3


class TestSealStatusUpdate:
    def test_update_status_single(self, seal_dao):
        batch_id = seal_dao.create_batch("91001", "91003")
        seals = seal_dao.get_available_seals(batch_id)
        seal_ids = [s["id"] for s in seals[:2]]
        seal_dao.update_seal_status(seal_ids, "pre_allocated",
                                    pre_inbound_id=1, batch_no="TEST001", location_code="A01")
        remaining = seal_dao.get_available_count(batch_id)
        assert remaining == 1
        updated = seal_dao.get_seal_by_code("91001")
        assert updated["status"] == "pre_allocated"
        assert updated["batch_no"] == "TEST001"

    def test_get_used_seals(self, seal_dao):
        batch_id = seal_dao.create_batch("92001", "92002")
        seals = seal_dao.get_available_seals(batch_id)
        seal_ids = [s["id"] for s in seals]
        seal_dao.update_seal_status(seal_ids, "shipped")
        used = seal_dao.get_used_seals()
        assert len(used) == 2


class TestSealTrace:
    def test_trace_seal(self, seal_dao):
        batch_id = seal_dao.create_batch("93001", "93001")
        seal = seal_dao.get_seal_by_code("93001")
        result = seal_dao.trace_seal("93001")
        assert result is not None
        assert result["seal_code"] == "93001"
        assert result["batch_name"] is not None
