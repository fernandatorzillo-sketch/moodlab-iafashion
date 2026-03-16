from core.database import Base
from sqlalchemy import Column, DateTime, Integer, String


class Outfit_recommendations(Base):
    __tablename__ = "outfit_recommendations"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    user_id = Column(String, nullable=False)
    occasion = Column(String, nullable=False)
    recommendation = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True)