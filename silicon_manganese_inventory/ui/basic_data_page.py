from PySide6.QtWidgets import QComboBox, QPushButton, QHBoxLayout, QMessageBox
from PySide6.QtWidgets import QInputDialog
from silicon_manganese_inventory.ui.base_page import BasePage
from silicon_manganese_inventory.dao.base_dao import SpecDAO, WarehouseDAO
from silicon_manganese_inventory.dao.lab_dao import LabDAO


class BasicDataPage(BasePage):
    def __init__(self, db):
        super().__init__(db, "基础数据管理")
        self.spec_dao = SpecDAO(db)
        self.warehouse_dao = WarehouseDAO(db)
        self.lab_dao = LabDAO(db)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["品名规格", "检验标准", "仓库"])
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        self.add_search_field("数据类型:", self.type_combo)

        self.add_header_button("+ 新增", self._add_item, "#27ae60")
        self._on_type_changed("品名规格")

    def _on_type_changed(self, text):
        if text == "品名规格":
            self.set_table_headers(["ID", "品名规格名称", "备注"])
        elif text == "检验标准":
            self.set_table_headers(["ID", "元素", "最小值", "最大值", "备注"])
        elif text == "仓库":
            self.set_table_headers(["ID", "仓库名称", "地址", "备注"])
        self.refresh()

    def refresh(self):
        text = self.type_combo.currentText()
        if text == "品名规格":
            rows = self.spec_dao.list()
            data = [[r["id"], r["name"], r["remark"] or ""] for r in rows]
        elif text == "检验标准":
            rows = self.lab_dao.get_standards()
            data = [[r["id"], r["element"], r["min_value"], r["max_value"], r["remark"] or ""] for r in rows]
        elif text == "仓库":
            rows = self.warehouse_dao.list()
            data = [[r["id"], r["name"], r["address"] or "", r["remark"] or ""] for r in rows]
        else:
            data = []
        self.populate_table(data)

    def _add_item(self):
        text = self.type_combo.currentText()
        if text == "品名规格":
            name, ok = QInputDialog.getText(self, "新增品名规格", "规格名称:")
            if ok and name.strip():
                self.spec_dao.create(name=name.strip())
        elif text == "检验标准":
            element, ok = QInputDialog.getText(self, "新增检验标准", "元素名称 (如 Mn):")
            if not ok or not element.strip():
                return
            min_val, ok2 = QInputDialog.getDouble(self, "最小值", f"{element} 最小值:", 0, -999, 999, 3)
            if not ok2:
                return
            max_val, ok3 = QInputDialog.getDouble(self, "最大值", f"{element} 最大值:", 100, -999, 999, 3)
            if not ok3:
                return
            self.lab_dao.update_standard(element.strip(), min_val, max_val)
        elif text == "仓库":
            name, ok = QInputDialog.getText(self, "新增仓库", "仓库名称:")
            if ok and name.strip():
                self.warehouse_dao.create(name=name.strip())
        self.refresh()
