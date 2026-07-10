from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QLabel, QMessageBox,
)
from silicon_manganese_inventory.dao.seal_dao import SealDAO


class SealTraceDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.seal_dao = SealDAO(db)
        self.setWindowTitle("铅封号追溯查询")
        self.setMinimumWidth(550)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        search_layout = QVBoxLayout()
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("输入铅封号（纯数字）查询完整生命周期")
        search_btn = QPushButton("查询追溯")
        search_btn.setStyleSheet("background-color: #3498db; color: white; padding: 8px 16px;")
        search_btn.clicked.connect(self._search)
        search_layout.addWidget(QLabel("铅封号:"))
        search_layout.addWidget(self.code_input)
        search_layout.addWidget(search_btn)
        layout.addLayout(search_layout)

        self.result_form = QFormLayout()
        self._labels = {}
        for key, label in [
            ("seal_code", "铅封号"),
            ("batch_name", "号段批次"),
            ("status", "当前状态"),
            ("pre_inbound_no", "预入库单号"),
            ("pre_inbound_date", "预入库日期"),
            ("pre_inbound_batch", "预入库批次"),
            ("inbound_no", "入库单号"),
            ("inbound_date", "入库日期"),
            ("outbound_no", "出库单号"),
            ("outbound_date", "出库日期"),
            ("sales_order_no", "销售订单号"),
            ("customer_name", "客户名称"),
        ]:
            lbl = QLabel("")
            lbl.setStyleSheet("font-size: 13px;")
            self.result_form.addRow(f"{label}:", lbl)
            self._labels[key] = lbl

        layout.addLayout(self.result_form)

        self.flow_label = QLabel("")
        self.flow_label.setStyleSheet("font-size: 14px; color: #2c3e50; font-weight: bold; padding: 12px;")
        layout.addWidget(self.flow_label)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.reject)
        layout.addWidget(close_btn)

        self.code_input.returnPressed.connect(self._search)

    def _search(self):
        code = self.code_input.text().strip()
        if not code:
            QMessageBox.warning(self, "错误", "请输入铅封号")
            return
        row = self.seal_dao.trace_seal(code)
        if not row:
            for lbl in self._labels.values():
                lbl.setText("")
            self.flow_label.setText("未找到该铅封号")
            return

        status_map = {
            "unused": "未使用",
            "pre_allocated": "已预分配",
            "in_stock": "已入库（在库）",
            "shipped": "已出库",
        }

        status = row.get("status", "")
        flow_parts = []
        if row.get("pre_inbound_date"):
            flow_parts.append(f"预入库 ({row['pre_inbound_date']})")
        if row.get("inbound_date"):
            flow_parts.append(f"入库确认 ({row['inbound_date']})")
        if row.get("outbound_date"):
            flow_parts.append(f"出库发货 ({row['outbound_date']}) -> {row.get('customer_name', '')}")

        if flow_parts:
            self.flow_label.setText(f"生命周期: {' → '.join(flow_parts)}")
        else:
            self.flow_label.setText(f"当前状态: {status_map.get(status, status)}")

        row_dict = dict(row)
        for key, lbl in self._labels.items():
            val = row_dict.get(key, "")
            if key == "status":
                val = status_map.get(str(val), str(val))
            lbl.setText(str(val) if val else "-")
