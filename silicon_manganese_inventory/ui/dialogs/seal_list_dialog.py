from PySide6.QtWidgets import QTextEdit
from PySide6.QtCore import Qt
from silicon_manganese_inventory.ui.dialogs.base_eas_dialog import BaseEasDialog


class SealListDialog(BaseEasDialog):
    def __init__(self, seal_list_str, parent=None):
        self.seal_list_str = seal_list_str
        seals_count = len([s for s in seal_list_str.split(",") if s.strip()])
        super().__init__(title=f"铅封号明细 - 共 {seals_count} 个", width=500, height=400, parent=parent)
        self._setup_ui()

    def _setup_ui(self):
        card, cl = self.add_card()
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setStyleSheet("border: none; font-size: 13px; color: #374151; font-family: 'Consolas', monospace; background: transparent;")
        cl.addWidget(self.text_edit)

        self.add_close_button()

        seals = [s.strip() for s in self.seal_list_str.split(",") if s.strip()]
        formatted = ""
        for i, seal in enumerate(seals):
            formatted += f"{seal:>12}"
            formatted += "\n" if (i + 1) % 6 == 0 else "  "
        self.text_edit.setText(formatted)
