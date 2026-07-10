from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Signal, Qt


class NavBar(QWidget):
    nav_changed = Signal(int)

    def __init__(self, items):
        super().__init__()
        self.items = items
        self.buttons = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setStyleSheet("""
            NavBar { background-color: #2c3e50; }
            QPushButton {
                color: #bdc3c7; background: transparent; border: none;
                padding: 14px 12px; text-align: left; font-size: 14px;
            }
            QPushButton:hover { background-color: #34495e; color: #ecf0f1; }
            QPushButton:checked { background-color: #3498db; color: white; font-weight: bold; }
        """)

        title = QLabel("导航菜单")
        title.setStyleSheet("color: #ecf0f1; font-size: 15px; font-weight: bold; padding: 16px 12px 8px 12px;")
        layout.addWidget(title)

        for name, idx in self.items:
            btn = QPushButton(f"  {name}")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, i=idx: self._on_click(i))
            layout.addWidget(btn)
            self.buttons.append(btn)

        layout.addStretch()
        if self.buttons:
            self.buttons[0].setChecked(True)

    def _on_click(self, index):
        for i, btn in enumerate(self.buttons):
            btn.setChecked(i == index)
        self.nav_changed.emit(index)
