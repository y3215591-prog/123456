from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog, QMessageBox,
    QComboBox,
)
from silicon_manganese_inventory.ui.base_page import BasePage
from silicon_manganese_inventory.ui.dialogs.excel_preview_dialog import ExcelPreviewDialog
from silicon_manganese_inventory.services.excel_service import ExcelService, ExportService


class ExcelImportPage(BasePage):
    def __init__(self, db):
        super().__init__(db, "Excel 导入/导出")
        self.excel_svc = ExcelService(db)

        import_layout = QVBoxLayout()
        import_label = QLabel("导入")
        import_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #2c3e50;")

        self.import_type_combo = QComboBox()
        self.import_type_combo.addItem("销售订单", "sales_order")
        self.import_type_combo.addItem("日发货流水", "daily_shipment")

        select_btn = QPushButton("选择文件并预览导入")
        select_btn.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white; border: none;
                          padding: 10px 24px; border-radius: 4px; font-size: 14px; }
            QPushButton:hover { background-color: #219a52; }
        """)
        select_btn.clicked.connect(self._import_file)

        import_row = QHBoxLayout()
        import_row.addWidget(QLabel("导入类型:"))
        import_row.addWidget(self.import_type_combo)
        import_row.addWidget(select_btn)
        import_row.addStretch()

        import_layout.addWidget(import_label)
        import_layout.addLayout(import_row)

        self.result_label = QLabel("")
        self.result_label.setStyleSheet("font-size: 13px; color: #7f8c8d; padding: 8px 0;")
        import_layout.addWidget(self.result_label)
        self.main_layout.insertLayout(2, import_layout)

        export_layout = QVBoxLayout()
        export_label = QLabel("导出")
        export_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #2c3e50; margin-top: 16px;")

        export_inv_btn = QPushButton("导出成品库存")
        export_inv_btn.setStyleSheet("""
            QPushButton { background-color: #2980b9; color: white; border: none;
                          padding: 10px 24px; border-radius: 4px; font-size: 14px; }
            QPushButton:hover { background-color: #2472a4; }
        """)
        export_inv_btn.clicked.connect(self._export_inventory)

        export_daily_btn = QPushButton("导出每日发货明细")
        export_daily_btn.setStyleSheet("""
            QPushButton { background-color: #2980b9; color: white; border: none;
                          padding: 10px 24px; border-radius: 4px; font-size: 14px; }
            QPushButton:hover { background-color: #2472a4; }
        """)
        export_daily_btn.clicked.connect(self._export_daily_shipment)

        export_order_btn = QPushButton("导出订单装车汇总")
        export_order_btn.setStyleSheet("""
            QPushButton { background-color: #2980b9; color: white; border: none;
                          padding: 10px 24px; border-radius: 4px; font-size: 14px; }
            QPushButton:hover { background-color: #2472a4; }
        """)
        export_order_btn.clicked.connect(self._export_order_summary)

        backup_btn = QPushButton("备份数据库")
        backup_btn.setStyleSheet("""
            QPushButton { background-color: #8e44ad; color: white; border: none;
                          padding: 10px 24px; border-radius: 4px; font-size: 14px; }
            QPushButton:hover { background-color: #7d3c98; }
        """)
        backup_btn.clicked.connect(self._backup_db)

        btn_row = QHBoxLayout()
        btn_row.addWidget(export_inv_btn)
        btn_row.addWidget(export_daily_btn)
        btn_row.addWidget(export_order_btn)
        btn_row.addWidget(backup_btn)
        btn_row.addStretch()

        export_layout.addWidget(export_label)
        export_layout.addLayout(btn_row)
        self.main_layout.insertLayout(3, export_layout)
        self.table.hide()

    def _import_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 Excel 文件", "", "Excel Files (*.xlsx *.xls)")
        if not path:
            return
        import_type = self.import_type_combo.currentData()
        type_name = "销售订单" if import_type == "sales_order" else "日发货流水"

        dlg = ExcelPreviewDialog(path, type_name, self)
        if not dlg.exec():
            return

        selected = dlg.get_selected_rows()
        if not selected:
            self.result_label.setText("未选择任何数据行")
            return

        try:
            if import_type == "sales_order":
                result = self.excel_svc.import_sales_orders_from_rows(selected)
                self.result_label.setText(
                    f"导入完成: 新增订单 {result['imported_orders']} 条, "
                    f"新增客户 {result['new_customers']} 个, "
                    f"新增规格 {result['new_specs']} 个, "
                    f"跳过 {result['skipped']} 条")
            else:
                result = self.excel_svc.import_daily_shipments_from_rows(selected)
                self.result_label.setText(
                    f"导入完成: {result['imported']} 条, 跳过 {result['skipped']} 条")
        except Exception as e:
            self.show_error(f"导入失败: {e}")

    def _export_inventory(self):
        export = ExportService(self.db)
        from pathlib import Path
        path = str(Path.home() / "Desktop" / "成品库存.xlsx")
        export.export_inventory(path)
        self.show_info(f"已导出到: {path}")

    def _export_daily_shipment(self):
        export = ExportService(self.db)
        from pathlib import Path
        path = str(Path.home() / "Desktop" / "每日发货明细.xlsx")
        export.export_daily_shipments(path)
        self.show_info(f"已导出到: {path}")

    def _export_order_summary(self):
        export = ExportService(self.db)
        from pathlib import Path
        path = str(Path.home() / "Desktop" / "订单装车汇总.xlsx")
        export.export_order_summary(path)
        self.show_info(f"已导出到: {path}")

    def _backup_db(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "备份数据库", "", "SQLite Database (*.db)")
        if not path:
            return
        try:
            self.db.backup(path)
            self.show_info(f"数据库已备份到: {path}")
        except Exception as e:
            self.show_error(f"备份失败: {e}")

    def refresh(self):
        pass
