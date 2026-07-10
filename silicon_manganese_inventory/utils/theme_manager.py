from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QSettings
from silicon_manganese_inventory.utils.themes import THEMES, DEFAULT_THEME, FROSTED_BASE, FROSTED_CARD, NAVBAR_STYLE


class ThemeManager:
    _instance = None

    def __init__(self):
        self._settings = QSettings("SiliconMnInventory", "UI")
        self._current_key = self._settings.value("theme", DEFAULT_THEME)
        self._theme = THEMES.get(self._current_key, THEMES[DEFAULT_THEME])

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def current(self):
        return self._theme

    @property
    def current_key(self):
        return self._current_key

    def set_theme(self, key):
        if key not in THEMES:
            return
        self._current_key = key
        self._theme = THEMES[key]
        self._settings.setValue("theme", key)

    def hex_to_rgb(self, hex_color):
        h = hex_color.lstrip("#")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

    def apply_global(self, app=None):
        t = self._theme
        r, g, b = self.hex_to_rgb(t["accent"])
        qss = FROSTED_BASE.format(
            bg=t["bg"], card=t["card"], table_header=t["table_header"],
            text_primary=t["text_primary"], text_secondary=t["text_secondary"],
            accent=t["accent"], accent_r=r, accent_g=g, accent_b=b,
        )
        if app:
            app.setStyleSheet(qss)
        return qss

    def frosted_card_style(self):
        return FROSTED_CARD.format(card=self._theme["card"])

    def navbar_style(self):
        t = self._theme
        r, g, b = self.hex_to_rgb(t["accent"])
        return NAVBAR_STYLE.format(
            sidebar=t["sidebar"], text_primary=t["text_primary"],
            accent=t["accent"], accent_r=r, accent_g=g, accent_b=b,
        )


def apply_frosted(widget: QWidget):
    tm = ThemeManager.instance()
    widget.setAttribute(0x0002, False)  # 保持透明度
    widget.setStyleSheet(widget.styleSheet() + tm.frosted_card_style())
