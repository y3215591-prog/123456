from PySide6.QtWidgets import QComboBox, QLabel, QPushButton, QHBoxLayout
from silicon_manganese_inventory.ui.base_page import BasePage
from silicon_manganese_inventory.ui.dialogs.seal_import_dialog import SealImportDialog
from silicon_manganese_inventory.ui.dialogs.seal_trace_dialog import SealTraceDialog
from silicon_manganese_inventory.dao.seal_dao import SealDAO


PAGE_SIZE = 200


class SealManagePage(BasePage):
    def __init__(self, db):
        super().__init__(db, "铅封号管理")
        self.seal_dao = SealDAO(db)
        self._current_page = 0
        self._total_records = 0

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

        page_nav = QHBoxLayout()
        page_nav.setSpacing(6)
        self.prev_btn = QPushButton("< 上一页")
        self.next_btn = QPushButton("下一页 >")
        self.page_label = QLabel("第 1 页")
        for btn in [self.prev_btn, self.next_btn]:
            btn.setStyleSheet("""
                QPushButton { padding: 4px 12px; font-size: 12px;
                    border: 1px solid rgba(0,0,0,0.1); border-radius: 4px; }
                QPushButton:hover { background: rgba(0,0,0,0.05); }
                QPushButton:disabled { color: #ccc; }
            """)
        self.prev_btn.clicked.connect(self._prev_page)
        self.next_btn.clicked.connect(self._next_page)
        page_nav.addWidget(self.prev_btn)
        page_nav.addWidget(self.page_label)
        page_nav.addWidget(self.next_btn)
        page_nav.addStretch()

        self.total_label = QLabel("")
        self.total_label.setStyleSheet("font-size: 13px; color: #7f8c8d;")
        page_nav.addWidget(self.total_label)
        self.status_layout.addLayout(page_nav)

        self.set_table_headers([
            "铅封号", "号段批次", "状态", "预入库单号", "入库单号",
            "出库单号", "创建时间",
        ])

    def _on_batch_changed(self):
        self._current_page = 0
        self._do_search()

    def _do_search(self):
        self._current_page = 0
        self.refresh()

    def _prev_page(self):
        if self._current_page > 0:
            self._current_page -= 1
            self.refresh()

    def _next_page(self):
        max_page = (self._total_records - 1) // PAGE_SIZE
        if self._current_page < max_page:
            self._current_page += 1
            self.refresh()

    def refresh(self):
        try:
            self._do_refresh()
        except Exception as e:
            self.show_error(f"加载铅封数据失败: {e}")

    def _do_refresh(self):
        status = self.status_combo.currentData()

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

        batch_id = self.batch_combo.currentData()

        offset = self._current_page * PAGE_SIZE
        if batch_id:
            seals, total = self.seal_dao.get_seals_by_batch(batch_id, status=status, offset=offset, limit=PAGE_SIZE)
        else:
            seals, total = self.seal_dao.list_all(status=status, offset=offset, limit=PAGE_SIZE)

        self._total_records = total
        self._update_pagination()

        status_map = {
            "unused": "未使用",
            "pre_allocated": "已预分配",
            "in_stock": "已入库",
            "shipped": "已出库",
        }
        data = []
        for s in seals:
            data.append([
                s["seal_code"], s["batch_code"] or "",
                status_map.get(s["status"], s["status"]),
                s["pre_inbound_order"] or "",
                s["inbound_order"] or "",
                s["outbound_order"] or "",
                s["created_at"] or "",
            ])
        self.populate_table(data)

    def _update_pagination(self):
        total_pages = max(1, (self._total_records - 1) // PAGE_SIZE + 1)
        self.page_label.setText(f"第 {self._current_page + 1}/{total_pages} 页")
        self.total_label.setText(f"共 {self._total_records} 条")
        self.prev_btn.setEnabled(self._current_page > 0)
        self.next_btn.setEnabled(self._current_page < total_pages - 1)

    def _import_batch(self):
        dlg = SealImportDialog(self.db, self)
        if dlg.exec():
            self.refresh()

    def _trace(self):
        dlg = SealTraceDialog(self.db, self)
        dlg.exec()
