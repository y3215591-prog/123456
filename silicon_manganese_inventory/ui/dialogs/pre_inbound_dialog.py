from PySide6.QtWidgets import (
    QHBoxLayout, QLineEdit,
    QComboBox, QSpinBox, QLabel, QMessageBox, QTextEdit,
)
from PySide6.QtCore import Qt
from datetime import datetime
from silicon_manganese_inventory.ui.dialogs.base_eas_dialog import BaseEasDialog
from silicon_manganese_inventory.services.inbound_service import InboundService
from silicon_manganese_inventory.dao.seal_dao import SealDAO
from silicon_manganese_inventory.dao.base_dao import SpecDAO, LocationDAO


class PreInboundDialog(BaseEasDialog):
    def __init__(self, db, parent=None, edit_record=None):
        self.db = db
        self.edit_record = edit_record
        super().__init__(
            title="编辑预入库" if edit_record else "新增预入库",
            width=640, height=620, parent=parent,
        )
        self._setup_ui()
        if edit_record:
            self._load_record()
        self._update_preview()

    def _setup_ui(self):
        card, cl = self.add_card()
        self.add_section_title("基本信息")

        self.date_input = QLineEdit(datetime.now().strftime("%Y-%m-%d"))
        self.style_input(self.date_input)
        self.add_form_row("日期:", self.date_input, cl)

        self.batch_input = QLineEdit()
        self.batch_input.setPlaceholderText("如 1226062111")
        self.style_input(self.batch_input)
        self.add_form_row("批次号 *:", self.batch_input, cl)

        self.spec_combo = QComboBox()
        self.spec_combo.setEditable(True)
        self.style_combo(self.spec_combo)
        spec_dao = SpecDAO(self.db)
        for s in spec_dao.list():
            self.spec_combo.addItem(s["name"], s["id"])
        self.add_form_row("品名规格:", self.spec_combo, cl)

        self.quantity_input = QSpinBox()
        self.quantity_input.setRange(1, 99999)
        self.quantity_input.setValue(1)
        self.style_spin(self.quantity_input)
        self.add_form_row("数量(吨) *:", self.quantity_input, cl)

        self.location_combo = QComboBox()
        self.location_combo.setEditable(True)
        self.style_combo(self.location_combo)
        loc_dao = LocationDAO(self.db)
        for loc in loc_dao.list(code_prefix="Z"):
            self.location_combo.addItem(f"{loc['code']} ({loc['name']})", loc["code"])
        z01_idx = self.location_combo.findData("Z01")
        if z01_idx >= 0:
            self.location_combo.setCurrentIndex(z01_idx)
        self.add_form_row("自然块库位:", self.location_combo, cl)

        card2, cl2 = self.add_card()
        self.add_section_title("铅封号分配", cl2)

        self.seal_batch_combo = QComboBox()
        self.style_combo(self.seal_batch_combo)
        seal_dao = SealDAO(self.db)
        for batch in seal_dao.list_batches():
            available = batch["total_count"] - (batch["used_count"] or 0)
            self.seal_batch_combo.addItem(
                f"{batch['start_code']}~{batch['end_code']} (剩余{available})", batch["id"])
        self.add_form_row("铅封号段:", self.seal_batch_combo, cl2)

        self.preview_label = QLabel("")
        self.preview_label.setStyleSheet(
            "color: #16A34A; font-weight: bold; font-size: 13px; padding: 4px 0; border: none; background: transparent;")
        self.add_form_row("分配预览:", self.preview_label, cl2)

        card3, cl3 = self.add_card()
        self.add_section_title("其他信息（选填）", cl3)

        self.operator_input = QLineEdit()
        self.operator_input.setPlaceholderText("选填")
        self.style_input(self.operator_input)
        self.add_form_row("操作人:", self.operator_input, cl3)

        self.remark_input = QTextEdit()
        self.remark_input.setMaximumHeight(60)
        self.remark_input.setPlaceholderText("选填")
        self.style_textarea(self.remark_input)
        self.add_form_row("备注:", self.remark_input, cl3)

        self.add_primary_button("保存", self._save)
        self.add_cancel_button()

        self.quantity_input.valueChanged.connect(self._update_preview)
        self.seal_batch_combo.currentIndexChanged.connect(self._update_preview)

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
                self.preview_label.setStyleSheet(
                    "color: #16A34A; font-weight: bold; font-size: 13px; padding: 4px 0; border: none; background: transparent;")
                self.preview_label.setText(
                    f"{qty} 吨，分配: {seals[0]['seal_code']} ~ {seals[-1]['seal_code']}")
            else:
                self.preview_label.setText(f"{qty} 吨，可分配")
        else:
            self.preview_label.setStyleSheet(
                "color: #DC2626; font-weight: bold; font-size: 13px; padding: 4px 0; border: none; background: transparent;")
            self.preview_label.setText(f"号段不足，需要 {qty} 个，仅剩 {available} 个")

    def _load_record(self):
        r = self.edit_record
        self.date_input.setText(r["date"] or "")
        self.batch_input.setText(r["batch_no"] or "")
        idx = self.spec_combo.findData(r["spec_id"])
        if idx >= 0:
            self.spec_combo.setCurrentIndex(idx)
        self.quantity_input.setValue(int(r["quantity"] or 0))
        loc_code = r["location_code"]
        if loc_code:
            idx = self.location_combo.findData(loc_code)
            if idx >= 0:
                self.location_combo.setCurrentIndex(idx)
            else:
                self.location_combo.setCurrentText(loc_code)
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
        if not location:
            raw_text = self.location_combo.currentText().strip()
            if raw_text:
                location = raw_text
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
                    seal_batch_id=batch_id,
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
