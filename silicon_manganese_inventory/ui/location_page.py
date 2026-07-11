from PySide6.QtWidgets import (
    QComboBox, QLabel, QInputDialog, QMessageBox, QMenu, QHeaderView,
)
from PySide6.QtCore import Qt
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
        self.type_combo.currentTextChanged.connect(lambda: self._do_search())

        self.status_combo = QComboBox()
        self.status_combo.addItem("仅活跃", True)
        self.status_combo.addItem("全部(含停用)", False)
        self.add_search_field("状态:", self.status_combo, persist=False)
        self.status_combo.currentTextChanged.connect(lambda: self._do_search())

        self.add_search_button("搜索", self._do_search)
        self.add_header_button("+ 新增库位", self._add_location, "#16A34A")
        self.set_table_headers([
            "库位编码", "库位名称", "类型", "库存铅封(个)", "状态", "备注",
        ])

        self.total_label = QLabel("库位总数: 0")
        self.total_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #374151;")
        self.status_layout.addWidget(self.total_label)

        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

    def _do_search(self):
        self.refresh()

    def refresh(self):
        prefix = self.type_combo.currentData()
        active_only = self.status_combo.currentData()
        locations = self.loc_dao.list(code_prefix=prefix, active_only=active_only)
        total_count = 0
        total_stock = 0
        data = []
        for loc in locations:
            stock = self.loc_dao.get_available_qty(loc["code"])
            loc_type = "自然块" if loc["code"].startswith("Z") else "成品"
            status = "停用" if loc["status"] == "inactive" else "活跃"
            data.append([
                loc["code"], loc["name"] or "", loc_type, stock,
                status, loc["remark"] or "",
            ])
            total_count += 1
            total_stock += stock
        self.total_label.setText(
            f"库位总数: {total_count} | 在库铅封: {total_stock} 个")
        self.populate_table(data)

    def _add_location(self):
        from silicon_manganese_inventory.ui.dialogs.base_eas_dialog import BaseEasDialog
        from PySide6.QtWidgets import QLineEdit, QTextEdit
        from PySide6.QtCore import Qt as Qtc

        class AddLocationDialog(BaseEasDialog):
            def __init__(self, parent=None, edit_data=None):
                self.edit_data = edit_data
                is_edit = edit_data is not None
                super().__init__(
                    title="编辑库位" if is_edit else "新增库位",
                    width=400, height=280, parent=parent)
                card, cl = self.add_card()
                self.code_input = QLineEdit()
                if is_edit:
                    self.code_input.setText(edit_data.get("code", ""))
                else:
                    self.code_input.setPlaceholderText("如 A12 或 Z25")
                self.style_input(self.code_input)
                self.add_form_row("编码 *", self.code_input, cl)

                self.name_input = QLineEdit()
                if is_edit:
                    self.name_input.setText(edit_data.get("name", ""))
                self.name_input.setPlaceholderText("库位名称")
                self.style_input(self.name_input)
                self.add_form_row("名称", self.name_input, cl)

                self.remark_input = QTextEdit()
                self.remark_input.setMaximumHeight(60)
                if is_edit:
                    self.remark_input.setText(edit_data.get("remark", ""))
                self.remark_input.setPlaceholderText("备注")
                self.style_textarea(self.remark_input)
                self.add_form_row("备注", self.remark_input, cl)

                self.add_primary_button("保存", self.accept)
                self.add_cancel_button()

            def get_values(self):
                return {
                    "code": self.code_input.text().strip(),
                    "name": self.name_input.text().strip(),
                    "remark": self.remark_input.toPlainText().strip(),
                }

        dlg = AddLocationDialog(self)
        if dlg.exec() == dlg.Accepted:
            vals = dlg.get_values()
            if not vals["code"]:
                self.show_error("库位编码不能为空")
                return
            try:
                self.loc_dao.create(
                    code=vals["code"], name=vals["name"], remark=vals["remark"])
            except Exception as e:
                self.show_error(str(e))
                return
            self.refresh()

    def _edit_location(self, loc_id):
        loc = self.loc_dao.get(loc_id)
        if not loc:
            return
        from silicon_manganese_inventory.ui.dialogs.base_eas_dialog import BaseEasDialog
        from PySide6.QtWidgets import QLineEdit, QTextEdit

        class EditLocationDialog(BaseEasDialog):
            def __init__(self, edit_data, parent=None):
                self.edit_data = edit_data
                super().__init__(
                    title="编辑库位", width=400, height=280, parent=parent)
                card, cl = self.add_card()
                self.code_input = QLineEdit(edit_data["code"])
                self.style_input(self.code_input)
                self.add_form_row("编码", self.code_input, cl)

                self.name_input = QLineEdit(edit_data.get("name", ""))
                self.style_input(self.name_input)
                self.add_form_row("名称", self.name_input, cl)

                self.remark_input = QTextEdit()
                self.remark_input.setMaximumHeight(60)
                self.remark_input.setText(edit_data.get("remark", ""))
                self.style_textarea(self.remark_input)
                self.add_form_row("备注", self.remark_input, cl)

                self.add_primary_button("保存", self.accept)
                self.add_cancel_button()

            def get_values(self):
                return {
                    "name": self.name_input.text().strip(),
                    "remark": self.remark_input.toPlainText().strip(),
                }

        dlg = EditLocationDialog(dict(loc), self)
        if dlg.exec() == dlg.Accepted:
            vals = dlg.get_values()
            try:
                self.loc_dao.update(loc_id, name=vals["name"], remark=vals["remark"])
            except Exception as e:
                self.show_error(str(e))
                return
            self.refresh()

    def _toggle_active(self, loc_id, current_status):
        new_active = current_status == "inactive"
        label = "激活" if new_active else "停用"
        reply = QMessageBox.question(
            self, f"确认{label}库位",
            f"确定要{label}该库位吗？" + ("\n停用后将在列表中自动隐藏。" if not new_active else ""),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.loc_dao.toggle_active(loc_id, new_active)
            self.refresh()

    def _delete_location(self, loc_id, code):
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除库位 \"{code}\" 吗？\n（仅可删除无关联记录的空库位）",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                self.loc_dao.delete(loc_id)
            except ValueError as e:
                self.show_error(str(e))
                return
            self.refresh()

    def _show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item:
            return
        row = item.row()
        code_item = self.table.item(row, 0)
        status_item = self.table.item(row, 4)
        if not code_item:
            return

        code = code_item.text()
        current_status = status_item.text() if status_item else "活跃"

        loc = self.loc_dao.get_by_code(code)
        if not loc:
            return

        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background: white; border: 1px solid #E2E8F0; }")

        edit_action = menu.addAction("编辑")
        edit_action.triggered.connect(lambda: self._edit_location(loc["id"]))

        if current_status == "活跃":
            toggle_action = menu.addAction("停用")
            toggle_action.triggered.connect(
                lambda: self._toggle_active(loc["id"], "active"))
        else:
            toggle_action = menu.addAction("激活")
            toggle_action.triggered.connect(
                lambda: self._toggle_active(loc["id"], "inactive"))

        delete_action = menu.addAction("删除")
        delete_action.triggered.connect(
            lambda: self._delete_location(loc["id"], code))

        menu.exec(self.table.mapToGlobal(pos))
