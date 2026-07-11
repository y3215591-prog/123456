from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton, QWidget,
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QSizePolicy,
)
from PySide6.QtCore import Qt
from silicon_manganese_inventory.utils.theme_manager import ThemeManager

_tm = ThemeManager.instance()


def _theme_color(key, default):
    try:
        return _tm.current.get(key, default)
    except Exception:
        return default


class BaseEasDialog(QDialog):
    def __init__(self, title="", width=560, height=480, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(width, height)
        self.setStyleSheet(f"QDialog {{ background: {_theme_color('bg', '#F5F7FA')}; }}")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self._title_bar = QFrame()
        self._title_bar.setObjectName("dlgTitle")
        self._title_bar.setFixedHeight(44)
        self._title_bar.setStyleSheet(
            f"QFrame#dlgTitle {{ background: {_theme_color('accent', '#2B579A')}; }}")
        title_layout = QHBoxLayout(self._title_bar)
        title_layout.setContentsMargins(16, 0, 16, 0)

        self._title_label = QLabel(title)
        self._title_label.setObjectName("dlgTitle")
        self._title_label.setStyleSheet(
            "color: #FFFFFF; font-size: 15px; font-weight: bold; border: none; background: transparent;")
        title_layout.addWidget(self._title_label)
        self.main_layout.addWidget(self._title_bar)

        self._body = QWidget()
        self._body.setStyleSheet(
            f"QWidget#dlgBody {{ background: {_theme_color('bg', '#F5F7FA')}; }}")
        self._body.setObjectName("dlgBody")
        self.body_layout = QVBoxLayout(self._body)
        self.body_layout.setContentsMargins(20, 16, 20, 16)
        self.body_layout.setSpacing(12)
        self.main_layout.addWidget(self._body, 1)

        self._btn_bar = QFrame()
        self._btn_bar.setObjectName("btnBar")
        self._btn_bar.setFixedHeight(56)
        self._btn_bar.setStyleSheet(
            "QFrame#btnBar { background: #FAFBFC; border-top: 1px solid #E2E8F0; }")
        btn_layout = QHBoxLayout(self._btn_bar)
        btn_layout.setContentsMargins(16, 0, 16, 0)
        btn_layout.addStretch()
        self.btn_layout = btn_layout
        self.main_layout.addWidget(self._btn_bar)

    def add_primary_button(self, text, callback, color="#2B579A"):
        btn = QPushButton(text)
        btn.setStyleSheet(f"""
            QPushButton {{ background: {color}; color: white; border: none;
                          padding: 7px 20px; border-radius: 3px; font-size: 13px; font-weight: 600; }}
            QPushButton:hover {{ background: {self._darken(color)}; }}
        """)
        btn.clicked.connect(callback)
        btn.setDefault(True)
        self.btn_layout.addWidget(btn)
        return btn

    def add_cancel_button(self):
        btn = QPushButton("取消")
        btn.setStyleSheet("""
            QPushButton { background: #FFFFFF; color: #374151; border: 1px solid #D1D5DB;
                          padding: 7px 20px; border-radius: 3px; font-size: 13px; }
            QPushButton:hover { background: #F3F4F6; }
        """)
        btn.clicked.connect(self.reject)
        self.btn_layout.addWidget(btn)
        return btn

    def add_close_button(self):
        btn = QPushButton("关闭")
        btn.setStyleSheet("""
            QPushButton { background: #2B579A; color: white; border: none;
                          padding: 7px 20px; border-radius: 3px; font-size: 13px; }
            QPushButton:hover { background: #234881; }
        """)
        btn.clicked.connect(self.accept)
        self.btn_layout.addWidget(btn)
        return btn

    def add_section_title(self, text, parent_layout=None):
        lbl = QLabel(text)
        lbl.setObjectName("sectionTitle")
        lbl.setStyleSheet(
            f"color: {_theme_color('text_primary', '#1D2939')}; font-size: 13px; font-weight: 600; padding: 0px; border: none; background: transparent;")
        (parent_layout or self.body_layout).addWidget(lbl)
        return lbl

    def add_card(self, parent_layout=None):
        card = QFrame()
        card.setObjectName("dlgCard")
        card.setStyleSheet(
            "QFrame#dlgCard { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 4px; }")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 12, 16, 12)
        card_layout.setSpacing(8)
        (parent_layout or self.body_layout).addWidget(card)
        return card, card_layout

    def h_line(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #E2E8F0; max-height: 1px;")
        self.body_layout.addWidget(line)

    def _darken(self, color):
        if color.startswith("#") and len(color) == 7:
            r = max(0, int(color[1:3], 16) - 25)
            g = max(0, int(color[3:5], 16) - 25)
            b = max(0, int(color[5:7], 16) - 25)
            return f"#{r:02x}{g:02x}{b:02x}"
        return color

    @staticmethod
    def style_input(widget):
        widget.setStyleSheet("""
            border: 1px solid #D1D5DB; border-radius: 3px; padding: 5px 10px;
            font-size: 13px; background: #FFFFFF; min-height: 28px;
        """)

    @staticmethod
    def style_textarea(widget):
        widget.setStyleSheet("""
            border: 1px solid #D1D5DB; border-radius: 3px; padding: 5px 8px;
            font-size: 13px; background: #FFFFFF;
        """)

    @staticmethod
    def style_spin(widget):
        widget.setStyleSheet("""
            border: 1px solid #D1D5DB; border-radius: 3px; padding: 5px 10px;
            font-size: 13px; background: #FFFFFF; min-height: 28px;
        """)

    @staticmethod
    def style_combo(widget):
        widget.setStyleSheet("""
            QComboBox { border: 1px solid #D1D5DB; border-radius: 3px; padding: 5px 10px;
                        font-size: 13px; background: #FFFFFF; min-height: 28px; }
            QComboBox::drop-down { border: none; padding-right: 8px; }
        """)

    def add_form_row(self, label_text, widget, parent_layout=None):
        layout = parent_layout or self.body_layout
        row = QHBoxLayout()
        row.setSpacing(8)
        lbl = QLabel(label_text)
        lbl.setFixedWidth(80)
        lbl.setStyleSheet("font-size: 13px; color: #374151; border: none; background: transparent;")
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row.addWidget(lbl)
        row.addWidget(widget, 1)
        layout.addLayout(row)
        return row
