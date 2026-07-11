from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QDoubleSpinBox, QMessageBox, QTextEdit, QLabel,
    QFrame, QWidget, QScrollArea,
)
from PySide6.QtCore import Qt
from datetime import datetime
from silicon_manganese_inventory.ui.dialogs.base_eas_dialog import BaseEasDialog
from silicon_manganese_inventory.dao.base_dao import DailyShipmentDAO
from silicon_manganese_inventory.dao.seal_dao import SealDAO


class BatchEntryWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame { background: #F0F4F8; border-radius: 6px; border: 1px solid #E2E8F0; }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        self.batch_input = QLineEdit()
        self.batch_input.setPlaceholderText("批次号(10位)")
        self.batch_input.setMaximumWidth(130)
        self.batch_input.setStyleSheet("""
            QLineEdit { border: 1px solid #E2E8F0; border-radius: 4px; padding: 6px 10px; font-size: 13px; background: white; }
            QLineEdit:focus { border-color: #2B579A; }
        """)

        self.qty_input = QDoubleSpinBox()
        self.qty_input.setRange(0, 99999)
        self.qty_input.setDecimals(2)
        self.qty_input.setValue(0)
        self.qty_input.setMaximumWidth(120)
        self.qty_input.setStyleSheet("""
            QDoubleSpinBox { border: 1px solid #E2E8F0; border-radius: 4px; padding: 6px 10px; font-size: 13px; background: white; }
            QDoubleSpinBox:focus { border-color: #2B579A; }
        """)

        layout.addWidget(QLabel("批次号:"))
        layout.addWidget(self.batch_input)
        layout.addWidget(QLabel("吨数:"))
        layout.addWidget(self.qty_input)
        layout.addStretch()

    def get_data(self):
        return {
            "batch_no": self.batch_input.text().strip(),
            "quantity": self.qty_input.value(),
        }


class DailyShipmentDialog(BaseEasDialog):
    def __init__(self, db, parent=None, edit_record=None):
        self.db = db
        self.edit_record = edit_record
        self._batch_widgets = []

        super().__init__(
            title="编辑发货明细" if edit_record else "新增发货明细",
            width=660, height=640, parent=parent,
        )
        self._setup_ui()
        if edit_record:
            self._load_record()

    def _setup_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("QWidget { background: transparent; }")
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(0, 4, 0, 4)
        scroll_layout.setSpacing(0)

        card, cl = self.add_card(scroll_layout)
        self.add_section_title("基本信息", cl)

        seq_widget = QWidget()
        seq_inner = QHBoxLayout(seq_widget)
        seq_inner.setContentsMargins(0, 0, 0, 0)
        self.seq_label = QLabel("")
        self.seq_label.setMinimumWidth(80)
        seq_inner.addWidget(self.seq_label)
        seq_inner.addStretch()
        self.add_form_row("序号:", seq_widget, cl)

        self._load_seq_no()

        self.date_input = QLineEdit(datetime.now().strftime("%Y-%m-%d"))
        self.style_input(self.date_input)
        self.add_form_row("发货日期:", self.date_input, cl)

        self.order_input = QLineEdit()
        self.order_input.setPlaceholderText("输入后自动匹配客户")
        self.style_input(self.order_input)
        self.order_input.textChanged.connect(self._on_order_changed)
        self.add_form_row("销售订单号:", self.order_input, cl)

        self.cust_name_label = QLabel("-")
        self.cust_name_label.setStyleSheet("color: #374151; font-size: 13px; padding: 4px 0; border: none; background: transparent;")
        self.add_form_row("客户名称:", self.cust_name_label, cl)

        self.cust_code_label = QLabel("-")
        self.cust_code_label.setStyleSheet("color: #6B7280; font-size: 12px; padding: 4px 0; border: none; background: transparent;")
        self.add_form_row("客户代码:", self.cust_code_label, cl)

        self.plate_input = QLineEdit()
        self.style_input(self.plate_input)
        self.add_form_row("车牌号:", self.plate_input, cl)

        card2, cl2 = self.add_card(scroll_layout)
        self.add_section_title("重量信息", cl2)

        self.gross_input = QDoubleSpinBox()
        self.gross_input.setRange(0, 99999)
        self.gross_input.setDecimals(2)
        self.style_spin(self.gross_input)
        self.gross_input.valueChanged.connect(self._auto_calc_net)
        self.add_form_row("毛重:", self.gross_input, cl2)

        self.tare_input = QDoubleSpinBox()
        self.tare_input.setRange(0, 99999)
        self.tare_input.setDecimals(2)
        self.style_spin(self.tare_input)
        self.tare_input.valueChanged.connect(self._auto_calc_net)
        self.add_form_row("皮重:", self.tare_input, cl2)

        self.net_input = QDoubleSpinBox()
        self.net_input.setRange(0, 99999)
        self.net_input.setDecimals(2)
        self.style_spin(self.net_input)
        self.add_form_row("净重:", self.net_input, cl2)

        card3, cl3 = self.add_card(scroll_layout)
        self.add_section_title("批次明细（支持多批次）", cl3)

        self.batch_list_layout = QVBoxLayout()
        self.batch_list_layout.setSpacing(8)
        cl3.addLayout(self.batch_list_layout)

        add_batch_layout = QHBoxLayout()
        add_batch_btn = QPushButton("+ 添加批次")
        add_batch_btn.setCursor(Qt.PointingHandCursor)
        add_batch_btn.setStyleSheet("""
            QPushButton {
                background: #EBF0FA; color: #2B579A; border: 1px dashed #2B579A;
                border-radius: 4px; padding: 6px 16px; font-size: 12px;
            }
            QPushButton:hover { background: #D4E2F9; }
        """)
        add_batch_btn.clicked.connect(self._add_batch_row)
        add_batch_layout.addWidget(add_batch_btn)
        add_batch_layout.addStretch()
        cl3.addLayout(add_batch_layout)

        self.seal_preview_label = QLabel("")
        self.seal_preview_label.setStyleSheet("color: #16A34A; font-size: 12px; padding: 4px 0; border: none; background: transparent;")
        cl3.addWidget(self.seal_preview_label)

        card4, cl4 = self.add_card(scroll_layout)
        self.add_section_title("其他信息（选填）", cl4)

        self.received_input = QDoubleSpinBox()
        self.received_input.setRange(0, 99999)
        self.received_input.setDecimals(2)
        self.style_spin(self.received_input)
        self.add_form_row("客户收货净重:", self.received_input, cl4)

        self.remark_input = QTextEdit()
        self.remark_input.setMaximumHeight(60)
        self.remark_input.setPlaceholderText("选填")
        self.style_textarea(self.remark_input)
        self.add_form_row("备注:", self.remark_input, cl4)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        self.body_layout.addWidget(scroll)

        self.add_primary_button("保存", self._save)
        self.add_cancel_button()

        self._add_batch_row()

    def _on_order_changed(self):
        order_no = self.order_input.text().strip()
        if not order_no:
            self.cust_name_label.setText("-")
            self.cust_code_label.setText("-")
            return
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT customer_name, customer_code FROM sales_orders WHERE order_no=? LIMIT 1",
                (order_no,),
            ).fetchone()
        if row:
            self.cust_name_label.setText(row["customer_name"] or "")
            self.cust_code_label.setText(row["customer_code"] or "")
        else:
            self.cust_name_label.setText("(未找到订单)")
            self.cust_code_label.setText("(未找到订单)")

    def _add_batch_row(self):
        entry = BatchEntryWidget()
        entry.batch_input.textChanged.connect(self._refresh_seal_preview)
        entry.qty_input.valueChanged.connect(self._refresh_seal_preview)
        self.batch_list_layout.addWidget(entry)
        self._batch_widgets.append(entry)

    def _refresh_seal_preview(self):
        seal_parts = []
        for w in self._batch_widgets:
            data = w.get_data()
            if data["batch_no"] and data["quantity"] > 0:
                qty_int = max(1, int(data["quantity"]))
                with self.db.get_connection() as conn:
                    seals = conn.execute(
                        "SELECT seal_code FROM seal_numbers WHERE batch_no=? AND status='in_stock' ORDER BY seal_code LIMIT ?",
                        (data["batch_no"], qty_int),
                    ).fetchall()
                if seals:
                    codes = [s["seal_code"] for s in seals]
                    seal_parts.append(f"{data['batch_no']}: {codes[0]}~{codes[-1]} ({len(codes)}个)")
        if seal_parts:
            self.seal_preview_label.setText("铅封分配预览: " + " | ".join(seal_parts))
        else:
            self.seal_preview_label.setText("")

    def _auto_calc_net(self):
        gross = self.gross_input.value()
        tare = self.tare_input.value()
        if gross > 0 and tare > 0:
            self.net_input.setValue(round(gross - tare, 2))

    def _load_seq_no(self):
        if self.edit_record:
            self.seq_label.setText(str(self.edit_record["seq_no"] or ""))
        else:
            with self.db.get_connection() as conn:
                self._next_seq = (conn.execute(
                    "SELECT COALESCE(MAX(seq_no), 0) + 1 FROM daily_shipments"
                ).fetchone()[0])
                self.seq_label.setText(str(self._next_seq))

    def _load_record(self):
        r = self.edit_record
        self._load_seq_no()
        self.date_input.setText(r["shipment_date"] or "")
        self.plate_input.setText(r["plate_no"] or "")
        self.order_input.setText(r["sales_order_no"] or "")
        self._on_order_changed()
        self.gross_input.setValue(r["gross_weight"] or 0)
        self.tare_input.setValue(r["tare_weight"] or 0)
        self.net_input.setValue(r["net_weight"] or 0)
        self.received_input.setValue(r["customer_received_weight"] or 0)
        self.remark_input.setText(r["remark"] or "")

        batch_no_str = r["batch_no"] or ""
        if batch_no_str:
            batches = [b.strip() for b in batch_no_str.split(",") if b.strip()]
            self._batch_widgets[0].batch_input.setText(batches[0] if batches else "")
            qty = r["load_quantity"] or 0
            self._batch_widgets[0].qty_input.setValue(float(qty) if len(batches) <= 1 else 0)
            for i, b in enumerate(batches[1:], 1):
                self._add_batch_row()
                self._batch_widgets[i].batch_input.setText(b)

    def _save(self):
        dao = DailyShipmentDAO(self.db)
        seq_no = int(self.seq_label.text() or 0)

        batches = []
        total_qty = 0
        seal_codes_list = []

        for w in self._batch_widgets:
            data = w.get_data()
            if data["batch_no"] and data["quantity"] > 0:
                batches.append(data["batch_no"])
                total_qty += data["quantity"]
                qty_int = max(1, int(data["quantity"]))
                with self.db.get_connection() as conn:
                    seals = conn.execute(
                        "SELECT seal_code FROM seal_numbers WHERE batch_no=? AND status='in_stock' ORDER BY seal_code LIMIT ?",
                        (data["batch_no"], qty_int),
                    ).fetchall()
                seal_codes_list.extend([s["seal_code"] for s in seals])

        batch_no_str = ",".join(batches)

        cust_name = self.cust_name_label.text().strip()
        if cust_name in ("-", "(未找到订单)"):
            cust_name = ""
        cust_code = self.cust_code_label.text().strip()
        if cust_code in ("-", "(未找到订单)"):
            cust_code = ""

        kwargs = {
            "seq_no": seq_no,
            "shipment_date": self.date_input.text(),
            "plate_no": self.plate_input.text(),
            "customer_code": cust_code,
            "customer_name": cust_name,
            "sales_order_no": self.order_input.text().strip(),
            "material_name": "",
            "spec": "",
            "batch_no": batch_no_str,
            "load_quantity": round(total_qty, 2),
            "gross_weight": self.gross_input.value(),
            "tare_weight": self.tare_input.value(),
            "net_weight": self.net_input.value(),
            "customer_received_weight": self.received_input.value(),
            "seal_codes": ",".join(seal_codes_list),
            "remark": self.remark_input.toPlainText(),
        }
        try:
            if self.edit_record:
                dao.update(self.edit_record["id"], **kwargs)
            else:
                dao.create(**kwargs)
        except Exception as e:
            QMessageBox.warning(self, "错误", str(e))
            return
        self.accept()
