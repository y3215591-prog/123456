from PySide6.QtWidgets import QLineEdit
from silicon_manganese_inventory.ui.base_page import BasePage
from silicon_manganese_inventory.services.report_service import ReportService
from silicon_manganese_inventory.services.excel_service import ExportService


class OrderSummaryPage(BasePage):
    def __init__(self, db):
        super().__init__(db, "订单装车汇总")
        self.report_svc = ReportService(db)

        self.order_input = QLineEdit()
        self.order_input.setPlaceholderText("销售订单号")
        self.add_search_field("订单号:", self.order_input)
        self.add_search_button("搜索", self._do_search)
        self.add_header_button("导出 Excel", self._export, "#2980b9")

        self.set_table_headers([
            "销售订单号", "客户代码", "客户名称", "物料名称", "规格",
            "订单量", "已发量", "待发量", "完成率", "预警",
        ])

    def _do_search(self):
        self.refresh()

    def refresh(self):
        all_rows = self.report_svc.get_order_summary()
        order_filter = self.order_input.text().strip()
        data = []
        for r in all_rows:
            if order_filter and order_filter not in str(r["order_no"]):
                continue
            data.append([
                r["order_no"], r["customer_code"] or "", r["customer_name"] or "",
                r["material_name"] or "", r["spec"] or "", r["order_quantity"],
                r["shipped_quantity"], r["pending_quantity"],
                f"{r['completion_rate'] * 100:.1f}%" if r["completion_rate"] else "0%",
                r["warning"] or "",
            ])
        self.populate_table(data)

    def _export(self):
        export = ExportService(self.db)
        from pathlib import Path
        path = str(Path.home() / "Desktop" / "导出订单装车汇总.xlsx")
        export.export_order_summary(path)
        self.show_info(f"已导出到: {path}")
