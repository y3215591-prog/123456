from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QMessageBox, QInputDialog, QMenu, QTableWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from silicon_manganese_inventory.ui.base_page import BasePage
from silicon_manganese_inventory.dao.base_dao import CustomerDAO, SupplierDAO
from silicon_manganese_inventory.services.excel_service import ExcelService


class CustomerPage(BasePage):
    def __init__(self, db):
        super().__init__(db, "客户/供应商管理")
        self.cust_dao = CustomerDAO(db)
        self.supplier_dao = SupplierDAO(db)
        self._archived = False

        self.type_combo = QComboBox()
        self.type_combo.addItems(["客户", "供应商"])
        self.add_search_field("类型:", self.type_combo)
        self.add_search_button("搜索", self._do_search)
        self.add_header_button("+ 新增客户", self._add_customer, "#27ae60")
        self.add_header_button("+ 新增供应商", self._add_supplier, "#3498db")
        self.add_header_button("导入 Excel", self._import_excel, "#8e44ad")
        self._archive_btn = self._make_header_button(
            "已完成客户", self._toggle_archived, "#e67e22")

        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_context_menu)
        self.set_table_headers(["ID", "代码", "名称", "联系人", "电话", "地址", "备注"])
        self._update_archive_btn_visible()
        self.refresh()

    def _on_type_changed(self, text):
        self._update_archive_btn_visible()
        self.refresh()

    def _update_archive_btn_visible(self):
        if self.type_combo.currentText() == "供应商":
            self._archive_btn.hide()
        else:
            self._archive_btn.show()
            self._archive_btn.setText("返回活跃客户" if self._archived else "已完成客户")

    def _toggle_archived(self):
        self._archived = not self._archived
        self._update_archive_btn_visible()
        self.refresh()

    def _do_search(self):
        self.refresh()

    def refresh(self):
        if self.type_combo.currentText() == "供应商":
            rows = self.supplier_dao.list()
        else:
            rows = self.cust_dao.list(archived_only=self._archived)
        data = []
        for r in rows:
            archived_mark = " [已归档]" if (r["is_archived"] or 0) else ""
            data.append([
                r["id"], r["code"] or "", r["name"] + archived_mark,
                r["contact_person"] or "", r["contact_phone"] or "",
                r["address"] or "", r["remark"] or "",
            ])
        self.populate_table(data)

    def _add_customer(self):
        name, ok = QInputDialog.getText(self, "新增客户", "客户名称:")
        if not ok or not name.strip():
            return
        try:
            self.cust_dao.create(name=name.strip())
        except Exception as e:
            self.show_error(str(e))
            return
        self.refresh()

    def _add_supplier(self):
        name, ok = QInputDialog.getText(self, "新增供应商", "供应商名称:")
        if not ok or not name.strip():
            return
        try:
            self.supplier_dao.create(name=name.strip())
        except Exception as e:
            self.show_error(str(e))
            return
        self.type_combo.setCurrentText("供应商")
        self.refresh()

    def _import_excel(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择销售订单 Excel", "", "Excel 文件 (*.xlsx *.xls)")
        if not file_path:
            return
        try:
            svc = ExcelService(self.db)
            cust_stats = svc.import_customers_from_sales_excel(file_path)
            order_stats = svc.import_sales_orders(file_path)
            msg = (f"导入完成:\n"
                   f"  新增客户: {cust_stats['imported']} 条\n"
                   f"  跳过(重复): {cust_stats['skipped']} 条\n"
                   f"  导入销售订单: {order_stats['imported_orders']} 条")
            QMessageBox.information(self, "导入结果", msg)
        except Exception as e:
            self.show_error(f"导入失败: {e}")
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

        if self.type_combo.currentText() == "客户":
            act_edit = menu.addAction("编辑")
            record = self.cust_dao.get(record_id)
            if record and not record["is_archived"]:
                act_archive = menu.addAction("归档")
            else:
                act_archive = menu.addAction("取消归档")
            act_delete = menu.addAction("删除")
        else:
            act_edit = menu.addAction("编辑")
            act_archive = None
            act_delete = menu.addAction("删除")

        action = menu.exec_(self.table.viewport().mapToGlobal(pos))
        if not action:
            return
        if action == act_edit:
            self._edit_record(record_id)
        elif action == act_delete:
            self._delete_record(record_id)
        elif act_archive and action == act_archive:
            self._toggle_record_archive(record_id)

    def _edit_record(self, record_id):
        try:
            if self.type_combo.currentText() == "客户":
                r = self.cust_dao.get(record_id)
                dao = self.cust_dao
            else:
                r = self.supplier_dao.get(record_id)
                dao = self.supplier_dao
            if not r:
                return

            name, ok = QInputDialog.getText(self, "编辑名称", "名称:", text=r["name"])
            if not ok or not name.strip():
                return
            contact = self._ask_optional("联系人", r["contact_person"] or "")
            phone = self._ask_optional("电话", r["contact_phone"] or "")
            addr = self._ask_optional("地址", r["address"] or "")
            remark = self._ask_optional("备注", r["remark"] or "")
            dao.update(record_id, name=name.strip(), contact_person=contact,
                       contact_phone=phone, address=addr, remark=remark)
        except Exception as e:
            self.show_error(f"编辑失败: {e}")
        self.refresh()

    def _delete_record(self, record_id):
        reply = QMessageBox.question(self, "确认删除", "确定要删除该记录吗?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        try:
            if self.type_combo.currentText() == "客户":
                self.cust_dao.delete(record_id)
            else:
                self.supplier_dao.delete(record_id)
        except Exception as e:
            self.show_error(str(e))
            return
        self.refresh()

    def _toggle_record_archive(self, record_id):
        r = self.cust_dao.get(record_id)
        if r["is_archived"]:
            self.cust_dao.unarchive(record_id)
        else:
            self.cust_dao.archive(record_id)
        self.refresh()

    def _ask_optional(self, label, default=""):
        text, ok = QInputDialog.getText(self, label, f"{label}:", text=default)
        return text.strip() if ok else default

    def _make_header_button(self, text, callback, color):
        from PySide6.QtWidgets import QPushButton
        btn = QPushButton(text)
        btn.setStyleSheet(f"""
            QPushButton {{ background-color: {color}; color: white; border: none;
                          padding: 6px 16px; border-radius: 4px; font-size: 13px; }}
            QPushButton:hover {{ opacity: 0.9; }}
        """)
        btn.clicked.connect(callback)
        self.header_buttons.addWidget(btn)
        return btn
