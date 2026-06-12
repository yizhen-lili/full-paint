import uuid
from enum import StrEnum

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    Column,
    Date,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from core.database import Base


class OrderStatusEnum(StrEnum):
    pending_payment = "pending_payment"
    payment_expired = "payment_expired"
    paid = "paid"
    processing = "processing"
    shipped = "shipped"
    completed = "completed"
    cancelled = "cancelled"
    refund_processing = "refund_processing"
    refunded = "refunded"
    partially_refunded = "partially_refunded"


class DiscountSourceEnum(StrEnum):
    coupon = "coupon"
    auto_checkout = "auto_checkout"


class ShippingTypeEnum(StrEnum):
    home = "home"
    seven_eleven = "seven_eleven"
    family_mart = "family_mart"


class ShippingPreferenceEnum(StrEnum):
    together = "together"
    separate = "separate"


class CancelReasonCodeEnum(StrEnum):
    payment_expired = "payment_expired"
    customer_cancelled = "customer_cancelled"
    admin_cancelled = "admin_cancelled"


class ShipmentTypeEnum(StrEnum):
    fulfilled = "fulfilled"
    preorder = "preorder"


class ShipmentStatusEnum(StrEnum):
    pending = "pending"
    shipped = "shipped"
    delivered = "delivered"


class ProductionProgressStatusEnum(StrEnum):
    pending = "pending"
    in_production = "in_production"
    manufacturing = "manufacturing"
    packaging = "packaging"
    ready_to_ship = "ready_to_ship"
    shipped = "shipped"


class PaymentMethodEnum(StrEnum):
    bank_transfer = "bank_transfer"   # 手動網銀匯款（既有流程，admin 人工確認）
    ecpay = "ecpay"                   # ECpay 線上付款（AioCheckOut，webhook 自動確認）


class PaymentTransactionStatusEnum(StrEnum):
    created = "created"               # AioCheckOut 參數已產生、尚未收到任何回傳
    awaiting_atm = "awaiting_atm"     # ATM/超商已取號，等顧客繳費
    paid = "paid"                     # ReturnURL RtnCode=1，付款成功
    failed = "failed"                 # ReturnURL RtnCode!=1（信用卡拒絕等）
    expired = "expired"              # 取號後逾期未付（隨訂單逾期一起標記）


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    # 一般商品（產品變體）— 跟 custom_request_id 二選一
    product_variant_id = Column(
        UUID(as_uuid=True), ForeignKey("product_variants.id"), nullable=True
    )
    # 客製申請 — quote 確認後加進來；綁定 quoted_production_job_id 的版本
    custom_request_id = Column(
        UUID(as_uuid=True), ForeignKey("custom_requests.id"), nullable=True
    )
    production_job_id = Column(
        UUID(as_uuid=True), ForeignKey("production_jobs.id"), nullable=True
    )
    quantity = Column(Integer, nullable=False, default=1)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class Order(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_number = Column(String, nullable=False, unique=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status = Column(
        Enum(OrderStatusEnum, name="orderstatusenum"),
        nullable=False,
        default=OrderStatusEnum.pending_payment,
    )
    subtotal = Column(Numeric(10, 2), nullable=False)
    discount_amount = Column(Numeric(10, 2), nullable=False, default=0)
    discount_source = Column(
        Enum(DiscountSourceEnum, name="discountsourceenum"), nullable=True
    )
    auto_checkout_config_id = Column(
        UUID(as_uuid=True), ForeignKey("coupon_configs.id"), nullable=True
    )
    shipping_fee = Column(Numeric(10, 2), nullable=False, default=0)
    total = Column(Numeric(10, 2), nullable=False)
    user_coupon_id = Column(UUID(as_uuid=True), ForeignKey("user_coupons.id"), nullable=True)
    shipping_type = Column(
        Enum(ShippingTypeEnum, name="shippingtypeenum"), nullable=False
    )
    shipping_preference = Column(
        Enum(ShippingPreferenceEnum, name="shippingpreferenceenum"), nullable=True
    )
    shipping_snapshot = Column(JSONB, nullable=False)
    # 出貨資訊鎖定：admin 確認後才能建物流單；建單後永久鎖死
    shipping_locked = Column(Boolean, nullable=False, default=False, server_default="false")
    # 付款方式：bank_transfer（手動匯款）或 ecpay（線上付款）。既有訂單預設 bank_transfer。
    payment_method = Column(
        Enum(PaymentMethodEnum, name="paymentmethodenum"),
        nullable=False,
        default=PaymentMethodEnum.bank_transfer,
        server_default=PaymentMethodEnum.bank_transfer.value,
    )
    payment_deadline = Column(TIMESTAMP(timezone=True), nullable=True)
    paid_at = Column(TIMESTAMP(timezone=True), nullable=True)
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    cancel_reason_code = Column(
        Enum(CancelReasonCodeEnum, name="cancelreasoncodeenum"), nullable=True
    )
    cancel_reason_note = Column(Text, nullable=True)
    refund_amount = Column(Numeric(10, 2), nullable=True)
    refunded_at = Column(TIMESTAMP(timezone=True), nullable=True)
    refund_confirmed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    customer_notes = Column(Text, nullable=True)
    admin_notes = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(
        UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False
    )
    product_variant_id = Column(
        UUID(as_uuid=True), ForeignKey("product_variants.id"), nullable=True
    )
    custom_request_id = Column(
        UUID(as_uuid=True), ForeignKey("custom_requests.id"), nullable=True
    )
    production_job_id = Column(
        UUID(as_uuid=True), ForeignKey("production_jobs.id"), nullable=True
    )
    product_title_snapshot = Column(String, nullable=False)
    variant_spec_snapshot = Column(JSONB, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    quantity = Column(Integer, nullable=False)
    fulfilled_qty = Column(Integer, nullable=False, default=0)
    preorder_qty = Column(Integer, nullable=False, default=0)
    is_returned = Column(Boolean, nullable=False, default=False)


class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    shipment_type = Column(
        Enum(ShipmentTypeEnum, name="shipmenttypeenum"), nullable=False
    )
    status = Column(
        Enum(ShipmentStatusEnum, name="shipmentstatusenum"),
        nullable=False,
        default=ShipmentStatusEnum.pending,
    )
    tracking_number = Column(String, nullable=True)
    ecpay_logistics_id = Column(String, nullable=True)
    # CVS C2C 寄件用：用戶到 7-11 ibon / 全家 FamiPort 機台輸入這兩個值才能印貼紙
    cvs_payment_no = Column(String, nullable=True)       # 寄貨編號（CVSPaymentNo）
    # 驗證碼（CVSValidationNo，僅 7-Eleven C2C 有）
    cvs_validation_no = Column(String, nullable=True)
    # ECpay webhook 推送的最新狀態（Day 3 追蹤）
    # 最後收到的 RtnCode (e.g. 2067 = 客戶已取貨)
    last_rtn_code = Column(Integer, nullable=True)
    last_rtn_msg = Column(String, nullable=True)                # 最後狀態說明（中文）
    last_status_at = Column(TIMESTAMP(timezone=True), nullable=True)  # ECpay UpdateStatusDate
    shipped_at = Column(TIMESTAMP(timezone=True), nullable=True)
    delivered_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class ProductionProgress(Base):
    __tablename__ = "production_progress"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_item_id = Column(
        UUID(as_uuid=True), ForeignKey("order_items.id"), nullable=False
    )
    status = Column(
        Enum(ProductionProgressStatusEnum, name="productionprogressstatusenum"),
        nullable=False,
        default=ProductionProgressStatusEnum.pending,
    )
    notes = Column(Text, nullable=True)
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class PaymentSubmission(Base):
    __tablename__ = "payment_submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    is_flagged = Column(Boolean, nullable=False, default=False)
    transfer_amount = Column(Numeric(10, 2), nullable=False)
    transfer_date = Column(Date, nullable=False)
    transfer_time = Column(Time, nullable=False)
    account_last5 = Column(String(5), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class PaymentTransaction(Base):
    """ECpay 線上付款的每筆交易紀錄。

    一張訂單可有多筆（顧客重試 / ATM 取號後又改信用卡）。merchant_trade_no 是
    我方送 ECpay 的唯一單號，也是 webhook lookup / idempotency 的主鍵。
    amount 為發起時 order.total 快照，webhook 回傳時比對防金額竄改。
    """
    __tablename__ = "payment_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False, index=True)
    merchant_trade_no = Column(String, nullable=False, unique=True)
    status = Column(
        Enum(PaymentTransactionStatusEnum, name="paymenttransactionstatusenum"),
        nullable=False,
        default=PaymentTransactionStatusEnum.created,
    )
    amount = Column(Numeric(10, 2), nullable=False)
    ecpay_trade_no = Column(String, nullable=True)        # ECpay 端交易號（TradeNo）
    # 實際付款方式（Credit_CreditCard / ATM_TAISHIN ...）
    payment_type = Column(String, nullable=True)
    # ATM / 超商取號資訊（PaymentInfoURL 回傳）
    bank_code = Column(String, nullable=True)             # ATM 虛擬帳號銀行代碼
    vaccount = Column(String, nullable=True)              # ATM 虛擬帳號
    payment_no = Column(String, nullable=True)            # 超商繳費代碼
    expire_date = Column(TIMESTAMP(timezone=True), nullable=True)  # 取號繳費期限
    # webhook 軌跡
    last_rtn_code = Column(Integer, nullable=True)
    last_rtn_msg = Column(String, nullable=True)
    raw_callback = Column(JSONB, nullable=True)           # 最後一次 webhook 全文（稽核）
    paid_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
