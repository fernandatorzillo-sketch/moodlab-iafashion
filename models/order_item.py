from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.order_id"), index=True)
    email: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)

    sku_id: Mapped[str | None] = mapped_column(String(80), index=True, nullable=True)
    product_id: Mapped[str | None] = mapped_column(String(80), index=True, nullable=True)
    ref_id: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)

    name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    brand: Mapped[str | None] = mapped_column(String(255), nullable=True)

    quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    total_value: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)

    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    product_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at_order: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    raw_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)