from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QSpinBox,
    QComboBox, QLabel, QMessageBox, QTextEdit, QFrame,
)
from PySide6.QtCore import QTimer
from datetime import datetime
from silicon_manganese_inventory.services.outbound_service import OutboundService
from silicon_manganese_inventory.dao.base_dao import CustomerDAO, SpecDAO, LocationDAO, SalesOrderDAO
from silicon_manganese_inventory.ui.dialogs.base_eas_dialog import BaseEasDialog


class OutboundDialog(BaseEasDialog):
    def __init__(self, db, parent=None):
        super().__init__(title="新增出库", width=520, height=660, parent=parent)
        self.db = db
        self._order_timer = QTimer(self)
        self._order_timer.setSingleShot(True)
        self._order_timer.setInterval(300)
        self._order_timer.timeout.connect(self._on_order_changed_debounced)
        self._block_batch_signal = False
        self._block_contract_signal = False
        self._setup_ui()
        self._on_location_changed()
        self._on_qty_changed()

    def _hint_label(self, text, color="#6B7280"):
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {color}; font-size: 12px; padding: 0 0 0 88px; border: none; background: transparent;")
        return lbl

    def _setup_ui(self):
        card, cl = self.add_card()

        self.date_input = QLineEdit(datetime.now().strftime("%Y-%m-%d"))
        self.style_input(self.date_input)
        self.add_form_row("日期:", self.date_input, cl)

        self.batch_combo = QComboBox()
        self.batch_combo.setEditable(True)
        self.batch_combo.setInsertPolicy(QComboBox.NoInsert)
        with self.db.get_connection() as conn:
            batches = conn.execute(
                "SELECT DISTINCT batch_no FROM seal_numbers WHERE status='in_stock' AND batch_no != '' ORDER BY batch_no"
            ).fetchall()
        for b in batches:
            self.batch_combo.addItem(b["batch_no"])
        self.batch_combo.currentTextChanged.connect(self._on_batch_changed)
        self.add_form_row("批次号 *:", self.batch_combo, cl)

        self.spec_combo = QComboBox()
        self.spec_combo.setEditable(True)
        spec_dao = SpecDAO(self.db)
        for s in spec_dao.list():
            self.spec_combo.addItem(s["name"], s["id"])
        self.add_form_row("品名规格:", self.spec_combo, cl)

        self.sales_order_input = QLineEdit()
        self.sales_order_input.setPlaceholderText("输入后自动带出客户/规格/合同")
        self.style_input(self.sales_order_input)
        self.sales_order_input.textChanged.connect(self._on_order_text_changed)
        self.add_form_row("销售订单号:", self.sales_order_input, cl)

        self.order_remaining_label = self._hint_label("", "#D97706")
        cl.addWidget(self.order_remaining_label)

        self.contract_combo = QComboBox()
        self.contract_combo.setEditable(True)
        self.contract_combo.setInsertPolicy(QComboBox.NoInsert)
        with self.db.get_connection() as conn:
            contracts = conn.execute(
                "SELECT DISTINCT contract_no FROM sales_orders WHERE contract_no != '' ORDER BY contract_no"
            ).fetchall()
        for c in contracts:
            self.contract_combo.addItem(c["contract_no"])
        self.add_form_row("合同号:", self.contract_combo, cl)

        self.customer_combo = QComboBox()
        self.customer_combo.setEditable(True)
        self.customer_combo.setInsertPolicy(QComboBox.NoInsert)
        cust_dao = CustomerDAO(self.db)
        for c in cust_dao.list():
            self.customer_combo.addItem(c["name"], c["id"])
        self.add_form_row("客户:", self.customer_combo, cl)

        qc_widget = QFrame()
        qc_layout = QHBoxLayout(qc_widget)
        qc_layout.setContentsMargins(0, 0, 0, 0)
        self.quick_cust_input = QLineEdit()
        self.quick_cust_input.setPlaceholderText("输入新客户名快速新增")
        self.style_input(self.quick_cust_input)
        self.quick_cust_btn = QPushButton("+新增")
        self.quick_cust_btn.setStyleSheet(
            "QPushButton { background: #10B981; color: white; border: none; padding: 5px 12px; border-radius: 3px; font-size: 12px; }")
        self.quick_cust_btn.clicked.connect(self._quick_add_customer)
        qc_layout.addWidget(self.quick_cust_input)
        qc_layout.addWidget(self.quick_cust_btn)
        self.add_form_row("快速新增:", qc_widget, cl)

        self.plate_input = QLineEdit()
        self.style_input(self.plate_input)
        self.add_form_row("车牌号:", self.plate_input, cl)

        self.location_combo = QComboBox()
        self.location_combo.setEditable(True)
        self.location_combo.setInsertPolicy(QComboBox.NoInsert)
        loc_dao = LocationDAO(self.db)
        has_items = False
        for l in loc_dao.list():
            if l["code"].startswith("Z"):
                continue
            available = loc_dao.get_available_qty(l["code"])
            if available <= 0:
                continue
            self.location_combo.addItem(f"{l['code']} (库存{available}吨)", l["code"])
            has_items = True
        if not has_items:
            self.location_combo.addItem("暂无可用库位", None)
        self.location_combo.currentIndexChanged.connect(self._on_location_changed)
        self.add_form_row("出库库位:", self.location_combo, cl)

        self.max_qty_label = self._hint_label("", "#16A34A")
        cl.addWidget(self.max_qty_label)

        self.quantity_input = QSpinBox()
        self.quantity_input.setRange(1, 99999)
        self.quantity_input.setValue(1)
        self.quantity_input.valueChanged.connect(self._on_qty_changed)
        self.add_form_row("数量(吨) *:", self.quantity_input, cl)

        self.seal_preview = QLabel("")
        self.seal_preview.setStyleSheet(
            "color: #2B579A; font-weight: bold; font-size: 12px; padding: 0 0 0 88px; border: none; background: transparent;")
        cl.addWidget(self.seal_preview)

        self.operator_input = QLineEdit()
        self.style_input(self.operator_input)
        self.add_form_row("操作人:", self.operator_input, cl)

        self.remark_input = QTextEdit()
        self.remark_input.setMaximumHeight(60)
        self.style_textarea(self.remark_input)
        self.add_form_row("备注:", self.remark_input, cl)

        self.add_primary_button("保存", self._save, "#16A34A")
        self.add_cancel_button()

    def _on_batch_changed(self, text):
        if self._block_batch_signal:
            return
        batch = text.strip()
        if not batch:
            return
        with self.db.get_connection() as conn:
            locs = conn.execute(
                "SELECT DISTINCT location_code FROM seal_numbers WHERE batch_no=? AND status='in_stock' AND location_code != '' ORDER BY location_code",
                (batch,),
            ).fetchall()
        if locs:
            self._block_batch_signal = True
            for loc in locs:
                idx = self.location_combo.findData(loc["location_code"])
                if idx >= 0:
                    self.location_combo.setCurrentIndex(idx)
                    self._block_batch_signal = False
                    return
            loc_code = locs[0]["location_code"]
            idx = self.location_combo.findData(loc_code)
            if idx >= 0:
                self.location_combo.setCurrentIndex(idx)
            else:
                loc_dao = LocationDAO(self.db)
                available = loc_dao.get_available_qty(loc_code)
                self.location_combo.insertItem(0, f"{loc_code} (库存{available}吨)", loc_code)
                self.location_combo.setCurrentIndex(0)
            self._block_batch_signal = False

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
            if order["customer_name"]:
                idx = self.customer_combo.findText(order["customer_name"])
                if idx >= 0:
                    self.customer_combo.setCurrentIndex(idx)
            if order["material_desc"]:
                self.spec_combo.setCurrentText(order["material_desc"])
            if order["contract_no"]:
                self._block_contract_signal = True
                self.contract_combo.setCurrentText(order["contract_no"])
                self._block_contract_signal = False
            ordered = (order["quantity"] or 0)
            shipped = self._get_order_shipped(text.strip())
            remaining = ordered - shipped
            status_text = "已完成" if remaining <= 0 else f"待发 {remaining} 吨"
            self.order_remaining_label.setText(f"订购: {ordered}吨 | 已发: {shipped}吨 | {status_text}")
            if remaining <= 0:
                self.order_remaining_label.setStyleSheet(
                    "color: #16A34A; font-size: 12px; padding: 0 0 0 88px; border: none; background: transparent;")
            else:
                self.order_remaining_label.setStyleSheet(
                    "color: #D97706; font-size: 12px; padding: 0 0 0 88px; border: none; background: transparent;")
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
        ordered = (order["quantity"] or 0)
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
                    "QSpinBox { border: 1px solid #D1D5DB; border-radius: 3px; padding: 5px 10px; "
                    "font-size: 13px; background: #FFF5F5; min-height: 28px; color: #DC2626; font-weight: bold; }")
                self.seal_preview.setStyleSheet(
                    "color: #DC2626; font-weight: bold; font-size: 12px; padding: 0 0 0 88px; border: none; background: transparent;")
            else:
                self.quantity_input.setStyleSheet(
                    "QSpinBox { border: 1px solid #D1D5DB; border-radius: 3px; padding: 5px 10px; "
                    "font-size: 13px; background: #FFFFFF; min-height: 28px; }")
                self.seal_preview.setStyleSheet(
                    "color: #2B579A; font-weight: bold; font-size: 12px; padding: 0 0 0 88px; border: none; background: transparent;")
        else:
            self.quantity_input.setStyleSheet(
                "QSpinBox { border: 1px solid #D1D5DB; border-radius: 3px; padding: 5px 10px; "
                "font-size: 13px; background: #FFFFFF; min-height: 28px; }")
            self.seal_preview.setStyleSheet(
                "color: #2B579A; font-weight: bold; font-size: 12px; padding: 0 0 0 88px; border: none; background: transparent;")
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
        batch_no = self.batch_combo.currentText().strip()
        quantity = self.quantity_input.value()
        if not date or not batch_no or quantity <= 0:
            QMessageBox.warning(self, "错误", "日期、批次号和数量为必填项")
            return
        location = self.location_combo.currentData()
        if not location:
            location = self.location_combo.currentText().strip()
        if not location:
            QMessageBox.warning(self, "错误", "请选择出库库位")
            return
        loc_dao = LocationDAO(self.db)
        location = loc_dao.get_or_create(location)
        spec_id = self.spec_combo.currentData()
        if isinstance(spec_id, str):
            spec_name = self.spec_combo.currentText().strip()
            if spec_name:
                spec_dao = SpecDAO(self.db)
                spec_id = spec_dao.create(name=spec_name)
            else:
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
        sales_order = self.sales_order_input.text().strip()
        contract = self.contract_combo.currentText().strip()
        plate = self.plate_input.text().strip()
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
