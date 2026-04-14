from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class CustomerQuestionnaireAnswer(Base):
    __tablename__ = "customer_questionnaire_answers"

    email: Mapped[str] = mapped_column(String(255), primary_key=True)
    occasion: Mapped[str | None] = mapped_column(String(120), nullable=True)
    goal: Mapped[str | None] = mapped_column(String(120), nullable=True)
    style: Mapped[str | None] = mapped_column(String(120), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)