from PySide6.QtWidgets import (
    QComboBox, QLabel, QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox,
)
from PySide6.QtCore import Qt
from silicon_manganese_inventory.ui.base_page import BasePage
from silicon_manganese_inventory.services.report_service import ReportService
from silicon_manganese_inventory.services.excel_service import ExportService, ExcelService
from silicon_manganese_inventory.dao.base_dao import LocationDAO
from silicon_manganese_inventory.ui.dialogs.location_detail_dialog import (
    LocationDetailDialog,
)
from silicon_manganese_inventory.ui.dialogs.seal_list_dialog import SealListDialog
from silicon_manganese_inventory.utils.preferences import UIPreferences


class InventoryPage(BasePage):
    LOCATION_COL = 1
    SEAL_COL = 5

    def __init__(self, db):
        super().__init__(db, "成品库存")
        self.report_svc = ReportService(db)
        self.excel_svc = ExcelService(db)
        self._prefs = UIPreferences()

        self.location_combo = QComboBox()
        self.location_combo.addItem("全部", None)
        loc_dao = LocationDAO(db)
        for l in loc_dao.list():
            self.location_combo.addItem(l["code"], l["code"])
        self.add_search_field("库位:", self.location_combo)
        self.add_search_button("搜索", self._do_search)
        self.add_header_button("上传盘点数据", self._import_balance, "#8B5CF6")
        self.add_header_button("导出 Excel", self._export, "#2980b9")

        self.total_label = QLabel("库存总计: 0 吨")
        self.total_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50;")
        self.status_layout.addWidget(self.total_label)

        self.set_table_headers([
            "批次号", "库位", "结存(吨)", "最近入库日期", "化验结果", "铅封号明细",
        ])
        self.table.cellClicked.connect(self._on_cell_clicked)
        self._seal_data = {}

    def _do_search(self):
        self.refresh()

    def refresh(self):
        location = self.location_combo.currentData()
        rows = self.report_svc.get_inventory_report(location_code=location)
        total = sum(r["balance"] or 0 for r in rows)
        self.total_label.setText(f"库存总计: {total} 吨")
        self._seal_data = {}
        data = []
        for r_idx, r in enumerate(rows):
            location_code = r["location_code"] or ""
            seal_list = r.get("seal_list", "") or ""
            seal_min = r.get("seal_min", "")
            seal_max = r.get("seal_max", "")
            balance = r["balance"]
            if seal_list:
                self._seal_data[r_idx] = seal_list
                display = f"{seal_min}~{seal_max} ({balance}个)"
            else:
                display = ""
            data.append([
                r["batch_no"], location_code, balance,
                r["last_inbound_date"], r["overall_result"] or "", display,
            ])
        self.populate_table(data, highlight_col=2, highlight_threshold=100)

    def _import_balance(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择盘点Excel文件", "",
            "Excel 文件 (*.xlsx *.xls);;所有文件 (*)")
        if not path:
            return

        try:
            result = self.excel_svc.import_inventory_balance(path)
        except Exception as e:
            QMessageBox.warning(self, "导入失败", f"无法解析Excel文件:\n{str(e)}")
            return

        if not result["items"]:
            QMessageBox.information(self, "提示", "未发现结余>0的批次数据")
            return

        from silicon_manganese_inventory.ui.dialogs.inventory_balance_dialog import (
            InventoryBalanceDialog,
        )
        dlg = InventoryBalanceDialog(result, self.db, self)
        dlg.exec()

    def populate_table(self, rows, highlight_col=None, highlight_threshold=None):
        super().populate_table(rows, highlight_col, highlight_threshold)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.resizeSections(QHeaderView.ResizeToContents)

        for r in range(len(rows)):
            loc_item = self.table.item(r, self.LOCATION_COL)
            if loc_item and loc_item.text():
                loc_item.setForeground(Qt.blue)
                loc_item.setToolTip("点击查看库位详情")
                font = loc_item.font()
                font.setUnderline(True)
                loc_item.setFont(font)

            seal_item = self.table.item(r, self.SEAL_COL)
            if seal_item and seal_item.text():
                seal_item.setForeground(Qt.blue)
                seal_item.setToolTip("点击查看完整铅封号列表")
                font = seal_item.font()
                font.setUnderline(True)
                seal_item.setFont(font)

    def _on_cell_clicked(self, row, col):
        if col == self.LOCATION_COL:
            item = self.table.item(row, col)
            if item and item.text().strip():
                location_code = item.text().strip()
                dlg = LocationDetailDialog(self.db, location_code, self)
                dlg.exec()
        elif col == self.SEAL_COL:
            if row in self._seal_data:
                dlg = SealListDialog(self._seal_data[row], self)
                dlg.exec()

    def _export(self):
        export = ExportService(self.db)
        from pathlib import Path
        path = str(Path.home() / "Desktop" / "成品库存.xlsx")
        export.export_inventory(path)
        self.show_info(f"已导出到: {path}")
