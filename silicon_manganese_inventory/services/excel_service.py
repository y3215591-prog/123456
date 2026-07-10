import os
import openpyxl
from silicon_manganese_inventory.dao.database import DatabaseManager
from silicon_manganese_inventory.dao.base_dao import (
    CustomerDAO, SalesOrderDAO, DailyShipmentDAO,
)


class ExcelService:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def import_sales_orders(self, file_path):
        wb = openpyxl.load_workbook(file_path, data_only=True)
        ws = wb.active
        headers = [str(c.value or "").strip() for c in ws[1]]
        customer_dao = CustomerDAO(self.db)
        order_dao = SalesOrderDAO(self.db)
        spec_dao = None
        from silicon_manganese_inventory.dao.base_dao import SpecDAO
        spec_dao = SpecDAO(self.db)

        stats = {"new_customers": 0, "updated_customers": 0,
                 "new_specs": 0, "imported_orders": 0, "skipped": 0}
        order_no_idx = self._find_col(headers, ["销售订单号", "order_no"])
        customer_code_idx = self._find_col(headers, ["客户", "客户代码", "customer_code"])
        customer_name_idx = self._find_col(headers, ["客户名称", "customer_name"])
        material_desc_idx = self._find_col(headers, ["物料描述", "material_desc"])

        if order_no_idx is None:
            raise ValueError("Excel 缺少销售订单号列")

        for row in ws.iter_rows(min_row=2, values_only=True):
            order_no = str(row[order_no_idx] or "").strip()
            if not order_no:
                stats["skipped"] += 1
                continue

            customer_code = str(row[customer_code_idx] or "").strip() if customer_code_idx is not None else ""
            customer_name = str(row[customer_name_idx] or "").strip() if customer_name_idx is not None else ""
            material_desc = str(row[material_desc_idx] or "").strip() if material_desc_idx is not None else ""

            if customer_code and customer_name:
                existing = customer_dao.get_by_code(customer_code)
                if existing:
                    if existing["name"] != customer_name:
                        customer_dao.update(existing["id"], name=customer_name)
                        stats["updated_customers"] += 1
                else:
                    customer_dao.create(code=customer_code, name=customer_name)
                    stats["new_customers"] += 1

            if material_desc and spec_dao:
                existing_spec = spec_dao.get_by_name(material_desc.split(",")[0].strip())
                if not existing_spec:
                    spec_dao.create(material_desc.split(",")[0].strip())
                    stats["new_specs"] += 1

            kwargs = {}
            for col_name, col_idx_map in [
                ("order_no", order_no_idx),
                ("line_no", self._find_col(headers, ["销售订单行号", "line_no"])),
                ("customer_code", customer_code_idx),
                ("customer_name", customer_name_idx),
                ("contract_ref", self._find_col(headers, ["合同参考", "contract_ref"])),
                ("contract_no", self._find_col(headers, ["销售合同号", "contract_no"])),
                ("material_code", self._find_col(headers, ["物料编码", "material_code"])),
                ("material_desc", material_desc_idx),
                ("delivery_start", self._find_col(headers, ["交货开始日期", "delivery_start"])),
                ("delivery_end", self._find_col(headers, ["交货截止日期", "delivery_end"])),
                ("delivery_address", self._find_col(headers, ["送货地址", "delivery_address"])),
                ("quantity", self._find_col(headers, ["数量", "quantity"])),
                ("unit", self._find_col(headers, ["单位", "unit"])),
                ("factory_code", self._find_col(headers, ["工厂", "工厂代码", "factory_code"])),
                ("factory_name", self._find_col(headers, ["工厂名称", "factory_name"])),
                ("pickup_method", self._find_col(headers, ["提货方式", "pickup_method"])),
            ]:
                idx = col_idx_map
                if idx is not None and idx < len(row):
                    val = row[idx]
                    if val is not None:
                        kwargs[col_name] = val

            existing_order = order_dao.get_by_order_no(order_no)
            if not existing_order:
                order_dao.create(**kwargs)
                stats["imported_orders"] += 1

        wb.close()
        return stats

    def import_daily_shipments(self, file_path):
        wb = openpyxl.load_workbook(file_path, data_only=True)
        ws = wb.active
        dao = DailyShipmentDAO(self.db)

        headers = []
        for cell in ws[1]:
            val = str(cell.value or "").strip()
            headers.append(val)

        stats = {"imported": 0, "skipped": 0}
        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if row[0] is None:
                stats["skipped"] += 1
                continue
            kwargs = {}
            col_map = {
                "seq_no": 0, "shipment_date": 1, "plate_no": 2,
                "customer_code": 3, "customer_name": 4,
                "sales_order_no": 5, "material_name": 6, "spec": 7,
                "batch_no": 8, "load_quantity": 9,
                "gross_weight": 10, "tare_weight": 11, "net_weight": 12,
                "customer_received_weight": 13, "remark": 14,
            }
            for key, idx in col_map.items():
                if idx < len(row) and row[idx] is not None:
                    kwargs[key] = row[idx]
            if kwargs.get("seq_no") is not None:
                dao.create(**kwargs)
                stats["imported"] += 1

        wb.close()
        return stats

    def _find_col(self, headers, names):
        for i, h in enumerate(headers):
            if h in names:
                return i
        return None

    def import_sales_orders_from_rows(self, rows):
        customer_dao = CustomerDAO(self.db)
        order_dao = SalesOrderDAO(self.db)
        from silicon_manganese_inventory.dao.base_dao import SpecDAO
        spec_dao = SpecDAO(self.db)

        if not rows:
            return {"new_customers": 0, "updated_customers": 0,
                    "new_specs": 0, "imported_orders": 0, "skipped": 0}

        headers = [str(c or "").strip() for c in rows[0]]
        stats = {"new_customers": 0, "updated_customers": 0,
                 "new_specs": 0, "imported_orders": 0, "skipped": 0}
        order_no_idx = self._find_col(headers, ["销售订单号", "order_no"])
        customer_code_idx = self._find_col(headers, ["客户", "客户代码", "customer_code"])
        customer_name_idx = self._find_col(headers, ["客户名称", "customer_name"])
        material_desc_idx = self._find_col(headers, ["物料描述", "material_desc"])

        if order_no_idx is None:
            raise ValueError("Excel 缺少销售订单号列")

        for row in rows[1:]:
            order_no = str(row[order_no_idx] or "").strip()
            if not order_no:
                stats["skipped"] += 1
                continue
            customer_code = str(row[customer_code_idx] or "").strip() if customer_code_idx is not None else ""
            customer_name = str(row[customer_name_idx] or "").strip() if customer_name_idx is not None else ""
            material_desc = str(row[material_desc_idx] or "").strip() if material_desc_idx is not None else ""

            if customer_code and customer_name:
                existing = customer_dao.get_by_code(customer_code)
                if existing:
                    if existing["name"] != customer_name:
                        customer_dao.update(existing["id"], name=customer_name)
                        stats["updated_customers"] += 1
                else:
                    customer_dao.create(code=customer_code, name=customer_name)
                    stats["new_customers"] += 1

            if material_desc and spec_dao:
                existing_spec = spec_dao.get_by_name(material_desc.split(",")[0].strip())
                if not existing_spec:
                    spec_dao.create(material_desc.split(",")[0].strip())
                    stats["new_specs"] += 1

            kwargs = {}
            for col_name, col_idx_map in [
                ("order_no", order_no_idx),
                ("line_no", self._find_col(headers, ["销售订单行号", "line_no"])),
                ("customer_code", customer_code_idx),
                ("customer_name", customer_name_idx),
                ("contract_ref", self._find_col(headers, ["合同参考", "contract_ref"])),
                ("contract_no", self._find_col(headers, ["销售合同号", "contract_no"])),
                ("material_code", self._find_col(headers, ["物料编码", "material_code"])),
                ("material_desc", material_desc_idx),
                ("delivery_start", self._find_col(headers, ["交货开始日期", "delivery_start"])),
                ("delivery_end", self._find_col(headers, ["交货截止日期", "delivery_end"])),
                ("delivery_address", self._find_col(headers, ["送货地址", "delivery_address"])),
                ("quantity", self._find_col(headers, ["数量", "quantity"])),
                ("unit", self._find_col(headers, ["单位", "unit"])),
                ("factory_code", self._find_col(headers, ["工厂", "工厂代码", "factory_code"])),
                ("factory_name", self._find_col(headers, ["工厂名称", "factory_name"])),
                ("pickup_method", self._find_col(headers, ["提货方式", "pickup_method"])),
            ]:
                idx = col_idx_map
                if idx is not None and idx < len(row):
                    val = row[idx]
                    if val is not None:
                        kwargs[col_name] = val

            existing_order = order_dao.get_by_order_no(order_no)
            if not existing_order:
                order_dao.create(**kwargs)
                stats["imported_orders"] += 1
        return stats

    def import_daily_shipments_from_rows(self, rows):
        dao = DailyShipmentDAO(self.db)
        if not rows:
            return {"imported": 0, "skipped": 0}
        stats = {"imported": 0, "skipped": 0}
        col_map = {
            "seq_no": 0, "shipment_date": 1, "plate_no": 2,
            "customer_code": 3, "customer_name": 4,
            "sales_order_no": 5, "material_name": 6, "spec": 7,
            "batch_no": 8, "load_quantity": 9,
            "gross_weight": 10, "tare_weight": 11, "net_weight": 12,
            "customer_received_weight": 13, "remark": 14,
        }
        for row in rows[1:]:
            if row[0] is None:
                stats["skipped"] += 1
                continue
            kwargs = {}
            for key, idx in col_map.items():
                if idx < len(row) and row[idx] is not None:
                    kwargs[key] = row[idx]
            if kwargs.get("seq_no") is not None:
                dao.create(**kwargs)
                stats["imported"] += 1
        return stats


class ExportService:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def export_inventory(self, file_path):
        from silicon_manganese_inventory.services.report_service import ReportService
        service = ReportService(self.db)
        rows = service.get_inventory_report()
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "成品库存"
        ws.append(["批次号", "库位", "结存(吨)", "最近入库日期", "化验结果", "铅封号明细"])
        for row in rows:
            ws.append([
                row["batch_no"], row["location_code"], row["balance"],
                row["last_inbound_date"], row["overall_result"] or "",
                row["seal_list"] or "",
            ])
        wb.save(file_path)

    def export_daily_shipments(self, file_path, **filters):
        dao = DailyShipmentDAO(self.db)
        rows = dao.list(**filters)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "每日发货明细"
        ws.append(["序号", "发货日期", "车牌", "客户代码", "客户名称",
                    "销售订单号", "物料名称", "规格", "批次号", "装车吨数",
                    "毛重", "皮重", "净重", "客户收货净重", "铅封号", "备注"])
        for row in rows:
            ws.append([
                row["seq_no"], row["shipment_date"], row["plate_no"],
                row["customer_code"], row["customer_name"],
                row["sales_order_no"], row["material_name"], row["spec"],
                row["batch_no"], row["load_quantity"],
                row["gross_weight"], row["tare_weight"], row["net_weight"],
                row["customer_received_weight"], row["seal_codes"], row["remark"],
            ])
        wb.save(file_path)

    def export_order_summary(self, file_path):
        from silicon_manganese_inventory.services.report_service import ReportService
        service = ReportService(self.db)
        rows = service.get_order_summary()
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "订单装车汇总"
        ws.append(["订单号", "客户代码", "客户名称", "物料名称", "规格", "单位",
                    "订单量", "交货截止日期", "已发量", "待发量", "完成率",
                    "提货方式", "发货进度"])
        for row in rows:
            ws.append([
                row["order_no"], row["customer_code"], row["customer_name"],
                row["material_name"], row["spec"], row["unit"],
                row["order_quantity"], row["delivery_end"],
                row["shipped_quantity"], row["pending_quantity"],
                row["completion_rate"], row["pickup_method"], row["warning"],
            ])
        wb.save(file_path)
