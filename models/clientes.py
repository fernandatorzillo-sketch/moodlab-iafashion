from core.database import Base
from sqlalchemy import Column, DateTime, Integer, String


class Clientes(Base):
    __tablename__ = "clientes"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    empresa_id = Column(Integer, nullable=False)
    nome = Column(String, nullable=False)
    email = Column(String, nullable=True)
    telefone = Column(String, nullable=True)
    genero = Column(String, nullable=True)
    cidade = Column(String, nullable=True)
    estado = Column(String, nullable=True)
    data_cadastro = Column(DateTime(timezone=True), nullable=True)
    estilo_resumo = Column(String, nullable=True)
    tamanho_top = Column(String, nullable=True)
    tamanho_bottom = Column(String, nullable=True)
    tamanho_dress = Column(String, nullable=True)
    user_id = Column(String, nullable=False)