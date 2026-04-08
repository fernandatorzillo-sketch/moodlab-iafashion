from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class Empresa(BaseModel):
    id: int
    nome_empresa: str
    slug: str
    email_admin: str
    plataforma_ecommerce: Optional[str] = None
    erp: Optional[str] = None
    crm: Optional[str] = None
    logo_url: Optional[str] = None
    cor_primaria: Optional[str] = None
    cor_secundaria: Optional[str] = None
    ativa: bool = True
    user_id: str
    created_at: datetime
    updated_at: datetime