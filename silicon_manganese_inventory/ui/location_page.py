from PySide6.QtWidgets import QComboBox, QLabel
from PySide6.QtWidgets import QInputDialog
from silicon_manganese_inventory.ui.base_page import BasePage
from silicon_manganese_inventory.dao.base_dao import LocationDAO


class LocationPage(BasePage):
    def __init__(self, db):
        super().__init__(db, "库位管理")
        self.loc_dao = LocationDAO(db)

        self.type_combo = QComboBox()
        self.type_combo.addItem("全部", None)
        self.type_combo.addItem("自然块库位(Z*)", "Z")
        self.type_combo.addItem("成品库位(A*)", "A")
        self.add_search_field("类型:", self.type_combo)
        self.add_search_button("搜索", self._do_search)
        self.add_header_button("+ 新增库位", self._add_location, "#27ae60")
        self.set_table_headers([
            "库位编码", "库位名称", "类型", "库存铅封(个)",
        ])

        self.total_label = QLabel("库位总数: 0")
        self.total_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #2c3e50;")
        self.status_layout.addWidget(self.total_label)

    def _do_search(self):
        self.refresh()

    def refresh(self):
        prefix = self.type_combo.currentData()
        locations = self.loc_dao.list(code_prefix=prefix)
        total_count = 0
        total_stock = 0
        data = []
        for loc in locations:
            stock = self.loc_dao.get_available_qty(loc["code"])
            loc_type = "自然块" if loc["code"].startswith("Z") else "成品"
            data.append([
                l["code"], l["name"] or "", loc_type, stock,
            ])
            total_count += 1
            total_stock += stock
        self.total_label.setText(
            f"库位总数: {total_count} | 在库铅封: {total_stock} 个")
        self.populate_table(data)

    def _add_location(self):
        code, ok = QInputDialog.getText(self, "新增库位", "库位编码:")
        if not ok or not code:
            return
        name, ok2 = QInputDialog.getText(self, "新增库位", "库位名称:")
        if not ok2:
            return
        try:
            self.loc_dao.create(code=code, name=name)
        except ValueError as e:
            self.show_error(str(e))
            return
        self.refresh()
