from sqlalchemy.orm import Mapped

from core import Base, int_uniq, strpk, str_uniq


class RenameRequestModel(Base):

    old_nickname: Mapped[strpk]
    new_nickname: Mapped[str_uniq]
    user_id: Mapped[int_uniq]
