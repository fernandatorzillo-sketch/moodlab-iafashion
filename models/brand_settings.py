from core.database import Base
from sqlalchemy import Column, Integer, String


class Brand_settings(Base):
    __tablename__ = "brand_settings"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    empresa_id = Column(Integer, nullable=False)
    logo_url = Column(String, nullable=True)
    brand_name = Column(String, nullable=True)
    primary_color = Column(String, nullable=True)
    secondary_color = Column(String, nullable=True)
    background_color = Column(String, nullable=True)
    text_color = Column(String, nullable=True)
    font_family = Column(String, nullable=True)
    button_style = Column(String, nullable=True)
    border_radius = Column(String, nullable=True)
    display_mode = Column(String, nullable=True)
    tone_of_voice = Column(String, nullable=True)
    aesthetic_description = Column(String, nullable=True)
    module_name_closet = Column(String, nullable=True)
    module_name_looks = Column(String, nullable=True)
    module_name_recommendations = Column(String, nullable=True)
    banner_url = Column(String, nullable=True)
    user_id = Column(String, nullable=False)