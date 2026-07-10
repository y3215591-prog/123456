from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QSpinBox, QComboBox, QLabel, QMessageBox, QTextEdit,
)
from PySide6.QtCore import QTimer
from datetime import datetime
from silicon_manganese_inventory.services.outbound_service import OutboundService
from silicon_manganese_inventory.dao.base_dao import CustomerDAO, SpecDAO, LocationDAO, SalesOrderDAO


class OutboundDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("新增出库")
        self.setMinimumWidth(550)
        self._order_timer = QTimer(self)
        self._order_timer.setSingleShot(True)
        self._order_timer.setInterval(300)
        self._order_timer.timeout.connect(self._on_order_changed_debounced)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.date_input = QLineEdit(datetime.now().strftime("%Y-%m-%d"))
        form.addRow("日期:", self.date_input)

        self.batch_input = QLineEdit()
        form.addRow("批次号 *:", self.batch_input)

        self.spec_combo = QComboBox()
        self.spec_combo.setEditable(True)
        spec_dao = SpecDAO(self.db)
        for s in spec_dao.list():
            self.spec_combo.addItem(s["name"], s["id"])
        form.addRow("品名规格:", self.spec_combo)

        self.sales_order_input = QLineEdit()
        self.sales_order_input.setPlaceholderText("输入后自动带出客户/规格信息")
        self.sales_order_input.textChanged.connect(self._on_order_text_changed)
        form.addRow("销售订单号:", self.sales_order_input)

        self.contract_input = QLineEdit()
        form.addRow("合同号:", self.contract_input)

        self.customer_combo = QComboBox()
        self.customer_combo.setEditable(True)
        self.customer_combo.setInsertPolicy(QComboBox.NoInsert)
        cust_dao = CustomerDAO(self.db)
        for c in cust_dao.list():
            self.customer_combo.addItem(c["name"], c["id"])
        form.addRow("客户:", self.customer_combo)

        self.quick_cust_input = QLineEdit()
        self.quick_cust_input.setPlaceholderText("输入新客户名快速新增")
        self.quick_cust_btn = QPushButton("+新增")
        self.quick_cust_btn.clicked.connect(self._quick_add_customer)
        qc_layout = QHBoxLayout()
        qc_layout.addWidget(self.quick_cust_input)
        qc_layout.addWidget(self.quick_cust_btn)
        form.addRow("快速新增:", qc_layout)

        self.plate_input = QLineEdit()
        form.addRow("车牌号:", self.plate_input)

        self.order_remaining_label = QLabel("")
        form.addRow("", self.order_remaining_label)

        self.location_combo = QComboBox()
        loc_dao = LocationDAO(self.db)
        for l in loc_dao.list():
            if l["code"].startswith("Z"):
                continue
            available = loc_dao.get_available_qty(l["code"])
            if available <= 0:
                continue
            self.location_combo.addItem(f"{l['code']}(库存{available}吨)", l["code"])
        self.location_combo.currentIndexChanged.connect(self._on_location_changed)
        form.addRow("出库库位:", self.location_combo)

        self.max_qty_label = QLabel("")
        self.max_qty_label.setStyleSheet("color: #27ae60; font-size: 12px;")
        form.addRow("可用:", self.max_qty_label)

        self.quantity_input = QSpinBox()
        self.quantity_input.setRange(1, 99999)
        self.quantity_input.setValue(1)
        self.quantity_input.valueChanged.connect(self._on_qty_changed)
        form.addRow("数量(吨) *:", self.quantity_input)

        self.seal_preview = QLabel("")
        self.seal_preview.setStyleSheet("color: #3498db; font-weight: bold;")
        form.addRow("铅封号分配:", self.seal_preview)

        self.operator_input = QLineEdit()
        form.addRow("操作人:", self.operator_input)

        self.remark_input = QTextEdit()
        self.remark_input.setMaximumHeight(60)
        form.addRow("备注:", self.remark_input)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        save_btn = QPushButton("保存")
        save_btn.setStyleSheet("background-color: #27ae60; color: white; padding: 8px 24px;")
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self._on_location_changed()
        self._on_qty_changed()

    def _on_order_text_changed(self, text):
        self._order_timer.start()

    def _on_order_changed_debounced(self):
        text = self.sales_order_input.text()
        self._order_remaining_update(text)

    def _order_remaining_update(self, text):
        self.order_remaining_label.setText("")
        if not text.strip():
            return
        order_dao = SalesOrderDAO(self.db)
        order = order_dao.get_by_order_no(text.strip())
        if order:
            if order.get("customer_name"):
                idx = self.customer_combo.findText(order["customer_name"])
                if idx >= 0:
                    self.customer_combo.setCurrentIndex(idx)
            if order.get("material_desc"):
                self.spec_combo.setCurrentText(order["material_desc"])
            if order.get("contract_no") and not self.contract_input.text():
                self.contract_input.setText(order["contract_no"])
            ordered = order.get("quantity") or 0
            shipped = self._get_order_shipped(text.strip())
            remaining = ordered - shipped
            status_text = "已完成" if remaining <= 0 else f"待发 {remaining} 吨"
            self.order_remaining_label.setText(
                f"订购: {ordered}吨 | 已发: {shipped}吨 | {status_text}")
            if remaining <= 0:
                self.order_remaining_label.setStyleSheet(
                    "color: #27ae60; font-size: 13px; font-weight: bold;")
            else:
                self.order_remaining_label.setStyleSheet(
                    "color: #e67e22; font-size: 13px; font-weight: bold;")
        self._on_qty_changed()

    def _get_order_shipped(self, order_no):
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(quantity), 0) FROM outbound_orders WHERE sales_order_no=?",
                (order_no,),
            ).fetchone()
            return row[0] if row else 0

    def _get_order_remaining_qty(self, order_no):
        order_dao = SalesOrderDAO(self.db)
        order = order_dao.get_by_order_no(order_no)
        if not order:
            return None
        ordered = order.get("quantity") or 0
        shipped = self._get_order_shipped(order_no)
        return ordered - shipped

    def _on_location_changed(self):
        code = self.location_combo.currentData()
        if code:
            loc_dao = LocationDAO(self.db)
            available = loc_dao.get_available_qty(code)
            self.max_qty_label.setText(f"可用库存: {available} 吨")
            self.quantity_input.setMaximum(max(1, int(available)))

    def _on_qty_changed(self):
        qty = self.quantity_input.value()
        msg = f"将自动分配 {qty} 个铅封号"
        sales_order = self.sales_order_input.text().strip()
        if sales_order:
            remaining = self._get_order_remaining_qty(sales_order)
            if remaining is not None and qty > remaining:
                msg += f"  [超发预警: 订单仅余 {remaining} 吨]"
                self.quantity_input.setStyleSheet(
                    "QSpinBox { color: #e74c3c; font-weight: bold; }")
                self.seal_preview.setStyleSheet("color: #e74c3c;")
            else:
                self.quantity_input.setStyleSheet("")
                self.seal_preview.setStyleSheet("")
        else:
            self.quantity_input.setStyleSheet("")
            self.seal_preview.setStyleSheet("")
        self.seal_preview.setText(msg)

    def _quick_add_customer(self):
        name = self.quick_cust_input.text().strip()
        if not name:
            return
        cust_dao = CustomerDAO(self.db)
        cust_dao.create(name=name)
        self.customer_combo.addItem(name)
        self.customer_combo.setCurrentText(name)
        self.quick_cust_input.clear()
        QMessageBox.information(self, "提示", f"客户 '{name}' 已新增")

    def _save(self):
        date = self.date_input.text()
        batch_no = self.batch_input.text().strip()
        quantity = self.quantity_input.value()
        if not date or not batch_no or quantity <= 0:
            QMessageBox.warning(self, "错误", "日期、批次号和数量为必填项")
            return
        location = self.location_combo.currentData()
        if not location:
            location = self.location_combo.currentText().strip()
        if location:
            loc_dao = LocationDAO(self.db)
            location = loc_dao.get_or_create(location)
        spec_id = self.spec_combo.currentData()
        if isinstance(spec_id, str):
            spec_id = None
        cust_id = self.customer_combo.currentData()
        if isinstance(cust_id, str):
            cust_id = None
        if not cust_id:
            cust_name = self.customer_combo.currentText().strip()
            if cust_name:
                cust_dao = CustomerDAO(self.db)
                cust_id = cust_dao.create(name=cust_name)
                self.customer_combo.setItemData(self.customer_combo.currentIndex(), cust_id)
        if not cust_id:
            QMessageBox.warning(self, "错误", "请选择客户")
            return
        sales_order = self.sales_order_input.text().strip() or None
        contract = self.contract_input.text().strip() or None
        plate = self.plate_input.text().strip() or None
        operator = self.operator_input.text()
        remark = self.remark_input.toPlainText()

        svc = OutboundService(self.db)
        try:
            svc.create_outbound(
                date=date, batch_no=batch_no, quantity=quantity,
                location_code=location, spec_id=spec_id,
                customer_id=cust_id, sales_order_no=sales_order,
                contract_no=contract, plate_no=plate,
                operator=operator, remark=remark,
            )
        except ValueError as e:
            QMessageBox.warning(self, "错误", str(e))
            return
        self.accept()
