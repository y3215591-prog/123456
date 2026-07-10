from PySide6.QtWidgets import QDoubleSpinBox, QMessageBox
from silicon_manganese_inventory.services.lab_service import LabService
from silicon_manganese_inventory.ui.dialogs.base_eas_dialog import BaseEasDialog


class LabResultDialog(BaseEasDialog):
    def __init__(self, db, pre_inbound_id, parent=None):
        super().__init__(title="录入化验结果", width=420, height=380, parent=parent)
        self.db = db
        self.pre_inbound_id = pre_inbound_id
        self.lab_svc = LabService(db)
        self._setup_ui()

    def _setup_ui(self):
        card, cl = self.add_card()

        self.mn_input = QDoubleSpinBox()
        self.mn_input.setRange(0, 100)
        self.mn_input.setDecimals(2)
        self.mn_input.setValue(65.00)
        self.add_form_row("锰 Mn(%):", self.mn_input, cl)

        self.si_input = QDoubleSpinBox()
        self.si_input.setRange(0, 100)
        self.si_input.setDecimals(2)
        self.si_input.setValue(17.00)
        self.add_form_row("硅 Si(%):", self.si_input, cl)

        self.p_input = QDoubleSpinBox()
        self.p_input.setRange(0, 10)
        self.p_input.setDecimals(3)
        self.p_input.setValue(0.200)
        self.add_form_row("磷 P(%):", self.p_input, cl)

        self.s_input = QDoubleSpinBox()
        self.s_input.setRange(0, 10)
        self.s_input.setDecimals(3)
        self.s_input.setValue(0.030)
        self.add_form_row("硫 S(%):", self.s_input, cl)

        self.c_input = QDoubleSpinBox()
        self.c_input.setRange(0, 10)
        self.c_input.setDecimals(2)
        self.c_input.setValue(1.80)
        self.add_form_row("碳 C(%):", self.c_input, cl)

        self.add_primary_button("保存并确认入库", self._save, "#16A34A")
        self.add_cancel_button()

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
