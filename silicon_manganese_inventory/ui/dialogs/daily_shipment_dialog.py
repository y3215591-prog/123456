from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QDoubleSpinBox, QSpinBox, QMessageBox, QTextEdit,
)
from datetime import datetime
from silicon_manganese_inventory.dao.base_dao import DailyShipmentDAO


class DailyShipmentDialog(QDialog):
    def __init__(self, db, parent=None, edit_record=None):
        super().__init__(parent)
        self.db = db
        self.edit_record = edit_record
        self.setWindowTitle("编辑发货明细" if edit_record else "新增发货明细")
        self.setMinimumWidth(520)
        self._setup_ui()
        if edit_record:
            self._load_record()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.seq_input = QSpinBox()
        self.seq_input.setRange(0, 999999)
        form.addRow("序号 *:", self.seq_input)

        self.date_input = QLineEdit(datetime.now().strftime("%Y-%m-%d"))
        form.addRow("发货日期:", self.date_input)

        self.plate_input = QLineEdit()
        form.addRow("车牌号:", self.plate_input)

        self.cust_code_input = QLineEdit()
        form.addRow("客户代码:", self.cust_code_input)

        self.cust_name_input = QLineEdit()
        form.addRow("客户名称:", self.cust_name_input)

        self.order_input = QLineEdit()
        form.addRow("销售订单号:", self.order_input)

        self.material_input = QLineEdit()
        form.addRow("物料名称:", self.material_input)

        self.spec_input = QLineEdit()
        form.addRow("规格:", self.spec_input)

        self.batch_input = QLineEdit()
        form.addRow("批次号:", self.batch_input)

        self.load_qty_input = QDoubleSpinBox()
        self.load_qty_input.setRange(0, 99999)
        self.load_qty_input.setDecimals(2)
        self.load_qty_input.valueChanged.connect(self._auto_calc_net)
        form.addRow("装车吨数:", self.load_qty_input)

        self.gross_input = QDoubleSpinBox()
        self.gross_input.setRange(0, 99999)
        self.gross_input.setDecimals(2)
        self.gross_input.valueChanged.connect(self._auto_calc_net)
        form.addRow("毛重:", self.gross_input)

        self.tare_input = QDoubleSpinBox()
        self.tare_input.setRange(0, 99999)
        self.tare_input.setDecimals(2)
        self.tare_input.valueChanged.connect(self._auto_calc_net)
        form.addRow("皮重:", self.tare_input)

        self.net_input = QDoubleSpinBox()
        self.net_input.setRange(0, 99999)
        self.net_input.setDecimals(2)
        form.addRow("净重:", self.net_input)

        self.received_input = QDoubleSpinBox()
        self.received_input.setRange(0, 99999)
        self.received_input.setDecimals(2)
        form.addRow("客户收货净重:", self.received_input)

        self.seal_input = QLineEdit()
        form.addRow("铅封号:", self.seal_input)

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

    def _auto_calc_net(self):
        gross = self.gross_input.value()
        tare = self.tare_input.value()
        if gross > 0 and tare > 0:
            self.net_input.setValue(round(gross - tare, 2))

    def _load_record(self):
        r = self.edit_record
        self.seq_input.setValue(r.get("seq_no") or 0)
        self.date_input.setText(r.get("shipment_date", ""))
        self.plate_input.setText(r.get("plate_no", ""))
        self.cust_code_input.setText(r.get("customer_code", ""))
        self.cust_name_input.setText(r.get("customer_name", ""))
        self.order_input.setText(r.get("sales_order_no", ""))
        self.material_input.setText(r.get("material_name", ""))
        self.spec_input.setText(r.get("spec", ""))
        self.batch_input.setText(r.get("batch_no", ""))
        self.load_qty_input.setValue(r.get("load_quantity") or 0)
        self.gross_input.setValue(r.get("gross_weight") or 0)
        self.tare_input.setValue(r.get("tare_weight") or 0)
        self.net_input.setValue(r.get("net_weight") or 0)
        self.received_input.setValue(r.get("customer_received_weight") or 0)
        self.seal_input.setText(r.get("seal_codes", ""))
        self.remark_input.setText(r.get("remark", ""))

    def _save(self):
        if self.seq_input.value() <= 0:
            QMessageBox.warning(self, "错误", "序号为必填项")
            return
        dao = DailyShipmentDAO(self.db)
        kwargs = {
            "seq_no": self.seq_input.value(),
            "shipment_date": self.date_input.text(),
            "plate_no": self.plate_input.text(),
            "customer_code": self.cust_code_input.text(),
            "customer_name": self.cust_name_input.text(),
            "sales_order_no": self.order_input.text(),
            "material_name": self.material_input.text(),
            "spec": self.spec_input.text(),
            "batch_no": self.batch_input.text(),
            "load_quantity": self.load_qty_input.value(),
            "gross_weight": self.gross_input.value(),
            "tare_weight": self.tare_input.value(),
            "net_weight": self.net_input.value(),
            "customer_received_weight": self.received_input.value(),
            "seal_codes": self.seal_input.text(),
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
