from core.database import Base
from sqlalchemy import Boolean, Column, Integer, String


class Curated_look_items(Base):
    __tablename__ = "curated_look_items"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    look_id = Column(Integer, nullable=False)
    produto_id = Column(Integer, nullable=False)
    ordem = Column(Integer, nullable=True)
    obrigatorio = Column(Boolean, nullable=True)
    user_id = Column(String, nullable=False)