import os
import tempfile
import pytest
from silicon_manganese_inventory.dao.database import DatabaseManager


@pytest.fixture
def db():
    tmp = tempfile.mkdtemp()
    db_path = os.path.join(tmp, "test.db")
    mgr = DatabaseManager(db_path)
    mgr.initialize()
    yield mgr
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


class TestDatabaseInitialization:
    def test_creates_tables(self, db):
        with db.get_connection() as conn:
            tables = [
                row[0] for row in
                conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
            ]
        assert "seal_numbers" in tables
        assert "seal_batches" in tables
        assert "pre_inbound_orders" in tables
        assert "inbound_orders" in tables
        assert "outbound_orders" in tables
        assert "lab_results" in tables
        assert "lab_standards" in tables
        assert "customers" in tables
        assert "suppliers" in tables
        assert "locations" in tables
        assert "warehouses" in tables
        assert "specs" in tables
        assert "factories" in tables
        assert "sales_orders" in tables
        assert "daily_shipments" in tables

    def test_seeds_default_specs(self, db):
        with db.get_connection() as conn:
            count = conn.execute("SELECT COUNT(*) FROM specs").fetchone()[0]
        assert count >= 4

    def test_seeds_default_lab_standards(self, db):
        with db.get_connection() as conn:
            count = conn.execute("SELECT COUNT(*) FROM lab_standards").fetchone()[0]
        assert count == 5

    def test_seeds_default_warehouse(self, db):
        with db.get_connection() as conn:
            row = conn.execute("SELECT name FROM warehouses WHERE id=1").fetchone()
        assert row is not None
        assert row["name"] == "成品库"

    def test_idempotent_initialize(self, db):
        db.initialize()
        with db.get_connection() as conn:
            count = conn.execute("SELECT COUNT(*) FROM specs").fetchone()[0]
        assert count >= 4


class TestSealNumberConstraints:
    def test_seal_status_check_constraint(self, db):
        with db.get_connection() as conn:
            conn.execute("INSERT INTO seal_batches (start_code, end_code, total_count) VALUES (?, ?, ?)",
                         ("00001", "00001", 1))
            conn.execute(
                "INSERT INTO seal_numbers (seal_code, seal_batch_id, status) VALUES (?, ?, 'unused')",
                ("00001", conn.execute("SELECT last_insert_rowid()").fetchone()[0]),
            )
        with pytest.raises(Exception):
            with db.get_connection() as conn:
                conn.execute("UPDATE seal_numbers SET status='invalid_status'")

    def test_seal_code_unique(self, db):
        with db.get_connection() as conn:
            conn.execute("INSERT INTO seal_batches (start_code, end_code, total_count) VALUES (?, ?, ?)",
                         ("10001", "10001", 1))
            batch_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute(
                "INSERT INTO seal_numbers (seal_code, seal_batch_id) VALUES (?, ?)",
                ("10001", batch_id),
            )
        with pytest.raises(Exception):
            with db.get_connection() as conn:
                conn.execute(
                    "INSERT INTO seal_numbers (seal_code, seal_batch_id) VALUES (?, ?)",
                    ("10001", batch_id),
                )


class TestBackupRestore:
    def test_backup_creates_file(self, db):
        with db.get_connection() as conn:
            conn.execute("INSERT INTO warehouses (name) VALUES ('test_warehouse')")
        backup = os.path.join(tempfile.mkdtemp(), "backup.db")
        db.backup(backup)
        assert os.path.exists(backup)
        assert os.path.getsize(backup) > 0

    def test_restore_from_backup(self, db):
        with db.get_connection() as conn:
            conn.execute("INSERT INTO warehouses (name) VALUES ('original_warehouse')")
        backup = os.path.join(tempfile.mkdtemp(), "backup.db")
        db.backup(backup)
        with db.get_connection() as conn:
            conn.execute("DELETE FROM locations")
            conn.execute("DELETE FROM warehouses")
            count = conn.execute("SELECT COUNT(*) FROM warehouses").fetchone()[0]
        assert count == 0
        db.restore(backup)
        with db.get_connection() as conn:
            count = conn.execute("SELECT COUNT(*) FROM warehouses WHERE name='original_warehouse'").fetchone()[0]
        assert count == 1

    def test_restore_missing_file_raises(self, db):
        with pytest.raises(FileNotFoundError):
            db.restore("/nonexistent/path/backup.db")
