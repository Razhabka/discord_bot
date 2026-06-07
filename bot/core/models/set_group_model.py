from sqlalchemy.orm import Mapped, mapped_column
from core import Base, intpk, strpk, int_uniq, int_empty

class GroupMember(Base):
    """
    Модель для хранения информации об участниках КП.
    Автоматически получит имя таблицы 'GroupMember'.
    """
    id: Mapped[intpk]
    user_id: Mapped[int]
    username: Mapped[str]
    role_id: Mapped[int]
    group_id: Mapped[int]
    is_leader: Mapped[bool] = mapped_column(default=False)
