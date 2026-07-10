from PySide6.QtWidgets import QLineEdit, QMessageBox
from PySide6.QtWidgets import QInputDialog
from silicon_manganese_inventory.ui.base_page import BasePage
from silicon_manganese_inventory.dao.base_dao import LocationDAO


class LocationPage(BasePage):
    def __init__(self, db):
        super().__init__(db, "库位管理")
        self.loc_dao = LocationDAO(db)

        self.add_header_button("+ 新增库位", self._add_location, "#27ae60")
        self.set_table_headers(["库位编码", "库位名称", "所属仓库", "已用(吨)", "状态"])

    def refresh(self):
        locations = self.loc_dao.list()
        data = []
        for l in locations:
            data.append([
                l["code"], l["name"] or "", l.get("warehouse_name", "") or "",
                l.get("used_qty", 0) or 0,
                "启用" if l.get("status") == "active" else "停用",
            ])
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
