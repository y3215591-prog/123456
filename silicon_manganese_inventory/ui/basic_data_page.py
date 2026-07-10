from PySide6.QtWidgets import QComboBox, QInputDialog, QMessageBox, QMenu
from PySide6.QtCore import Qt
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
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        self.add_search_field("数据类型:", self.type_combo)

        self.add_header_button("+ 新增", self._add_item, "#27ae60")

        self.type_combo.addItems(["品名规格", "检验标准", "仓库"])
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_context_menu)

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
            min_val, ok2 = QInputDialog.getDouble(self, "最小值", f"{element} 最小值:", 0, 0, 999, 5)
            if not ok2:
                return
            max_val, ok3 = QInputDialog.getDouble(self, "最大值", f"{element} 最大值:", 100, 0, 999, 5)
            if not ok3:
                return
            self.lab_dao.update_standard(element.strip(), min_val, max_val)
        elif text == "仓库":
            name, ok = QInputDialog.getText(self, "新增仓库", "仓库名称:")
            if ok and name.strip():
                self.warehouse_dao.create(name=name.strip())
        self.refresh()

    def _on_context_menu(self, pos):
        index = self.table.indexAt(pos)
        if not index.isValid():
            return
        row = index.row()
        item = self.table.item(row, 0)
        if not item:
            return
        record_id = int(item.text())
        menu = QMenu(self)
        act_edit = menu.addAction("编辑")
        act_delete = menu.addAction("删除")
        action = menu.exec_(self.table.viewport().mapToGlobal(pos))
        if action == act_edit:
            self._edit_item(record_id, row)
        elif action == act_delete:
            self._delete_item(record_id)

    def _edit_item(self, record_id, row):
        text = self.type_combo.currentText()
        if text == "品名规格":
            r = self.spec_dao.get(record_id)
            name, ok = QInputDialog.getText(self, "编辑品名规格", "规格名称:", text=r["name"])
            if ok and name.strip():
                remark, _ = QInputDialog.getText(self, "编辑备注", "备注:", text=r["remark"] or "")
                self.spec_dao.update(record_id, name=name.strip(), remark=remark)
        elif text == "检验标准":
            element = self.table.item(row, 1).text()
            min_val = float(self.table.item(row, 2).text())
            max_val = float(self.table.item(row, 3).text())
            new_min, ok2 = QInputDialog.getDouble(self, "编辑最小值", f"{element} 最小值:", min_val, 0, 999, 5)
            if not ok2:
                return
            new_max, ok3 = QInputDialog.getDouble(self, "编辑最大值", f"{element} 最大值:", max_val, 0, 999, 5)
            if not ok3:
                return
            self.lab_dao.update_standard(element, new_min, new_max)
        elif text == "仓库":
            r = self.warehouse_dao.list()
            r = next((x for x in r if x["id"] == record_id), None)
            if not r:
                return
            name, ok = QInputDialog.getText(self, "编辑仓库", "仓库名称:", text=r["name"])
            if ok and name.strip():
                addr, _ = QInputDialog.getText(self, "编辑地址", "地址:", text=r["address"] or "")
                remark, _ = QInputDialog.getText(self, "编辑备注", "备注:", text=r["remark"] or "")
                self.warehouse_dao.update(record_id, name=name.strip(), address=addr, remark=remark)
        self.refresh()

    def _delete_item(self, record_id):
        reply = QMessageBox.question(self, "确认删除", "确定要删除该记录吗?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        try:
            text = self.type_combo.currentText()
            if text == "品名规格":
                self.spec_dao.delete(record_id)
            elif text == "检验标准":
                self.lab_dao.delete_standard(record_id)
            elif text == "仓库":
                self.warehouse_dao.delete(record_id)
        except Exception as e:
            self.show_error(str(e))
            return
        self.refresh()
