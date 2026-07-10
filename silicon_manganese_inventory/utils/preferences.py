from PySide6.QtCore import QSettings


class UIPreferences:
    def __init__(self):
        self._settings = QSettings("SiliconMnInventory", "UI")

    def save_filter(self, page_key, field_index, value):
        self._settings.setValue(f"{page_key}/filter/{field_index}", value)

    def load_filter(self, page_key, field_index, default=""):
        return self._settings.value(f"{page_key}/filter/{field_index}", default)

    def save_column_widths(self, page_key, widths):
        self._settings.setValue(f"{page_key}/column_widths", ",".join(str(w) for w in widths))

    def load_column_widths(self, page_key):
        raw = self._settings.value(f"{page_key}/column_widths", "")
        if not raw:
            return []
        return [int(x) for x in str(raw).split(",") if x]

    def clear_page(self, page_key):
        self._settings.remove(f"{page_key}")
