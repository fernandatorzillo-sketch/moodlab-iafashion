from core.database import Base
from sqlalchemy import Boolean, Column, Float, Integer, String


class Produtos_empresa(Base):
    __tablename__ = "produtos_empresa"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    empresa_id = Column(Integer, nullable=False)
    sku = Column(String, nullable=False)
    nome = Column(String, nullable=False)
    categoria = Column(String, nullable=True)
    subcategoria = Column(String, nullable=True)
    colecao = Column(String, nullable=True)
    cor = Column(String, nullable=True)
    modelagem = Column(String, nullable=True)
    tamanho = Column(String, nullable=True)
    preco = Column(Float, nullable=True)
    estoque = Column(Integer, nullable=True)
    imagem_url = Column(String, nullable=True)
    link_produto = Column(String, nullable=True)
    ocasiao = Column(String, nullable=True)
    tags_estilo = Column(String, nullable=True)
    ativo = Column(Boolean, nullable=True)
    user_id = Column(String, nullable=False)