from sqlalchemy.ext.asyncio import AsyncSession

from .base_async_orm import AsyncORM
from core.models import (
    AppMemberList, AskMemberList, DateInfo,
    NoticeList, RcdApplication, ButtonInfo
)


class RcdApplicationORM(AsyncORM):

    def __init__(self):
        super().__init__()

    # --------------------------------------------------------------------------------
    # Вставка данных в БД
    async def insert_date_info(self, session: AsyncSession, date_name, date):
        await self.insert_data(
            session, DateInfo, date_name=date_name, date=date
        )

    async def insert_message_id(
        self, session: AsyncSession, message_name, message_id
    ):
        await self.insert_data(
            session, RcdApplication,
            message_name=message_name, message_id=message_id
            )

    async def insert_members_to_notice_list(
        self, session: AsyncSession, members_id, action, role
    ):
        await self.insert_data(
                session, NoticeList,
                members_id=members_id, action=action, role=role
            )

    async def insert_appmember_id(self, session: AsyncSession, member_id):
        await self.insert_data(session, AppMemberList, member_id=member_id)

    async def insert_askmember_id(self, session: AsyncSession, member_id):
        await self.insert_data(session, AskMemberList, member_id=member_id)

    async def insert_button_info(
        self, session: AsyncSession, custom_id, **params
    ):
        await self.insert_data(
            session, ButtonInfo, custom_id=custom_id, **params
        )

    # --------------------------------------------------------------------------------
    # Получение данных
    async def get_rcd_date_obj(self, session: AsyncSession, pk):
        result = await self.get_obj_by_pk(session, DateInfo, pk)
        return result

    async def get_message_data_obj(self, session: AsyncSession, pk):
        result = await self.get_obj_by_pk(session, RcdApplication, pk)
        return result

    async def get_appmember_obj(self, session: AsyncSession, pk):
        result = await self.get_obj_by_pk(session, AppMemberList, pk)
        return result

    async def get_askmember_obj(self, session: AsyncSession, pk):
        result = await self.get_obj_by_pk(session, AskMemberList, pk)
        return result

    async def get_all_appmember_ids(self, session: AsyncSession):
        result = await self.get_filter_obj_all(session, AppMemberList)
        return [member.member_id for member in result]

    async def get_all_askmember_ids(self, session: AsyncSession):
        result = await self.get_filter_obj_all(session, AskMemberList)
        return [member.member_id for member in result]

    async def get_notice_list_obj_all(self, session: AsyncSession):
        result = await self.get_filter_obj_all(session, NoticeList)
        return result

    async def get_notice_list_data(self, session, action: str):
        obj_list = await self.get_filter_obj_all(
            session, NoticeList, action=action
        )

        if not obj_list:
            return None

        notice_list_data = []
        for obj in obj_list:
            members_id_list = [
                int(member_id) for member_id in obj.members_id.split(',')
            ]
            notice_dict_data = {
                'role': obj.role,
                'action': obj.action,
                'members_id': members_id_list
            }
            notice_list_data.append(notice_dict_data)
        return notice_list_data

    async def get_toogle_button_info(self, session: AsyncSession):
        result = await self.get_obj_by_pk(session, ButtonInfo, 'Тумблер')
        return result

    async def get_notice_button_info(self, session: AsyncSession):
        result = await self.get_obj_by_pk(
            session, ButtonInfo, 'ОповеститьОСписке'
        )
        return result

    async def get_second_list_button_info(self, session: AsyncSession):
        result = await self.get_obj_by_pk(
            session, ButtonInfo, 'СоздатьСписок'
        )
        return result

    # --------------------------------------------------------------------------------
    # Обновление данных
    async def update_button_info(
        self, session: AsyncSession, custom_id, **fields
    ):
        obj = await self.get_obj_by_pk(session, ButtonInfo, custom_id)
        self.obj_validation(obj)
        for attr, value in fields.items():
            setattr(obj, attr, value)
        session.add(obj)
        await session.flush()

    # --------------------------------------------------------------------------------
    # Удаление данных
    async def delete_from_notice_list(
        self, session: AsyncSession, action, role
    ):
        obj = await self.get_filter_obj_first(
            session, NoticeList, action=action, role=role
        )
        await self.delete_data(session, obj)

    async def clear_rcd_data(self, session: AsyncSession):
        for model in [
            AppMemberList, AskMemberList, DateInfo,
            NoticeList, RcdApplication
        ]:
            await self.clear_table(session, model)


rcd_app_orm = RcdApplicationORM()
