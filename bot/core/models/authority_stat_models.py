from sqlalchemy.orm import Mapped

from core import Base, intpk


class AuthorityStatistic(Base):

    id: Mapped[intpk]
    snapshot_overall_ms: Mapped[int]
    snapshot_date: Mapped[str]
    nickname: Mapped[str]
    auto_without_cape: Mapped[int]
