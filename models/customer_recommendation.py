from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class CustomerRecommendation(Base):
    __tablename__ = "customer_recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), index=True)

    sku_id: Mapped[str | None] = mapped_column(String(80), index=True, nullable=True)
    product_id: Mapped[str | None] = mapped_column(String(80), index=True, nullable=True)
    ref_id: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)

    name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)

    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    product_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)