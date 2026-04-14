from datetime import datetime

from sqlalchemy import JSON, DateTime, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class Order(Base):
    __tablename__ = "orders"

    order_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    sequence: Mapped[str | None] = mapped_column(String(80), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    status: Mapped[str | None] = mapped_column(String(120), nullable=True)
    creation_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    last_change: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    total_value: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)