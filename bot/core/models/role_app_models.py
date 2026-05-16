from sqlalchemy.orm import Mapped
from sqlalchemy import Column, String
from core import Base, strpk, int_uniq, str_uniq


class RoleApplicationData(Base):

    nickname: Mapped[strpk]
    user_id: Mapped[int_uniq]
    acc_btn_cstm_id: Mapped[str_uniq]
    den_btn_cstm_id: Mapped[str_uniq]

class BotSettings(Base):
    __tablename__ = 'important_channel'

    key = Column(String, primary_key=True)
    value = Column(String)
