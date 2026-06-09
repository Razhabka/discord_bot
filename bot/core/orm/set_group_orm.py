from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from loguru import logger

from .base_async_orm import AsyncORM
from core.models import GroupMember, BotSettings

from ..models import GroupMember


class GroupManagerORM(AsyncORM):

    def __init__(self):
        super().__init__()

    # --------------------------------------------------------------------------------
    # Вставка и сохранение данных
    async def insert_group_member(
            self, session: AsyncSession, user_id: int, username: str, role_id: int, group_id: str,
            is_leader: bool = False
    ):
        await self.insert_data(
            session, GroupMember,
            user_id=user_id, username=username, role_id=role_id, group_id=group_id, is_leader=is_leader
        )

    async def create_group_channel_info(
      self, session: AsyncSession, group_id: int
    ):
        await self.insert_data(session, BotSettings, group_id=group_id, channel_id=None)

    # --------------------------------------------------------------------------------
    # Получение данных
    async def get_members_by_group(self, session: AsyncSession, group_id: str):
        """Получает всех участников конкретной группы"""
        # Если в вашем BaseORM нет готового метода фильтрации по не-PK полю, используем стандартный select:
        query = select(GroupMember).where(GroupMember.group_id == group_id)
        result = await session.execute(query)
        return result.scalars().all()

    async def get_group_channels(self, session: AsyncSession, group_id: str) -> dict:
        """Возвращает словарь с ID текстового и голосового каналов группы: {'text': int|None, 'voice': int|None}"""
        channels = {'text': None, 'voice': None}

        for c_type in ['text', 'voice']:
            key = f"group_{c_type}_channel_{group_id}"
            result = await session.execute(select(BotSettings).filter_by(key=key))
            settings = result.scalars().first()
            if settings and settings.value:
                channels[c_type] = int(settings.value)

        return channels

    async def get_role_by_lead(self, session: AsyncSession, lead_id: str):
        """Получает всех участников конкретной группы"""
        # Если в вашем BaseORM нет готового метода фильтрации по не-PK полю, используем стандартный select:
        query = select(GroupMember.role_id).where(GroupMember.user_id== lead_id)
        result = await session.execute(query)
        return result.scalars().first()

    async def get_all_active_groups(self, session: AsyncSession):
        """Получает список всех групп, четко разделяя лидера и участников по флагу is_leader"""
        query = select(GroupMember)
        result = await session.execute(query)
        all_members = result.scalars().all()

        groups = {}
        for m in all_members:
            g_id = m.group_id
            if g_id not in groups:
                groups[g_id] = {"leader_id": None, "member_ids": []}

            if m.is_leader:
                groups[g_id]["leader_id"] = m.user_id
            else:
                groups[g_id]["member_ids"].append(m.user_id)

        return groups

    async def get_role_id_by_user_and_group(self, session: AsyncSession, user_id: int, group_id: str) -> int | None:
        """Получает ID роли конкретного пользователя в конкретной группе"""
        query = select(GroupMember.role_id).where(
            GroupMember.user_id == user_id,
            GroupMember.group_id == group_id
        )
        result = await session.execute(query)
        return result.scalars().first()

    # --------------------------------------------------------------------------------
    # Обновление данных

    async def update_group_channel_by_type(self, session: AsyncSession, group_id: str, channel_id: int | None, channel_type: str):
        """
        Привязка, обновление или удаление ID канала в таблице важных настроек.
        channel_type может быть: 'text' или 'voice'
        """
        key = f"group_{channel_type}_channel_{group_id}"
        result = await session.execute(select(BotSettings).filter_by(key=key))
        settings = result.scalar_one_or_none()

        if channel_id is None:
            if settings:
                await session.delete(settings)
                logger.info(f"Запись {channel_type} канала для группы {group_id} удалена из БД.")
        else:
            if settings:
                settings.value = str(channel_id)
                logger.info(f"ID {channel_type} канала для группы {group_id} обновлен в БД.")
            else:
                new_settings = BotSettings(key=key, value=str(channel_id))
                session.add(new_settings)
                logger.info(f"Создана новая запись {channel_type} канала для группы {group_id} в БД.")
        await session.flush()

    # --------------------------------------------------------------------------------
    # Удаление данных

    async def clear_group_data(self, session: AsyncSession, group_id: str):
        """Полная очистка группы и всех связанных каналов из базы данных"""
        # Удаляем участников
        members = await self.get_members_by_group(session, group_id)
        if members:
            for member in members:
                await session.delete(member)

        # Удаляем записи обоих каналов
        for c_type in ['text', 'voice']:
            key = f"group_{c_type}_channel_{group_id}"
            result = await session.execute(select(BotSettings).where(BotSettings.key == key))
            settings = result.scalar_one_or_none()
            if settings is not None:
                await session.delete(settings)

        await session.flush()



set_group_orm = GroupManagerORM()