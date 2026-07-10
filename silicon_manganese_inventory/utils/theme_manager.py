from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QSettings
from silicon_manganese_inventory.utils.themes import THEMES, DEFAULT_THEME, EAS_BASE, EAS_CARD, EAS_NAVBAR, EAS_DIALOG


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

    def apply_global(self, app=None):
        t = self._theme
        qss = EAS_BASE.format(**t)
        if app:
            app.setStyleSheet(qss)
        return qss

    def card_style(self):
        return EAS_CARD.format(**self._theme)

    def navbar_style(self):
        return EAS_NAVBAR.format(**self._theme)

    def dialog_style(self):
        return EAS_DIALOG.format(**self._theme)


def apply_frosted(widget: QWidget):
    tm = ThemeManager.instance()
    widget.setStyleSheet(widget.styleSheet() + tm.card_style())
