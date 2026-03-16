from core.database import Base
from sqlalchemy import Boolean, Column, DateTime, Integer, String


class Recommendation_logs(Base):
    __tablename__ = "recommendation_logs"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    empresa_id = Column(Integer, nullable=False)
    cliente_id = Column(Integer, nullable=True)
    look_id = Column(Integer, nullable=True)
    produtos_recomendados = Column(String, nullable=True)
    ocasiao = Column(String, nullable=True)
    fonte = Column(String, nullable=True)
    clicado = Column(Boolean, nullable=True)
    aprovado_marca = Column(Boolean, nullable=True)
    feedback = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True)
    user_id = Column(String, nullable=False)