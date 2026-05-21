from sqlalchemy import Column, String

from core.models import Base


class BotSettings(Base):
    __tablename__ = 'important_channel'

    key = Column(String, primary_key=True)
    value = Column(String)