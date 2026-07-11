from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QSpacerItem, QSizePolicy
from PySide6.QtCore import Signal
from PySide6.QtCore import Qt


class NavBar(QWidget):
    nav_changed = Signal(int)

    def __init__(self, items):
        super().__init__()
        self.setObjectName("navBar")
        self.items = items
        self.buttons = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        title = QLabel(" 功能导航")
        title.setObjectName("navTitle")
        title.setWordWrap(True)
        layout.addWidget(title)

        spacer = QSpacerItem(20, 8, QSizePolicy.Minimum, QSizePolicy.Fixed)
        layout.addItem(spacer)

        for name, idx in self.items:
            btn = QPushButton(f"  {name}")
            btn.setObjectName("navBtn")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty("active", "false")
            btn.clicked.connect(lambda checked, i=idx: self._on_click(i))
            layout.addWidget(btn)
            self.buttons.append(btn)

        layout.addStretch()
        if self.buttons:
            self.buttons[0].setChecked(True)
            self.buttons[0].setProperty("active", "true")
            self.buttons[0].style().unpolish(self.buttons[0])
            self.buttons[0].style().polish(self.buttons[0])

    def _on_click(self, index):
        for i, btn in enumerate(self.buttons):
            checked = (i == index)
            btn.setChecked(checked)
            btn.setProperty("active", "true" if checked else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.nav_changed.emit(index)
