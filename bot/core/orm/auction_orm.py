from .base_async_orm import AsyncORM
from core import async_session_factory
from core.models import UserBid, AuctionDataInfo


class AuctionORM(AsyncORM):

    def __init__(self):
        super().__init__()

    # --------------------------------------------------------------------------------
    # Вставка данных в БД
    async def insert_bid_data(self, user_id, user_bid, lot_id):
        """Метод для добавления ставки в БД"""
        async with async_session_factory() as session:
            data = UserBid(user_id, user_bid, lot_id)
            await self.add_commit(session, data)

    async def insert_auc_info_data(
                self, name_auc, data, start_auc_user_id,
                start_bid, lot_amount
            ):
        """Метод для добавления ставки в БД"""
        async with async_session_factory() as session:
            data = AuctionDataInfo(
                name_auc, data, start_auc_user_id,
                start_bid, lot_amount
            )
            await self.add_commit(session, data)

    # --------------------------------------------------------------------------------
    # Получение данных
    async def get_bid_obj(self, pk):
        """Метод для получения данных из БД по первичному ключу"""
        async with async_session_factory() as session:
            result = await self.get_obj_by_pk(session, UserBid, pk)
            return result

    async def get_auc_info_obj(self, pk):
        """Метод для получения данных из БД по первичному ключу"""
        async with async_session_factory() as session:
            result = await self.get_obj_by_pk(session, AuctionDataInfo, pk)
            return result

    # --------------------------------------------------------------------------------
    # Обновление данных
    async def update_bid_data(self, user_id, new_value):
        """Метод для изменения ставки по названию поля"""
        async with async_session_factory() as session:
            obj = await self.get_filter_obj(UserBid, 'user_id', user_id)
            setattr(obj.scalars().first(), 'user_bid', new_value)
            await self.add_commit(session, obj)
            await session.refresh(obj)

    # --------------------------------------------------------------------------------
    # Удаление данных
    async def delete_bid_data(self, user_id):
        """Метод для удаления ставки из БД"""
        async with async_session_factory() as session:
            obj = await self.get_filter_obj(UserBid, 'user_id', user_id)
            await self.delete_data(session, obj)
            await session.commit()

    async def clear_userbid_table(self):
        """Метод для очистки таблицы ставок в БД"""
        await self.clear_table(UserBid)


auc_orm = AuctionORM()
