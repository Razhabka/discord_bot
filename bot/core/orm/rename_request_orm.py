from sqlalchemy.ext.asyncio import AsyncSession

from .base_async_orm import AsyncORM
from core.models import RenameRequestModel


class RenameRequestORM(AsyncORM):

    def __init__(self):
        super().__init__()

    # --------------------------------------------------------------------------------
    # Вставка данных в БД
    async def insert_rename_request_data(
        self, session: AsyncSession, old_nickname, new_nickname, user_id
    ):
        """Метод для добавления данных о запросе на ренейм"""
        await self.insert_data(
            session, RenameRequestModel,
            old_nickname=old_nickname,
            new_nickname=new_nickname,
            user_id=user_id
        )

    # --------------------------------------------------------------------------------
    # Получение данных
    async def get_rename_request_obj(self, session: AsyncSession, pk):
        """Метод для получения данных из БД по первичному ключу"""
        result = await session.get(RenameRequestModel, pk)
        return result

    # --------------------------------------------------------------------------------
    # Удаление данных
    async def delete_rename_request_data(self, session: AsyncSession, pk):
        """Метод для удаления заявки на ренейм из бд"""
        obj = await self.get_obj_by_pk(session, RenameRequestModel, pk)
        await self.delete_data(session, obj)

    async def clear_rename_request_table(self, session: AsyncSession):
        """Метод для очистки таблицы заявок на ренейм в БД"""
        await self.clear_table(session, RenameRequestModel)


rename_req_orm = RenameRequestORM()
