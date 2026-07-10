from PySide6.QtWidgets import QComboBox, QLabel
from silicon_manganese_inventory.ui.base_page import BasePage
from silicon_manganese_inventory.services.report_service import ReportService
from silicon_manganese_inventory.services.excel_service import ExportService
from silicon_manganese_inventory.dao.base_dao import LocationDAO


class InventoryPage(BasePage):
    def __init__(self, db):
        super().__init__(db, "成品库存")
        self.report_svc = ReportService(db)

        self.location_combo = QComboBox()
        self.location_combo.addItem("全部", None)
        loc_dao = LocationDAO(db)
        for l in loc_dao.list():
            self.location_combo.addItem(l["code"], l["code"])
        self.add_search_field("库位:", self.location_combo)
        self.add_search_button("搜索", self._do_search)
        self.add_header_button("导出 Excel", self._export, "#2980b9")

        self.total_label = QLabel("库存总计: 0 吨")
        self.total_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50;")
        self.status_layout.addWidget(self.total_label)

        self.set_table_headers([
            "批次号", "库位", "结存(吨)", "最近入库日期", "化验结果", "铅封号明细",
        ])

    def _do_search(self):
        self.refresh()

    def refresh(self):
        location = self.location_combo.currentData()
        rows = self.report_svc.get_inventory_report(location_code=location)
        total = sum(r["balance"] or 0 for r in rows)
        self.total_label.setText(f"库存总计: {total} 吨")
        data = []
        for r in rows:
            data.append([
                r["batch_no"], r["location_code"] or "", r["balance"],
                r["last_inbound_date"], r["overall_result"] or "", r["seal_list"] or "",
            ])
        self.populate_table(data, highlight_col=2, highlight_threshold=100)

    def _export(self):
        export = ExportService(self.db)
        from pathlib import Path
        path = str(Path.home() / "Desktop" / "成品库存.xlsx")
        export.export_inventory(path)
        self.show_info(f"已导出到: {path}")
