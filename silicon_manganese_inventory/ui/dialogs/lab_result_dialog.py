from PySide6.QtWidgets import QDoubleSpinBox, QMessageBox, QTextEdit, QPushButton, QLabel, QComboBox
import re
from silicon_manganese_inventory.services.lab_service import LabService
from silicon_manganese_inventory.services.inbound_service import InboundService
from silicon_manganese_inventory.dao.base_dao import LocationDAO
from silicon_manganese_inventory.ui.dialogs.base_eas_dialog import BaseEasDialog


class LabResultDialog(BaseEasDialog):
    def __init__(self, db, pre_inbound_id, parent=None):
        super().__init__(title="录入化验结果", width=480, height=620, parent=parent)
        self.db = db
        self.pre_inbound_id = pre_inbound_id
        self.lab_svc = LabService(db)
        self.inbound_svc = InboundService(db)
        self._inbound_confirmed = False
        self._setup_ui()

    def _setup_ui(self):
        card, cl = self.add_card()

        paste_lbl = QLabel("粘贴化验结果（自动解析）：")
        paste_lbl.setStyleSheet("font-size: 12px; color: #6B7280; border: none; background: transparent; margin-top: 4px;")
        cl.addWidget(paste_lbl)

        self.paste_input = QTextEdit()
        self.paste_input.setMaximumHeight(50)
        self.paste_input.setPlaceholderText("如: Mn含量:66.1%(合格) | Si含量:18.7%(合格) | C含量:1.67%...")
        self.style_textarea(self.paste_input)
        self.paste_input.textChanged.connect(lambda: self.paste_input.setStyleSheet(
            "QTextEdit { border: 1px solid #D1D5DB; border-radius: 4px; padding: 4px 8px; font-size: 13px; background: white; }"))
        cl.addWidget(self.paste_input)

        parse_btn = QPushButton("解析填充")
        parse_btn.setStyleSheet("""
            QPushButton { background: #2563EB; color: white; border: none;
                          padding: 5px 14px; border-radius: 3px; font-size: 12px; }
            QPushButton:hover { background: #1D4ED8; }
        """)
        parse_btn.clicked.connect(self._parse_and_fill)
        cl.addWidget(parse_btn)

        sep = QLabel("")
        sep.setMaximumHeight(4)
        cl.addWidget(sep)

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

        card2, cl2 = self.add_card()

        self.target_location_combo = QComboBox()
        self.target_location_combo.setEditable(True)
        loc_dao = LocationDAO(self.db)
        for loc in loc_dao.list():
            if not loc["code"].startswith("Z"):
                self.target_location_combo.addItem(
                    f"{loc['code']} ({loc['name']})", loc["code"])
        jul_idx = self.target_location_combo.findData("A01-7月")
        if jul_idx >= 0:
            self.target_location_combo.setCurrentIndex(jul_idx)
        self.style_combo(self.target_location_combo)
        self.add_form_row("目标库位:", self.target_location_combo, cl2)

        self.add_primary_button("保存并确认入库", self._save, "#16A34A")
        self.add_cancel_button()

    def _parse_and_fill(self):
        text = self.paste_input.toPlainText().strip()
        if not text:
            return

        field_map = {
            "mn": self.mn_input, "si": self.si_input,
            "c": self.c_input, "s": self.s_input, "p": self.p_input,
        }

        pattern = re.compile(r'(Mn|Si|C|S|P)[-\s]*含量[:\s]*(\d+\.?\d*)', re.IGNORECASE)
        matches = pattern.findall(text)

        filled = []
        for elem, val in matches:
            key = elem.lower()
            if key in field_map:
                try:
                    field_map[key].setValue(float(val))
                    filled.append(key.upper())
                except ValueError:
                    pass

        if not filled:
            QMessageBox.warning(self, "解析失败", "未能从文本中识别元素含量，请检查格式。\n支持格式: Mn含量:66.1%(合格) | Si含量:18.7%(合格)")
        else:
            self.paste_input.setStyleSheet(
                "QTextEdit { border: 2px solid #16A34A; border-radius: 4px; padding: 4px 8px; font-size: 13px; }")

    def _save(self):
        try:
            result = self.lab_svc.record_result(
                pre_inbound_id=self.pre_inbound_id,
                mn_content=self.mn_input.value(),
                si_content=self.si_input.value(),
                p_content=self.p_input.value(),
                s_content=self.s_input.value(),
                c_content=self.c_input.value(),
            )
            overall = result.get("overall_result", "")
            if overall == "合格":
                target = self.target_location_combo.currentData()
                if not target:
                    target = self.target_location_combo.currentText().strip()
                if not target:
                    QMessageBox.warning(self, "错误", "请选择目标库位")
                    return
                loc_dao = LocationDAO(self.db)
                target = loc_dao.get_or_create(target)
                self.inbound_svc.confirm_inbound(self.pre_inbound_id, target_location=target)
                self._inbound_confirmed = True
            elif overall == "不合格":
                QMessageBox.warning(self, "化验不合格",
                    "化验结果为不合格，无法完成入库确认。"
                    "\n化验结果已保存，请联系管理员处理。")
        except Exception as e:
            QMessageBox.warning(self, "错误", str(e))
            return
        self.accept()

    def is_inbound_confirmed(self):
        return self._inbound_confirmed
