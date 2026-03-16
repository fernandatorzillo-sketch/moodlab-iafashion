from core.database import Base
from sqlalchemy import Boolean, Column, DateTime, Integer, String


class Curated_looks(Base):
    __tablename__ = "curated_looks"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    empresa_id = Column(Integer, nullable=False)
    nome = Column(String, nullable=False)
    ocasiao = Column(String, nullable=True)
    estilo = Column(String, nullable=True)
    descricao_editorial = Column(String, nullable=True)
    observacoes_marca = Column(String, nullable=True)
    tags = Column(String, nullable=True)
    prioridade = Column(Integer, nullable=True)
    ativo = Column(Boolean, nullable=True)
    tipo = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True)
    user_id = Column(String, nullable=False)