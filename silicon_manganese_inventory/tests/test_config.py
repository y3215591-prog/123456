import os
import sys
import tempfile
from unittest.mock import patch
from silicon_manganese_inventory import config


class TestConfig:
    def test_default_specs_not_empty(self):
        assert len(config.DEFAULT_SPECS) >= 4

    def test_default_lab_standards_count(self):
        assert len(config.DEFAULT_LAB_STANDARDS) == 5

    def test_default_alert_threshold_positive(self):
        assert config.DEFAULT_ALERT_THRESHOLD > 0

    def test_app_name(self):
        assert "硅锰合金" in config.APP_NAME

    def test_db_path_ends_with_db(self):
        assert config.DB_PATH.endswith(".db")

    @patch.object(sys, "platform", "win32")
    def test_get_app_data_dir_windows(self):
        with patch.dict(os.environ, {"APPDATA": r"C:\Users\test\AppData\Roaming"}, clear=True):
            app_dir = config.get_app_data_dir()
            assert "SiliconMnInventory" in app_dir

    @patch.object(sys, "platform", "darwin")
    def test_get_app_data_dir_mac(self):
        with patch.dict(os.environ, {}, clear=True):
            app_dir = config.get_app_data_dir()
            assert "Application Support" in app_dir
            assert "SiliconMnInventory" in app_dir

    @patch.object(sys, "platform", "linux")
    def test_get_app_data_dir_linux(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"XDG_DATA_HOME": tmpdir}, clear=True):
                app_dir = config.get_app_data_dir()
                assert "SiliconMnInventory" in app_dir
