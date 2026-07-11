from PySide6.QtWidgets import QLineEdit, QFileDialog, QMessageBox, QDateEdit, QLabel
from PySide6.QtCore import QDate
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

        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate())
        self.date_from.setDisplayFormat("yyyy-MM-dd")
        self.date_from.setStyleSheet("""
            QDateEdit { border: 1px solid #D1D5DB; border-radius: 3px; padding: 4px 8px;
                        font-size: 13px; background: #FFFFFF; min-height: 26px; }
        """)
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setDisplayFormat("yyyy-MM-dd")
        self.date_to.setStyleSheet("""
            QDateEdit { border: 1px solid #D1D5DB; border-radius: 3px; padding: 4px 8px;
                        font-size: 13px; background: #FFFFFF; min-height: 26px; }
        """)
        self.order_input = QLineEdit()
        self.order_input.setPlaceholderText("销售订单号")
        self.plate_input = QLineEdit()
        self.plate_input.setPlaceholderText("车牌号")
        self.add_search_field("日期:", self.date_from)
        self.add_search_field("-", self.date_to)
        self.add_search_field("订单号:", self.order_input)
        self.add_search_field("车牌:", self.plate_input)
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

        self.total_label = QLabel("")
        self.total_label.setStyleSheet(
            "font-size: 13px; font-weight: bold; color: #2B579A; padding: 4px 8px; "
            "border: none; background: transparent;")
        self.status_layout.addWidget(self.total_label)

    def _do_search(self):
        self.refresh()

    def refresh(self):
        kwargs = {}
        if self.date_from.date().isValid():
            kwargs["date_from"] = self.date_from.date().toString("yyyy-MM-dd")
        if self.date_to.date().isValid():
            kwargs["date_to"] = self.date_to.date().toString("yyyy-MM-dd")
        if self.order_input.text():
            kwargs["sales_order_no"] = self.order_input.text()
        if self.plate_input.text():
            kwargs["plate_no"] = self.plate_input.text()
        rows = self.report_svc.get_daily_shipment_report(**kwargs)
        data = []
        totals = {"load": 0.0, "gross": 0.0, "tare": 0.0, "net": 0.0, "received": 0.0}
        for r in rows:
            load_qty = float(r["load_quantity"] or 0)
            gross = float(r["gross_weight"] or 0)
            tare = float(r["tare_weight"] or 0)
            net = float(r["net_weight"] or 0)
            received = float(r["customer_received_weight"] or 0)
            totals["load"] += load_qty
            totals["gross"] += gross
            totals["tare"] += tare
            totals["net"] += net
            totals["received"] += received
            data.append([
                r["id"] or "", r["seq_no"] or "", r["shipment_date"] or "",
                r["plate_no"] or "", r["customer_code"] or "",
                r["customer_name"] or "", r["sales_order_no"] or "",
                r["material_name"] or "", r["spec"] or "",
                r["batch_no"] or "", load_qty,
                gross, tare, net, received,
                r["seal_codes"] or "", r["remark"] or "",
            ])
        self.populate_table(data)
        self.total_label.setText(
            f"共 {len(rows)} 条 | 装车: {totals['load']:.2f}吨 | "
            f"毛重: {totals['gross']:.2f} | 皮重: {totals['tare']:.2f} | "
            f"净重: {totals['net']:.2f} | 收货净重: {totals['received']:.2f}")

    def _add(self):
        dlg = DailyShipmentDialog(self.db, self)
        if dlg.exec():
            self.refresh()

    def _edit(self):
        row = self.table.currentRow()
        if row < 0:
            self.show_error("请先选择一条记录")
            return
        item = self.table.item(row, 0)
        if not item:
            self.show_error("无效的记录")
            return
        record_id = item.text()
        record = self.shipment_dao.get(int(record_id))
        if not record:
            self.show_error("未找到记录")
            return
        dlg = DailyShipmentDialog(self.db, self, edit_record=record)
        if dlg.exec():
            self.refresh()

    def _export(self):
        try:
            kwargs = {}
            if self.date_from.date().isValid():
                kwargs["date_from"] = self.date_from.date().toString("yyyy-MM-dd")
            if self.date_to.date().isValid():
                kwargs["date_to"] = self.date_to.date().toString("yyyy-MM-dd")
            if self.order_input.text():
                kwargs["sales_order_no"] = self.order_input.text()
            if self.plate_input.text():
                kwargs["plate_no"] = self.plate_input.text()
            include_seals = QMessageBox.question(
                self, "导出选项", "是否在导出中包含铅封号列?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes,
            ) == QMessageBox.Yes
            export = ExportService(self.db)
            from pathlib import Path
            path = str(Path.home() / "Desktop" / "导出每日发货明细.xlsx")
            export.export_daily_shipments(path, include_seals=include_seals, **kwargs)
            self.show_info(f"已导出到: {path}")
        except Exception as e:
            self.show_error(f"导出失败: {e}")

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
