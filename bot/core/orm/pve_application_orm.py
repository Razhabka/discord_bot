from sqlalchemy.ext.asyncio import AsyncSession

from .base_async_orm import AsyncORM
from core.models import AppMemberListPve, DateInfoPve, PveApplication, NoticeListPve


class PveApplicationORM(AsyncORM):

    def __init__(self):
        super().__init__()

    # --------------------------------------------------------------------------------
    # Вставка данных в БД
    async def insert_date_info(self, session: AsyncSession, date_name, date):
        await self.insert_data(
            session, DateInfoPve, date_name=date_name, date=date
        )

    async def insert_message_id(
        self, session: AsyncSession, message_name, message_id
    ):
        await self.insert_data(
            session, PveApplication,
            message_name=message_name, message_id=message_id
            )
        
    async def insert_members_to_notice_list(
        self, session: AsyncSession, members_id, role
    ):
        await self.insert_data(
                session, NoticeListPve,
                members_id=members_id, role=role
            )

    async def insert_appmember_id(self, session: AsyncSession, member_id):
        await self.insert_data(session, AppMemberListPve, member_id=member_id)

    # --------------------------------------------------------------------------------
    # Получение данных
    async def get_pve_date_obj(self, session: AsyncSession, pk):
        result = await self.get_obj_by_pk(session, DateInfoPve, pk)
        return result

    async def get_message_data_obj(self, session: AsyncSession, pk):
        result = await self.get_obj_by_pk(session, PveApplication, pk)
        return result

    async def get_appmember_obj(self, session: AsyncSession, pk):
        result = await self.get_obj_by_pk(session, AppMemberListPve, pk)
        return result

    async def get_all_appmember_ids(self, session: AsyncSession):
        result = await self.get_filter_obj_all(session, AppMemberListPve)
        return [member.member_id for member in result]
    
    async def get_notice_list_obj_all(self, session: AsyncSession):
        result = await self.get_filter_obj_all(session, NoticeListPve)
        return result

    async def get_notice_list_data(self, session):
        obj_list = await self.get_filter_obj_all(session, NoticeListPve)

        if not obj_list:
            return None

        notice_list_data = []
        for obj in obj_list:
            members_id_list = [
                int(member_id) for member_id in obj.members_id.split(',')
            ]
            notice_dict_data = {
                'role': obj.role,
                'members_id': members_id_list
            }
            notice_list_data.append(notice_dict_data)
        return notice_list_data

    # --------------------------------------------------------------------------------
    # Обновление данных

    pass

    # --------------------------------------------------------------------------------
    # Удаление данных
    async def delete_from_notice_list(
        self, session: AsyncSession, role
    ):
        obj = await self.get_filter_obj_first(
            session, NoticeListPve, role=role
        )
        await self.delete_data(session, obj)
    
    async def clear_pve_data(self, session: AsyncSession):
        for model in [AppMemberListPve, DateInfoPve, PveApplication, NoticeListPve]:
            await self.clear_table(session, model)


pve_app_orm = PveApplicationORM()
