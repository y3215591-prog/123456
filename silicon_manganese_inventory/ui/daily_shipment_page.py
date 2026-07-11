from PySide6.QtWidgets import QLineEdit, QFileDialog, QMessageBox
from silicon_manganese_inventory.ui.base_page import BasePage
from silicon_manganese_inventory.ui.dialogs.daily_shipment_dialog import DailyShipmentDialog
from silicon_manganese_inventory.services.report_service import ReportService
from silicon_manganese_inventory.services.excel_service import ExportService, ExcelService
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
        self.add_header_button("导入 MES Excel", self._import_mes, "#8e44ad")
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
                r["id"] or "", r["seq_no"] or "", r["shipment_date"] or "",
                r["plate_no"] or "", r["customer_code"] or "",
                r["customer_name"] or "", r["sales_order_no"] or "",
                r["material_name"] or "", r["spec"] or "",
                r["batch_no"] or "", r["load_quantity"] or "",
                r["gross_weight"] or "", r["tare_weight"] or "",
                r["net_weight"] or "", r["customer_received_weight"] or "",
                r["seal_codes"] or "", r["remark"] or "",
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
        include_seals = QMessageBox.question(
            self, "导出选项", "是否在导出中包含铅封号列?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes,
        ) == QMessageBox.Yes
        export = ExportService(self.db)
        from pathlib import Path
        path = str(Path.home() / "Desktop" / "每日发货明细.xlsx")
        export.export_daily_shipments(path, include_seals=include_seals, **kwargs)
        self.show_info(f"已导出到: {path}")

    def _import_mes(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择 MES 导出发货明细", "", "Excel 文件 (*.xlsx *.xls)")
        if not file_path:
            return
        try:
            svc = ExcelService(self.db)
            stats = svc.import_mes_shipments(file_path)
            msg = (f"导入完成:\n"
                   f"  发货记录: {stats.get('imported', 0)} 条\n"
                   f"  跳过: {stats.get('skipped', 0)} 条\n"
                   f"  重复: {stats.get('duplicate', 0)} 条\n"
                   f"  出库单: {stats.get('outbound_created', 0)} 个\n"
                   f"  发货铅封: {stats.get('seal_shipped', 0)} 个")
            QMessageBox.information(self, "导入结果", msg)
        except Exception as e:
            self.show_error(f"导入失败: {e}")
        self.refresh()
