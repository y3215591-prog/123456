from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QLabel, QMessageBox, QHeaderView,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
import openpyxl


class ExcelPreviewDialog(QDialog):
    def __init__(self, file_path, import_type, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.import_type = import_type
        self.all_rows = []
        self.checked = set()
        self.setWindowTitle("导入预览")
        self.setMinimumSize(900, 560)
        self._load_data()
        self._setup_ui()

    def _load_data(self):
        try:
            wb = openpyxl.load_workbook(self.file_path, data_only=True)
            ws = wb.active
            self.all_rows = []
            for row in ws.iter_rows(values_only=True):
                self.all_rows.append([str(c or "") for c in row])
            wb.close()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法读取文件: {e}")
            self.all_rows = []

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        row_count = max(len(self.all_rows) - 1, 0)
        info = QLabel(f"文件: {self.file_path} | 类型: {self.import_type} | 共 {row_count} 行数据")
        info.setStyleSheet("font-size: 14px; color: #2c3e50; font-weight: bold; padding: 8px 0;")
        layout.addWidget(info)

        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setStyleSheet("""
            QTableWidget { gridline-color: #ddd; font-size: 12px; }
            QHeaderView::section { background-color: #3498db; color: white; padding: 4px; }
        """)

        if self.all_rows:
            headers = self.all_rows[0]
            self.table.setColumnCount(len(headers))
            self.table.setHorizontalHeaderLabels(headers)
            self.table.setRowCount(len(self.all_rows) - 1)
            for i, row in enumerate(self.all_rows[1:]):
                self.checked.add(i)
                for j, val in enumerate(row):
                    item = QTableWidgetItem(val)
                    if i % 2 == 0:
                        item.setBackground(Qt.white)
                    self.table.setItem(i, j, item)
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        self.table.cellClicked.connect(self._on_cell_clicked)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()

        select_all_btn = QPushButton("全选")
        select_all_btn.clicked.connect(self._select_all)
        deselect_all_btn = QPushButton("全不选")
        deselect_all_btn.clicked.connect(self._deselect_all)

        self.checked_label = QLabel(f"已选: {len(self.checked)} / {len(self.all_rows) - 1}")
        self.checked_label.setStyleSheet("font-size: 13px; color: #27ae60; font-weight: bold;")

        btn_layout.addWidget(select_all_btn)
        btn_layout.addWidget(deselect_all_btn)
        btn_layout.addWidget(self.checked_label)
        btn_layout.addStretch()

        import_btn = QPushButton("确认导入")
        import_btn.setStyleSheet("background-color: #27ae60; color: white; padding: 8px 20px; border: none; border-radius: 4px; font-size: 14px;")
        import_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(import_btn)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

        self._refresh_highlights()

    def _on_cell_clicked(self, row, col):
        if row in self.checked:
            self.checked.discard(row)
        else:
            self.checked.add(row)
        self._refresh_highlights()
        self.checked_label.setText(f"已选: {len(self.checked)} / {len(self.all_rows) - 1}")

    def _select_all(self):
        self.checked = set(range(len(self.all_rows) - 1))
        self._refresh_highlights()
        self.checked_label.setText(f"已选: {len(self.checked)} / {len(self.all_rows) - 1}")

    def _deselect_all(self):
        self.checked.clear()
        self._refresh_highlights()
        self.checked_label.setText(f"已选: 0 / {len(self.all_rows) - 1}")

    def _refresh_highlights(self):
        for i in range(self.table.rowCount()):
            item = self.table.item(i, 0)
            if item:
                item.setBackground(QColor("#e8f5e9") if i in self.checked else QColor("#fce4ec"))

    def get_selected_rows(self):
        return [self.all_rows[i + 1] for i in sorted(self.checked)]
