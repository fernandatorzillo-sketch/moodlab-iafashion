from core.database import Base
from sqlalchemy import Column, DateTime, Integer, String


class Empresas(Base):
    __tablename__ = "empresas"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    nome_empresa = Column(String, nullable=False)
    email_admin = Column(String, nullable=False)
    plataforma_ecommerce = Column(String, nullable=True)
    erp = Column(String, nullable=True)
    crm = Column(String, nullable=True)
    user_id = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=True)