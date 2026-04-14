from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class CustomerClosetItem(Base):
    __tablename__ = "customer_closet_items"
    __table_args__ = (
        UniqueConstraint("email", "sku_id", name="uq_customer_closet_email_sku"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), index=True)

    sku_id: Mapped[str | None] = mapped_column(String(80), index=True, nullable=True)
    product_id: Mapped[str | None] = mapped_column(String(80), index=True, nullable=True)
    ref_id: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)

    name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    brand: Mapped[str | None] = mapped_column(String(255), nullable=True)

    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    product_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    purchase_count: Mapped[int] = mapped_column(Integer, default=0)
    total_quantity: Mapped[int] = mapped_column(Integer, default=0)
    total_spent: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    first_purchase_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_purchase_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)