from PySide6.QtWidgets import QLineEdit, QMessageBox
from silicon_manganese_inventory.dao.seal_dao import SealDAO
from silicon_manganese_inventory.ui.dialogs.base_eas_dialog import BaseEasDialog


class SealImportDialog(BaseEasDialog):
    def __init__(self, db, parent=None):
        super().__init__(title="导入铅封号段", width=420, height=300, parent=parent)
        self.db = db
        self._setup_ui()

    def _setup_ui(self):
        card, cl = self.add_card()

        self.start_input = QLineEdit()
        self.start_input.setPlaceholderText("起始编号（纯数字）")
        self.style_input(self.start_input)
        self.add_form_row("起始编号 *:", self.start_input, cl)

        self.end_input = QLineEdit()
        self.end_input.setPlaceholderText("结束编号（纯数字）")
        self.style_input(self.end_input)
        self.add_form_row("结束编号 *:", self.end_input, cl)

        self.batch_input = QLineEdit()
        self.batch_input.setPlaceholderText("如无则自动生成")
        self.style_input(self.batch_input)
        self.add_form_row("号段批次:", self.batch_input, cl)

        self.add_primary_button("导入", self._import, "#16A34A")
        self.add_cancel_button()

    def _import(self):
        start = self.start_input.text().strip()
        end = self.end_input.text().strip()
        batch_code = self.batch_input.text().strip() or None
        if not start or not end:
            QMessageBox.warning(self, "错误", "起始和结束编号为必填项")
            return
        try:
            start_int = int(start)
            end_int = int(end)
        except ValueError:
            QMessageBox.warning(self, "错误", "铅封编号必须为纯数字")
            return
        if start_int > end_int:
            QMessageBox.warning(self, "错误", "起始编号不能大于结束编号")
            return
        try:
            dao = SealDAO(self.db)
            dao.import_range(start_int, end_int, batch_code=batch_code)
        except Exception as e:
            QMessageBox.warning(self, "错误", str(e))
            return
        self.accept()
