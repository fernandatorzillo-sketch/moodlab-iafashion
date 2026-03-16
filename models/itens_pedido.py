from core.database import Base
from sqlalchemy import Column, Float, Integer, String


class Itens_pedido(Base):
    __tablename__ = "itens_pedido"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    pedido_id = Column(Integer, nullable=False)
    produto_id = Column(Integer, nullable=False)
    sku = Column(String, nullable=True)
    quantidade = Column(Integer, nullable=True)
    preco_unitario = Column(Float, nullable=True)
    tamanho = Column(String, nullable=True)
    user_id = Column(String, nullable=False)