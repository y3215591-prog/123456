from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QLabel, QMessageBox, QHeaderView,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
import openpyxl
from silicon_manganese_inventory.ui.dialogs.base_eas_dialog import BaseEasDialog


class ExcelPreviewDialog(BaseEasDialog):
    def __init__(self, file_path, import_type, parent=None):
        super().__init__(title="导入预览", width=960, height=580, parent=parent)
        self.file_path = file_path
        self.import_type = import_type
        self.all_rows = []
        self.checked = set()
        self._load_failed = False
        self._load_data()
        self._setup_ui()

    def _load_data(self):
        try:
            wb = openpyxl.load_workbook(self.file_path, data_only=True)
            ws = wb.active
            self.all_rows = [[str(c or "") for c in row] for row in ws.iter_rows(values_only=True)]
            wb.close()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法读取文件: {e}")
            self.all_rows = []
            self._load_failed = True

    def _setup_ui(self):
        row_count = max(len(self.all_rows) - 1, 0)
        info = QLabel(f"文件: {self.file_path} | 类型: {self.import_type} | 共 {row_count} 行数据")
        info.setStyleSheet("font-size: 13px; color: #6B7280; padding: 0; border: none; background: transparent;")
        self.body_layout.addWidget(info)

        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)

        if self.all_rows:
            headers = self.all_rows[0]
            self.table.setColumnCount(len(headers))
            self.table.setHorizontalHeaderLabels(headers)
            self.table.setRowCount(len(self.all_rows) - 1)
            for i, row in enumerate(self.all_rows[1:]):
                self.checked.add(i)
                for j, val in enumerate(row):
                    self.table.setItem(i, j, QTableWidgetItem(val))
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        self.table.cellClicked.connect(self._on_cell_clicked)
        self.body_layout.addWidget(self.table)

        self.btn_layout.addStretch(1)

        select_all_btn = QPushButton("全选")
        select_all_btn.setStyleSheet(
            "QPushButton { background: #F3F4F6; color: #374151; border: 1px solid #D1D5DB; padding: 5px 14px; border-radius: 3px; font-size: 13px; }"
            "QPushButton:hover { background: #E5E7EB; }")
        select_all_btn.clicked.connect(self._select_all)
        deselect_all_btn = QPushButton("全不选")
        deselect_all_btn.setStyleSheet(
            "QPushButton { background: #F3F4F6; color: #374151; border: 1px solid #D1D5DB; padding: 5px 14px; border-radius: 3px; font-size: 13px; }"
            "QPushButton:hover { background: #E5E7EB; }")
        deselect_all_btn.clicked.connect(self._deselect_all)

        self.checked_label = QLabel(f"已选: {len(self.checked)} / {row_count}")
        self.checked_label.setStyleSheet("font-size: 13px; color: #16A34A; font-weight: bold; border: none; background: transparent;")

        self.btn_layout.addWidget(select_all_btn)
        self.btn_layout.addWidget(deselect_all_btn)
        self.btn_layout.addWidget(self.checked_label)

        import_btn = QPushButton("确认导入")
        import_btn.setStyleSheet(
            "QPushButton { background: #16A34A; color: white; border: none; padding: 6px 16px; border-radius: 3px; font-size: 13px; font-weight: 600; }"
            "QPushButton:hover { background: #15803D; }"
            "QPushButton:disabled { background: #9CA3AF; }")
        import_btn.clicked.connect(self.accept)
        if self._load_failed:
            import_btn.setEnabled(False)
        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet(
            "QPushButton { background: #FFFFFF; color: #374151; border: 1px solid #D1D5DB; padding: 6px 16px; border-radius: 3px; font-size: 13px; }"
            "QPushButton:hover { background: #F3F4F6; }")
        cancel_btn.clicked.connect(self.reject)
        self.btn_layout.addWidget(import_btn)
        self.btn_layout.addWidget(cancel_btn)

        self._refresh_highlights()

    def _on_cell_clicked(self, row, col):
        if row in self.checked:
            self.checked.discard(row)
        else:
            self.checked.add(row)
        self._refresh_highlights()
        self.checked_label.setText(f"已选: {len(self.checked)} / {max(len(self.all_rows) - 1, 0)}")

    def _select_all(self):
        self.checked = set(range(max(len(self.all_rows) - 1, 0)))
        self._refresh_highlights()
        self.checked_label.setText(f"已选: {len(self.checked)} / {max(len(self.all_rows) - 1, 0)}")

    def _deselect_all(self):
        self.checked.clear()
        self._refresh_highlights()
        self.checked_label.setText(f"已选: 0 / {max(len(self.all_rows) - 1, 0)}")

    def _refresh_highlights(self):
        for i in range(self.table.rowCount()):
            item = self.table.item(i, 0)
            if item:
                item.setBackground(QColor("#DCFCE7") if i in self.checked else QColor("#FEE2E2"))

    def get_selected_rows(self):
        if not self.all_rows or not self.checked:
            return []
        result = [self.all_rows[0]]
        result.extend(self.all_rows[i + 1] for i in sorted(self.checked))
        return result
