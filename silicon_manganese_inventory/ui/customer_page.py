from PySide6.QtWidgets import QComboBox, QLineEdit, QMessageBox
from PySide6.QtWidgets import QInputDialog
from silicon_manganese_inventory.ui.base_page import BasePage
from silicon_manganese_inventory.dao.base_dao import CustomerDAO, SupplierDAO


class CustomerPage(BasePage):
    def __init__(self, db):
        super().__init__(db, "客户/供应商管理")
        self.cust_dao = CustomerDAO(db)
        self.supplier_dao = SupplierDAO(db)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["客户", "供应商"])
        self.add_search_field("类型:", self.type_combo)
        self.add_search_button("搜索", self._do_search)
        self.add_header_button("+ 新增客户", self._add_customer, "#27ae60")
        self.add_header_button("+ 新增供应商", self._add_supplier, "#3498db")

        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        self.set_table_headers(["名称", "联系人", "电话", "地址", "备注"])

    def _on_type_changed(self, text):
        self.refresh()

    def _do_search(self):
        self.refresh()

    def refresh(self):
        if self.type_combo.currentText() == "供应商":
            rows = self.supplier_dao.list()
        else:
            rows = self.cust_dao.list()
        data = []
        for r in rows:
            data.append([
                r["name"], r["contact"] or "",
                r["phone"] or "", r["address"] or "",
                r["remark"] or "",
            ])
        self.populate_table(data)

    def _add_customer(self):
        name, ok = QInputDialog.getText(self, "新增客户", "客户名称:")
        if not ok or not name.strip():
            return
        try:
            self.cust_dao.create(name=name.strip())
        except ValueError as e:
            self.show_error(str(e))
            return
        self.refresh()

    def _add_supplier(self):
        name, ok = QInputDialog.getText(self, "新增供应商", "供应商名称:")
        if not ok or not name.strip():
            return
        try:
            self.supplier_dao.create(name=name.strip())
        except ValueError as e:
            self.show_error(str(e))
            return
        self.type_combo.setCurrentText("供应商")
        self.refresh()
