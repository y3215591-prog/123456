from PySide6.QtWidgets import QLineEdit
from silicon_manganese_inventory.ui.base_page import BasePage
from silicon_manganese_inventory.ui.dialogs.daily_shipment_dialog import DailyShipmentDialog
from silicon_manganese_inventory.services.report_service import ReportService
from silicon_manganese_inventory.services.excel_service import ExportService
from silicon_manganese_inventory.dao.base_dao import DailyShipmentDAO


class DailyShipmentPage(BasePage):
    def __init__(self, db):
        super().__init__(db, "每日发货明细")
        self.report_svc = ReportService(db)
        self.shipment_dao = DailyShipmentDAO(db)

        self.date_from = QLineEdit()
        self.date_from.setPlaceholderText("开始日期")
        self.date_to = QLineEdit()
        self.date_to.setPlaceholderText("结束日期")
        self.add_search_field("日期:", self.date_from)
        self.add_search_field("-", self.date_to)
        self.add_search_button("搜索", self._do_search)
        self.add_header_button("+ 新增", self._add, "#27ae60")
        self.add_header_button("编辑", self._edit, "#3498db")
        self.add_header_button("导出 Excel", self._export, "#2980b9")

        self.set_table_headers([
            "ID", "序号", "发货日期", "车牌", "客户代码", "客户名称",
            "销售订单号", "物料名称", "规格", "批次号", "装车吨数",
            "毛重", "皮重", "净重", "收货净重", "铅封号", "备注",
        ])
        self.table.setColumnHidden(0, True)

    def _do_search(self):
        self.refresh()

    def refresh(self):
        kwargs = {}
        if self.date_from.text():
            kwargs["date_from"] = self.date_from.text()
        if self.date_to.text():
            kwargs["date_to"] = self.date_to.text()
        rows = self.report_svc.get_daily_shipment_report(**kwargs)
        data = []
        for r in rows:
            data.append([
                r.get("id", ""), r.get("seq_no", ""), r.get("shipment_date", ""),
                r.get("plate_no", ""), r.get("customer_code", ""),
                r.get("customer_name", ""), r.get("sales_order_no", ""),
                r.get("material_name", ""), r.get("spec", ""),
                r.get("batch_no", ""), r.get("load_quantity", ""),
                r.get("gross_weight", ""), r.get("tare_weight", ""),
                r.get("net_weight", ""), r.get("customer_received_weight", ""),
                r.get("seal_codes", ""), r.get("remark", ""),
            ])
        self.populate_table(data)

    def _add(self):
        dlg = DailyShipmentDialog(self.db, self)
        if dlg.exec():
            self.refresh()

    def _edit(self):
        row = self.table.currentRow()
        if row < 0:
            self.show_error("请先选择一条记录")
            return
        record_id = self.table.item(row, 0).text()
        record = self.shipment_dao.get(int(record_id))
        if not record:
            self.show_error("未找到记录")
            return
        dlg = DailyShipmentDialog(self.db, self, edit_record=record)
        if dlg.exec():
            self.refresh()

    def _export(self):
        kwargs = {}
        if self.date_from.text():
            kwargs["date_from"] = self.date_from.text()
        if self.date_to.text():
            kwargs["date_to"] = self.date_to.text()
        export = ExportService(self.db)
        from pathlib import Path
        path = str(Path.home() / "Desktop" / "每日发货明细.xlsx")
        export.export_daily_shipments(path, **kwargs)
        self.show_info(f"已导出到: {path}")
