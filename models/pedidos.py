from core.database import Base
from sqlalchemy import Column, DateTime, Float, Integer, String


class Pedidos(Base):
    __tablename__ = "pedidos"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    empresa_id = Column(Integer, nullable=False)
    cliente_id = Column(Integer, nullable=True)
    numero_pedido = Column(String, nullable=False)
    data_pedido = Column(DateTime(timezone=True), nullable=True)
    valor_total = Column(Float, nullable=True)
    status = Column(String, nullable=True)
    user_id = Column(String, nullable=False)