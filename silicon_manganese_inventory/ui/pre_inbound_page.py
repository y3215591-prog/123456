from PySide6.QtWidgets import QLineEdit
from datetime import datetime
from silicon_manganese_inventory.ui.base_page import BasePage
from silicon_manganese_inventory.ui.dialogs.pre_inbound_dialog import PreInboundDialog
from silicon_manganese_inventory.ui.dialogs.lab_result_dialog import LabResultDialog
from silicon_manganese_inventory.services.inbound_service import InboundService
from silicon_manganese_inventory.services.lab_service import LabService


class PreInboundPage(BasePage):
    def __init__(self, db):
        super().__init__(db, "预入库管理")
        self.inbound_svc = InboundService(db)
        self.lab_svc = LabService(db)

        self.date_from = QLineEdit()
        self.date_from.setPlaceholderText("开始日期")
        self.date_to = QLineEdit()
        self.date_to.setPlaceholderText("结束日期")
        self.batch_input = QLineEdit()
        self.batch_input.setPlaceholderText("批次号")
        self.add_search_field("日期:", self.date_from)
        self.add_search_field("-", self.date_to)
        self.add_search_field("批次:", self.batch_input)
        self.add_search_button("搜索", self._do_search)

        self.add_header_button("+ 新增预入库", self._add_pre_inbound, "#27ae60")
        self._add_edit_btn = self._add_header_btn("编辑", self._edit_selected, "#3498db")
        self._add_del_btn = self._add_header_btn("作废", self._cancel_selected, "#e74c3c")
        self._add_lab_btn = self._add_header_btn("录入化验", self._add_lab_result, "#f39c12")

        self.set_table_headers([
            "预入库单号", "日期", "批次号", "数量(吨)", "库位",
            "铅封号范围", "化验状态", "操作人", "备注",
        ])

    def _add_header_btn(self, text, callback, color):
        self.add_header_button(text, callback, color)
        return self.header_buttons.itemAt(self.header_buttons.count() - 1).widget()

    def _do_search(self):
        self.refresh()

    def refresh(self):
        kwargs = {}
        if self.date_from.text():
            kwargs["date_from"] = self.date_from.text()
        if self.date_to.text():
            kwargs["date_to"] = self.date_to.text()
        if self.batch_input.text():
            kwargs["batch_no"] = self.batch_input.text()
        rows = self.inbound_svc.list_pre_inbound(**kwargs)
        data = []
        for r in rows:
            seal_range = f"{r['seal_start']}~{r['seal_end']}" if r["seal_start"] else ""
            data.append([
                r["order_no"], r["date"], r["batch_no"], r["quantity"],
                r["location_code"], seal_range,
                "已化验" if r["lab_status"] == "tested" else "待化验",
                r["operator"], r["remark"] or "",
            ])
        self.populate_table(data)

    def _add_pre_inbound(self):
        dlg = PreInboundDialog(self.db, self)
        if dlg.exec():
            self.refresh()

    def _edit_selected(self):
        row = self.table.currentRow()
        if row < 0:
            self.show_error("请先选择一条记录")
            return
        order_no = self.table.item(row, 0).text()
        from silicon_manganese_inventory.dao.inbound_dao import InboundDAO
        dao = InboundDAO(self.db)
        records = dao.list_pre_inbound()
        record = next((r for r in records if r["order_no"] == order_no), None)
        if not record:
            return
        if record["lab_status"] == "tested":
            self.show_error("已化验的预入库单不能编辑")
            return
        dlg = PreInboundDialog(self.db, self, edit_record=record)
        if dlg.exec():
            self.refresh()

    def _cancel_selected(self):
        row = self.table.currentRow()
        if row < 0:
            self.show_error("请先选择一条记录")
            return
        order_no = self.table.item(row, 0).text()
        from silicon_manganese_inventory.dao.inbound_dao import InboundDAO
        dao = InboundDAO(self.db)
        records = dao.list_pre_inbound()
        record = next((r for r in records if r["order_no"] == order_no), None)
        if not record:
            return
        try:
            self.inbound_svc.cancel_pre_inbound(record["id"])
        except ValueError as e:
            self.show_error(str(e))
            return
        self.show_info("预入库单已作废")
        self.refresh()

    def _add_lab_result(self):
        row = self.table.currentRow()
        if row < 0:
            self.show_error("请先选择一条记录")
            return
        order_no = self.table.item(row, 0).text()
        from silicon_manganese_inventory.dao.inbound_dao import InboundDAO
        dao = InboundDAO(self.db)
        records = dao.list_pre_inbound()
        record = next((r for r in records if r["order_no"] == order_no), None)
        if not record:
            return
        dlg = LabResultDialog(self.db, record["id"], self)
        if dlg.exec():
            self.refresh()
