from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from .base_async_orm import AsyncORM
from core import async_session_factory
from core.models import RoleApplicationData


class RoleApplicationORM(AsyncORM):

    def __init__(self):
        super().__init__()

    # --------------------------------------------------------------------------------
    # Вставка данных в БД
    async def insert_role_application_data(
        self, session: AsyncSession, nickname, user_id,
        acc_btn_cstm_id, den_btn_cstm_id
    ):
        """Метод для добавления данных о заявке на роль"""
        await self.insert_data(
            session, RoleApplicationData,
            nickname=nickname,
            user_id=user_id,
            acc_btn_cstm_id=acc_btn_cstm_id,
            den_btn_cstm_id=den_btn_cstm_id
        )

    # --------------------------------------------------------------------------------
    # Получение данных
    async def get_roleapp_obj(self, session: AsyncSession, pk):
        """Метод для получения данных из БД по первичному ключу"""
        result = await session.get(RoleApplicationData, pk)
        return result

    async def get_roleapp_count(self, session: AsyncSession):
        """Метод для получения количества строк в таблице"""
        result = await session.execute(
            select(func.count()).select_from(RoleApplicationData)
        )
        count = result.scalar()
        return count

    async def get_btn_cstm_ids(self):
        """
        Метод для получения всех значений столбцов acc_btn_cstm_id
        и den_btn_cstm_id из БД
        """
        async with async_session_factory() as session:
            stmt = select(
                RoleApplicationData.acc_btn_cstm_id,
                RoleApplicationData.den_btn_cstm_id
            )
            result = await session.execute(stmt)
            return result.all()

    # --------------------------------------------------------------------------------
    # Удаление данных
    async def delete_roleapp_data(self, session: AsyncSession, pk):
        """Метод для удаления заявки на роль из бд"""
        obj = await self.get_obj_by_pk(session, RoleApplicationData, pk)
        await self.delete_data(session, obj)

    async def clear_roleapp_table(self, session: AsyncSession):
        """Метод для очистки таблицы заявок на роль в БД"""
        await self.clear_table(session, RoleApplicationData)


role_app_orm = RoleApplicationORM()
