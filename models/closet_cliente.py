from core.database import Base
from sqlalchemy import Column, DateTime, Integer, String


class Closet_cliente(Base):
    __tablename__ = "closet_cliente"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    empresa_id = Column(Integer, nullable=False)
    cliente_id = Column(Integer, nullable=False)
    produto_id = Column(Integer, nullable=False)
    origem = Column(String, nullable=True)
    data_entrada = Column(DateTime(timezone=True), nullable=True)
    user_id = Column(String, nullable=False)