from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QMessageBox,
)
from silicon_manganese_inventory.dao.seal_dao import SealDAO


class SealImportDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("导入铅封号段")
        self.setMinimumWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.start_input = QLineEdit()
        self.start_input.setPlaceholderText("起始编号（纯数字）")
        form.addRow("起始编号 *:", self.start_input)

        self.end_input = QLineEdit()
        self.end_input.setPlaceholderText("结束编号（纯数字）")
        form.addRow("结束编号 *:", self.end_input)

        self.batch_input = QLineEdit()
        self.batch_input.setPlaceholderText("如无则自动生成")
        form.addRow("号段批次:", self.batch_input)

        layout.addLayout(form)

        btn_layout = QVBoxLayout()
        save_btn = QPushButton("导入")
        save_btn.setStyleSheet("background-color: #27ae60; color: white; padding: 8px 24px;")
        save_btn.clicked.connect(self._import)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

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
        except ValueError as e:
            QMessageBox.warning(self, "错误", str(e))
            return
        self.accept()
