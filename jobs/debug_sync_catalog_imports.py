print("1. entrou no arquivo sync catalog")

print("2. importando básicos...")
import asyncio
import os
from datetime import datetime, timezone
print("2 ok")

print("3. importando services/modelos...")
from services.closet_db import AsyncSessionLocal, init_closet_db
print("3.1 closet_db ok")

from services.vtex_catalog_service import *
print("3.2 vtex_catalog_service ok")

print("4. terminou todos os imports com sucesso")