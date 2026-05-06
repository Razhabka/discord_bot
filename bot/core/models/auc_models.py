from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core import Base, intpk, int_uniq, strpk


class AuctionDataInfo(Base):
    """Модель информации об аукционе"""
    name_auc: Mapped[strpk]
    data: Mapped[str]
    start_auc_user_id: Mapped[int_uniq]
    start_bid: Mapped[int]
    lot_amount: Mapped[int]
    bids: Mapped[list["UserBid"]] = relationship(
        'UserBid', back_populates='auction'
    )


class UserBid(Base):
    """Модель ставок на аукционе"""
    lot_id: Mapped[intpk] = mapped_column(
        ForeignKey('AuctionDataInfo.name_auc')
    )
    user_id: Mapped[int_uniq | None]
    user_bid: Mapped[int]
    auction: Mapped["AuctionDataInfo"] = relationship(
        'AuctionDataInfo', back_populates='bids'
    )
