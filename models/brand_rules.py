from core.database import Base
from sqlalchemy import Boolean, Column, Integer, String


class Brand_rules(Base):
    __tablename__ = "brand_rules"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    empresa_id = Column(Integer, nullable=False)
    rule_type = Column(String, nullable=False)
    rule_value = Column(String, nullable=True)
    descricao = Column(String, nullable=True)
    ativo = Column(Boolean, nullable=True)
    prioridade = Column(Integer, nullable=True)
    user_id = Column(String, nullable=False)