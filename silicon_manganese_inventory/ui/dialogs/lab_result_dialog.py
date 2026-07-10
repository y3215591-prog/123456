from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QDoubleSpinBox, QMessageBox,
)
from silicon_manganese_inventory.services.lab_service import LabService


class LabResultDialog(QDialog):
    def __init__(self, db, pre_inbound_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.pre_inbound_id = pre_inbound_id
        self.lab_svc = LabService(db)
        self.setWindowTitle("录入化验结果")
        self.setMinimumWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.mn_input = QDoubleSpinBox()
        self.mn_input.setRange(0, 100)
        self.mn_input.setDecimals(2)
        self.mn_input.setValue(65.00)
        form.addRow("锰 Mn(%):", self.mn_input)

        self.si_input = QDoubleSpinBox()
        self.si_input.setRange(0, 100)
        self.si_input.setDecimals(2)
        self.si_input.setValue(17.00)
        form.addRow("硅 Si(%):", self.si_input)

        self.p_input = QDoubleSpinBox()
        self.p_input.setRange(0, 10)
        self.p_input.setDecimals(3)
        self.p_input.setValue(0.200)
        form.addRow("磷 P(%):", self.p_input)

        self.s_input = QDoubleSpinBox()
        self.s_input.setRange(0, 10)
        self.s_input.setDecimals(3)
        self.s_input.setValue(0.030)
        form.addRow("硫 S(%):", self.s_input)

        self.c_input = QDoubleSpinBox()
        self.c_input.setRange(0, 10)
        self.c_input.setDecimals(2)
        self.c_input.setValue(1.80)
        form.addRow("碳 C(%):", self.c_input)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        save_btn = QPushButton("保存并确认入库")
        save_btn.setStyleSheet("background-color: #27ae60; color: white; padding: 8px 24px;")
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _save(self):
        try:
            self.lab_svc.record_result(
                pre_inbound_id=self.pre_inbound_id,
                mn_content=self.mn_input.value(),
                si_content=self.si_input.value(),
                p_content=self.p_input.value(),
                s_content=self.s_input.value(),
                c_content=self.c_input.value(),
            )
        except ValueError as e:
            QMessageBox.warning(self, "错误", str(e))
            return
        self.accept()
