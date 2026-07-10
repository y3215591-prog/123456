import os
import sys


def get_app_data_dir():
    if sys.platform == "win32":
        base = os.getenv("APPDATA", os.path.expanduser("~"))
    elif sys.platform == "darwin":
        base = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    else:
        base = os.getenv("XDG_DATA_HOME", os.path.join(os.path.expanduser("~"), ".local", "share"))
    app_dir = os.path.join(base, "SiliconMnInventory")
    os.makedirs(app_dir, exist_ok=True)
    return app_dir


DB_PATH = os.path.join(get_app_data_dir(), "silicon_mn_inventory.db")

APP_NAME = "硅锰合金库存管理系统"
APP_VERSION = "1.0.0"

DEFAULT_SPECS = [
    ("FeMn65Si17", 65.0, 17.0, "普碳锰硅合金"),
    ("FeMn65Si17低P", 65.0, 17.0, "低磷锰硅合金"),
    ("SiMn6517", 65.0, 17.0, "硅锰6517"),
    ("SiMn6014", 60.0, 14.0, "硅锰6014"),
]

DEFAULT_LAB_STANDARDS = [
    ("Mn", 60.0, 75.0),
    ("Si", 14.0, 20.0),
    ("C", 0.0, 2.5),
    ("S", 0.0, 0.05),
    ("P", 0.0, 0.35),
]

DEFAULT_ALERT_THRESHOLD = 50

DEFAULT_LOCATIONS = [
    ("Z01", "自然块库位1", 1),
    ("Z02", "自然块库位2", 1),
    ("Z03", "自然块库位3", 1),
    ("A01-7月", "成品库位A01-7月", 1),
    ("A01-8月", "成品库位A01-8月", 1),
    ("A01-9月", "成品库位A01-9月", 1),
    ("A01-10月", "成品库位A01-10月", 1),
    ("A01-11月", "成品库位A01-11月", 1),
    ("A01-12月", "成品库位A01-12月", 1),
    ("A01-2701", "成品库位A01-2027年1月", 1),
    ("A01-2702", "成品库位A01-2027年2月", 1),
    ("A01-2703", "成品库位A01-2027年3月", 1),
    ("A01-2704", "成品库位A01-2027年4月", 1),
    ("A01-2705", "成品库位A01-2027年5月", 1),
    ("A01-2706", "成品库位A01-2027年6月", 1),
    ("A01-2707", "成品库位A01-2027年7月", 1),
    ("A01-2708", "成品库位A01-2027年8月", 1),
    ("A01-2709", "成品库位A01-2027年9月", 1),
    ("A01-2710", "成品库位A01-2027年10月", 1),
    ("A01-2711", "成品库位A01-2027年11月", 1),
    ("A01-2712", "成品库位A01-2027年12月", 1),
]
