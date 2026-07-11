from PySide6.QtCore import QSettings, QByteArray


class UIPreferences:
    def __init__(self):
        self._settings = QSettings("SiliconMnInventory", "UI")

    def save_filter(self, page_key, field_index, value):
        self._settings.setValue(f"{page_key}/filter/{field_index}", value)

    def load_filter(self, page_key, field_index, default=""):
        return self._settings.value(f"{page_key}/filter/{field_index}", default)

    def save_header_state(self, page_key, state: QByteArray):
        self._settings.setValue(f"{page_key}/header_state", state.toBase64())

    def load_header_state(self, page_key):
        raw = self._settings.value(f"{page_key}/header_state")
        if raw is not None and raw:
            return QByteArray.fromBase64(raw)
        return QByteArray()

    def clear_page(self, page_key):
        self._settings.remove(f"{page_key}")
