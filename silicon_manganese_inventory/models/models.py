from dataclasses import dataclass, fields
from datetime import date
from typing import Optional
from enum import Enum


class SealStatus(str, Enum):
    UNUSED = "unused"
    PRE_ALLOCATED = "pre_allocated"
    IN_STOCK = "in_stock"
    SHIPPED = "shipped"


class LabStatus(str, Enum):
    PENDING = "pending"
    TESTED = "tested"


class LocationStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


@dataclass
class SealBatch:
    id: Optional[int] = None
    name: str = ""
    start_code: str = ""
    end_code: str = ""
    total_count: int = 0
    used_count: int = 0
    import_date: str = ""

    @property
    def available(self) -> int:
        return self.total_count - self.used_count


@dataclass
class SealNumber:
    id: Optional[int] = None
    seal_code: str = ""
    seal_batch_id: int = 0
    status: SealStatus = SealStatus.UNUSED
    pre_inbound_id: Optional[int] = None
    inbound_id: Optional[int] = None
    outbound_id: Optional[int] = None
    batch_no: str = ""
    location_code: str = ""
    batch_code: str = ""
    pre_inbound_order: str = ""
    inbound_order: str = ""
    outbound_order: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass
class Spec:
    id: Optional[int] = None
    name: str = ""
    mn_content: float = 0.0
    si_content: float = 0.0
    remark: str = ""


@dataclass
class Warehouse:
    id: Optional[int] = None
    name: str = ""
    address: str = ""
    remark: str = ""
    is_active: bool = True


@dataclass
class Location:
    id: Optional[int] = None
    code: str = ""
    name: str = ""
    warehouse_id: int = 1
    warehouse_name: str = ""
    status: str = "active"
    used_qty: float = 0.0
    remark: str = ""


@dataclass
class Customer:
    id: Optional[int] = None
    code: str = ""
    name: str = ""
    contact_person: str = ""
    contact_phone: str = ""
    address: str = ""
    remark: str = ""


@dataclass
class Supplier:
    id: Optional[int] = None
    code: str = ""
    name: str = ""
    contact_person: str = ""
    contact_phone: str = ""
    address: str = ""
    remark: str = ""


@dataclass
class PreInboundOrder:
    id: Optional[int] = None
    order_no: str = ""
    date: str = ""
    batch_no: str = ""
    spec_id: Optional[int] = None
    quantity: float = 0.0
    location_code: str = ""
    seal_batch_id: Optional[int] = None
    seal_start: str = ""
    seal_end: str = ""
    lab_status: LabStatus = LabStatus.PENDING
    lab_id: Optional[int] = None
    operator: str = ""
    remark: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass
class InboundOrder:
    id: Optional[int] = None
    order_no: str = ""
    pre_inbound_id: int = 0
    date: str = ""
    batch_no: str = ""
    spec_id: Optional[int] = None
    quantity: float = 0.0
    location_code: str = ""
    operator: str = ""
    remark: str = ""
    created_at: str = ""


@dataclass
class OutboundOrder:
    id: Optional[int] = None
    order_no: str = ""
    date: str = ""
    customer_id: Optional[int] = None
    customer_name: str = ""
    sales_order_no: str = ""
    contract_no: str = ""
    plate_no: str = ""
    spec_id: Optional[int] = None
    spec_name: str = ""
    quantity: float = 0.0
    batch_nos: str = ""
    seal_start: str = ""
    seal_end: str = ""
    operator: str = ""
    remark: str = ""
    created_at: str = ""


@dataclass
class LabResult:
    id: Optional[int] = None
    pre_inbound_id: int = 0
    mn_content: Optional[float] = None
    si_content: Optional[float] = None
    c_content: Optional[float] = None
    s_content: Optional[float] = None
    p_content: Optional[float] = None
    mn_result: str = ""
    si_result: str = ""
    c_result: str = ""
    s_result: str = ""
    p_result: str = ""
    overall_result: str = ""
    test_date: str = ""
    remark: str = ""


@dataclass
class LabStandard:
    id: Optional[int] = None
    element: str = ""
    min_value: float = 0.0
    max_value: float = 0.0
    remark: str = ""


@dataclass
class SalesOrder:
    id: Optional[int] = None
    order_no: str = ""
    line_no: str = ""
    customer_code: str = ""
    customer_name: str = ""
    contract_no: str = ""
    material_desc: str = ""
    quantity: float = 0.0
    unit: str = "吨"
    delivery_start: str = ""
    delivery_end: str = ""
    pickup_method: str = ""
    factory_code: str = ""
    factory_name: str = ""


@dataclass
class DailyShipment:
    id: Optional[int] = None
    seq_no: int = 0
    shipment_date: str = ""
    plate_no: str = ""
    customer_code: str = ""
    customer_name: str = ""
    sales_order_no: str = ""
    material_name: str = ""
    spec: str = ""
    batch_no: str = ""
    load_quantity: float = 0.0
    gross_weight: float = 0.0
    tare_weight: float = 0.0
    net_weight: float = 0.0
    customer_received_weight: Optional[float] = None
    seal_codes: str = ""
    remark: str = ""
    outbound_id: Optional[int] = None


@dataclass
class InventoryRow:
    batch_no: str = ""
    location_code: str = ""
    balance: float = 0.0
    last_inbound_date: str = ""
    overall_result: str = ""
    seal_list: str = ""


@dataclass
class OrderSummaryRow:
    order_no: str = ""
    customer_code: str = ""
    customer_name: str = ""
    material_name: str = ""
    spec: str = ""
    unit: str = "吨"
    order_quantity: float = 0.0
    delivery_end: str = ""
    shipped_quantity: float = 0.0
    pending_quantity: float = 0.0
    completion_rate: float = 0.0
    pickup_method: str = ""
    warning: str = ""


def row_to_dataclass(cls, row):
    if row is None:
        return None
    row_dict = dict(row) if not isinstance(row, dict) else row
    field_names = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in row_dict.items() if k in field_names})
