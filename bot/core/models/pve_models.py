from sqlalchemy.orm import Mapped

from core import Base, intpk, int_uniq, strpk, str_uniq


class MemberIdModelPve(Base):
    """Базовая модель с полем member_id"""
    __abstract__ = True

    member_id: Mapped[intpk]


class AppMemberListPve(MemberIdModelPve):
    """Модель ID пользователей, кто подал заявки на ПВЕ"""
    pass


class NoticeListPve(Base):
    """Модель списка пользователей для оповещения о ПВЕ"""
    members_id: Mapped[strpk]
    role: Mapped[str]


class DateInfoPve(Base):
    """Модель информации о дате ПВЕ"""
    date_name: Mapped[strpk]
    date: Mapped[str_uniq]


class PveApplication(Base):
    """Модель списка названия сообщений и их ID"""
    message_name: Mapped[strpk]
    message_id: Mapped[int_uniq]
