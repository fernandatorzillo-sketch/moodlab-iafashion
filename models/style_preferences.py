from core.database import Base
from sqlalchemy import Column, DateTime, Integer, String


class Style_preferences(Base):
    __tablename__ = "style_preferences"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    user_id = Column(String, nullable=False)
    preferred_colors = Column(String, nullable=True)
    preferred_styles = Column(String, nullable=True)
    preferred_occasions = Column(String, nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)