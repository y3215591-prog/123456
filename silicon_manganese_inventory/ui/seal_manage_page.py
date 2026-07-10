from PySide6.QtWidgets import QLineEdit, QComboBox, QLabel, QMessageBox, QPushButton
from silicon_manganese_inventory.ui.base_page import BasePage
from silicon_manganese_inventory.ui.dialogs.seal_import_dialog import SealImportDialog
from silicon_manganese_inventory.ui.dialogs.seal_trace_dialog import SealTraceDialog
from silicon_manganese_inventory.dao.seal_dao import SealDAO


class SealManagePage(BasePage):
    def __init__(self, db):
        super().__init__(db, "铅封号管理")
        self.seal_dao = SealDAO(db)

        self.status_combo = QComboBox()
        self.status_combo.addItem("全部", None)
        self.status_combo.addItem("未使用", "unused")
        self.status_combo.addItem("已预分配", "pre_allocated")
        self.status_combo.addItem("已入库", "in_stock")
        self.status_combo.addItem("已出库", "shipped")
        self.add_search_field("状态:", self.status_combo)
        self.add_search_button("搜索", self._do_search)
        self.add_header_button("+ 导入号段", self._import_batch, "#27ae60")
        self.add_header_button("追溯查询", self._trace, "#3498db")

        self.batch_combo = QComboBox()
        self.batch_combo.addItem("全部号段", None)
        self.batch_combo.currentIndexChanged.connect(self._on_batch_changed)
        self.search_layout.addWidget(QLabel("号段:"))
        self.search_layout.addWidget(self.batch_combo)

        self.total_label = QLabel("")
        self.total_label.setStyleSheet("font-size: 13px; color: #7f8c8d;")
        self.status_layout.addWidget(self.total_label)

        self.set_table_headers([
            "铅封号", "号段批次", "状态", "预入库单号", "入库单号",
            "出库单号", "创建时间",
        ])

    def _on_batch_changed(self):
        self._do_search()

    def _do_search(self):
        self.refresh()

    def refresh(self):
        status = self.status_combo.currentData()
        batch_id = self.batch_combo.currentData()

        batches = self.seal_dao.list_batches()
        current_bid = self.batch_combo.currentData()
        self.batch_combo.blockSignals(True)
        self.batch_combo.clear()
        self.batch_combo.addItem("全部号段", None)
        for b in batches:
            available = b["total_count"] - (b["used_count"] or 0)
            self.batch_combo.addItem(
                f"{b['start_code']}~{b['end_code']} (剩余{available})", b["id"])
        idx = self.batch_combo.findData(current_bid)
        if idx >= 0:
            self.batch_combo.setCurrentIndex(idx)
        self.batch_combo.blockSignals(False)

        if batch_id:
            seals = self.seal_dao.get_seals_by_batch(batch_id, status=status)
        else:
            seals = self.seal_dao.list_all(status=status)

        status_map = {
            "unused": "未使用",
            "pre_allocated": "已预分配",
            "in_stock": "已入库",
            "shipped": "已出库",
        }
        data = []
        for s in seals:
            data.append([
                s["seal_code"], s.get("batch_code", ""),
                status_map.get(s["status"], s["status"]),
                s.get("pre_inbound_order", "") or "",
                s.get("inbound_order", "") or "",
                s.get("outbound_order", "") or "",
                s.get("created_at", "") or "",
            ])
        self.populate_table(data)
        self.total_label.setText(f"共 {len(seals)} 条记录")

    def _import_batch(self):
        dlg = SealImportDialog(self.db, self)
        if dlg.exec():
            self.refresh()

    def _trace(self):
        dlg = SealTraceDialog(self.db, self)
        dlg.exec()
