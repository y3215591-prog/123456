from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QComboBox, QSpinBox, QLabel, QMessageBox, QTextEdit,
)
from datetime import datetime
from silicon_manganese_inventory.services.inbound_service import InboundService
from silicon_manganese_inventory.dao.seal_dao import SealDAO
from silicon_manganese_inventory.dao.base_dao import SpecDAO, LocationDAO


class PreInboundDialog(QDialog):
    def __init__(self, db, parent=None, edit_record=None):
        super().__init__(parent)
        self.db = db
        self.edit_record = edit_record
        self.setWindowTitle("编辑预入库" if edit_record else "新增预入库")
        self.setMinimumWidth(500)
        self._setup_ui()
        if edit_record:
            self._load_record()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.date_input = QLineEdit(datetime.now().strftime("%Y-%m-%d"))
        form.addRow("日期:", self.date_input)

        self.batch_input = QLineEdit()
        self.batch_input.setPlaceholderText("如 1226062111")
        form.addRow("批次号 *:", self.batch_input)

        self.spec_combo = QComboBox()
        self.spec_combo.setEditable(True)
        spec_dao = SpecDAO(self.db)
        for s in spec_dao.list():
            self.spec_combo.addItem(s["name"], s["id"])
        form.addRow("品名规格:", self.spec_combo)

        self.quantity_input = QSpinBox()
        self.quantity_input.setRange(1, 99999)
        self.quantity_input.setValue(1)
        form.addRow("数量(吨) *:", self.quantity_input)

        self.location_combo = QComboBox()
        self.location_combo.setEditable(True)
        loc_dao = LocationDAO(self.db)
        for l in loc_dao.list(code_prefix="Z"):
            self.location_combo.addItem(f"{l['code']} ({l['name']})", l["code"])
        z01_idx = self.location_combo.findData("Z01")
        if z01_idx >= 0:
            self.location_combo.setCurrentIndex(z01_idx)
        form.addRow("自然块库位:", self.location_combo)

        self.seal_batch_combo = QComboBox()
        seal_dao = SealDAO(self.db)
        for b in seal_dao.list_batches():
            available = b["total_count"] - (b["used_count"] or 0)
            self.seal_batch_combo.addItem(
                f"{b['start_code']}~{b['end_code']} (剩余{available})", b["id"])
        form.addRow("铅封号段:", self.seal_batch_combo)

        self.preview_label = QLabel("")
        self.preview_label.setStyleSheet("color: #27ae60; font-weight: bold;")
        form.addRow("分配预览:", self.preview_label)

        self.operator_input = QLineEdit()
        form.addRow("操作人:", self.operator_input)

        self.remark_input = QTextEdit()
        self.remark_input.setMaximumHeight(60)
        form.addRow("备注:", self.remark_input)

        layout.addLayout(form)

        self.quantity_input.valueChanged.connect(self._update_preview)
        self.seal_batch_combo.currentIndexChanged.connect(self._update_preview)

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

    def _update_preview(self):
        qty = self.quantity_input.value()
        if self.seal_batch_combo.currentIndex() < 0:
            return
        batch_id = self.seal_batch_combo.currentData()
        seal_dao = SealDAO(self.db)
        available = seal_dao.get_available_count(batch_id)
        if available >= qty:
            seals = seal_dao.get_available_seals(batch_id, limit=qty)
            if seals:
                self.preview_label.setText(
                    f"{qty} 吨，将分配: {seals[0]['seal_code']} ~ {seals[-1]['seal_code']}")
            else:
                self.preview_label.setText(f"{qty} 吨，可分配")
        else:
            self.preview_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
            self.preview_label.setText(f"号段不足！需要 {qty} 个，仅剩 {available} 个")

    def _load_record(self):
        r = self.edit_record
        self.date_input.setText(r["date"])
        self.batch_input.setText(r["batch_no"])
        idx = self.spec_combo.findData(r["spec_id"])
        if idx >= 0:
            self.spec_combo.setCurrentIndex(idx)
        self.quantity_input.setValue(int(r["quantity"]))
        idx = self.location_combo.findText(r["location_code"])
        if idx >= 0:
            self.location_combo.setCurrentIndex(idx)
        idx = self.seal_batch_combo.findData(r["seal_batch_id"])
        if idx >= 0:
            self.seal_batch_combo.setCurrentIndex(idx)
        self.operator_input.setText(r["operator"] or "")
        self.remark_input.setText(r["remark"] or "")

    def _save(self):
        date = self.date_input.text()
        batch_no = self.batch_input.text().strip()
        quantity = self.quantity_input.value()
        if not date or not batch_no or quantity <= 0:
            QMessageBox.warning(self, "错误", "日期、批次号和数量为必填项")
            return
        if self.seal_batch_combo.currentIndex() < 0:
            QMessageBox.warning(self, "错误", "请选择铅封号段")
            return
        batch_id = self.seal_batch_combo.currentData()
        spec_id = self.spec_combo.currentData()
        if isinstance(spec_id, str):
            spec_id = None
        location = self.location_combo.currentData()
        if location:
            raw_text = self.location_combo.currentText().strip()
            if raw_text != location and not self.location_combo.findData(raw_text, flags=0):
                location = raw_text
        else:
            location = self.location_combo.currentText().strip()
        if location:
            loc_dao = LocationDAO(self.db)
            location = loc_dao.get_or_create(location)
        operator = self.operator_input.text()
        remark = self.remark_input.toPlainText()

        svc = InboundService(self.db)
        try:
            if self.edit_record:
                from silicon_manganese_inventory.dao.inbound_dao import InboundDAO
                dao = InboundDAO(self.db)
                dao.update_pre_inbound(
                    self.edit_record["id"],
                    date=date, batch_no=batch_no, quantity=quantity,
                    spec_id=spec_id, location_code=location,
                    operator=operator, remark=remark,
                )
            else:
                svc.create_pre_inbound(
                    date=date, batch_no=batch_no, quantity=quantity,
                    spec_id=spec_id, location_code=location,
                    seal_batch_id=batch_id, operator=operator, remark=remark,
                )
        except Exception as e:
            QMessageBox.warning(self, "错误", str(e))
            return
        self.accept()
