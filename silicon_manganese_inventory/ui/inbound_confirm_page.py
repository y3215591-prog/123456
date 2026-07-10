from PySide6.QtWidgets import QLineEdit, QComboBox
from silicon_manganese_inventory.ui.base_page import BasePage
from silicon_manganese_inventory.services.inbound_service import InboundService
from silicon_manganese_inventory.dao.lab_dao import LabDAO
from silicon_manganese_inventory.dao.inbound_dao import InboundDAO
from silicon_manganese_inventory.dao.base_dao import LocationDAO


class InboundConfirmPage(BasePage):
    def __init__(self, db):
        super().__init__(db, "入库确认")
        self.inbound_svc = InboundService(db)

        self.order_input = QLineEdit()
        self.order_input.setPlaceholderText("预入库单号")
        self.batch_input = QLineEdit()
        self.batch_input.setPlaceholderText("批次号")
        self.add_search_field("单号:", self.order_input)
        self.add_search_field("批次:", self.batch_input)

        self.target_location_combo = QComboBox()
        self.target_location_combo.setEditable(True)
        loc_dao = LocationDAO(db)
        for loc in loc_dao.list():
            if not loc["code"].startswith("Z"):
                self.target_location_combo.addItem(
                    f"{loc['code']} ({loc['name']})", loc["code"])
        jul_idx = self.target_location_combo.findData("A01-7月")
        if jul_idx >= 0:
            self.target_location_combo.setCurrentIndex(jul_idx)

        self.add_search_field("目标成品库位:", self.target_location_combo)
        self.add_search_button("搜索", self._do_search)
        self.add_header_button("确认入库", self._confirm, "#27ae60")

        self.set_table_headers([
            "预入库单号", "日期", "批次号", "数量(吨)", "自然块库位",
            "化验结果", "铅封号范围", "化验明细",
        ])

    def _do_search(self):
        self.refresh()

    def refresh(self):
        kwargs = {"lab_status": "tested", "inbound_status": "unconfirmed"}
        if self.order_input.text():
            kwargs["keyword"] = self.order_input.text()
        if self.batch_input.text():
            kwargs["batch_no"] = self.batch_input.text()
        rows = self.inbound_svc.list_pre_inbound(**kwargs)
        data = []
        lab_dao = LabDAO(self.db)
        for r in rows:
            seal_range = f"{r['seal_start']}~{r['seal_end']}" if r["seal_start"] else ""
            lab = lab_dao.get_result(r["id"])
            lab_detail = ""
            if lab:
                lab_detail = (
                    f"Mn:{lab['mn_content']} Si:{lab['si_content']} P:{lab['p_content']} "
                    f"S:{lab['s_content']} C:{lab['c_content']} -> {lab['overall_result']}"
                )
            data.append([
                r["order_no"], r["date"], r["batch_no"], r["quantity"],
                r["location_code"], "已化验", seal_range, lab_detail,
            ])
        self.populate_table(data)

    def _confirm(self):
        row = self.table.currentRow()
        if row < 0:
            self.show_error("请先选择一条已化验的预入库记录")
            return
        order_no = self.table.item(row, 0).text()
        dao = InboundDAO(self.db)
        record = dao.get_pre_inbound_by_order_no(order_no)
        if not record:
            return
        if record["lab_status"] != "tested":
            self.show_error("请先录入化验结果")
            return
        target = self.target_location_combo.currentData()
        if not target:
            target = self.target_location_combo.currentText().strip()
        if not target:
            self.show_error("请选择或输入目标成品库位")
            return
        loc_dao = LocationDAO(self.db)
        target = loc_dao.get_or_create(target)
        try:
            self.inbound_svc.confirm_inbound(record["id"], target_location=target)
        except ValueError as e:
            self.show_error(str(e))
            return
        self.show_info(f"入库确认成功，铅封号已移至 {target}")
        self.refresh()
