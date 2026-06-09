import discord
import sys
from loguru import logger

from bot.core import async_session_factory
from core import settings
from core.orm import async_orm, role_app_orm, set_group_orm
from randomaizer.randomaizer import RandomButton
from rename_request.rename_request import RenameButton, AccessDeniedView
from role_application.role_application import (
    ApplicationButton, has_required_role
)
from rcd_aplication.rcd_aplication import (
    StartRCDButton, CreateRCDList, AddMemberToListButton,
    PrivateMessageView as RcdPrivetMessage
)
from pve_application.discord_ui import (
    PveAppButton, PublishListButton, NotificationButton, StopAppButton, AddMemberToListButtonPve,
    PrivateMessageView as PvePrivetMessage)
from role_application.role_application import RoleButton
from set_group.set_group import SetGroupButton, GroupManagementView
from core import APPLICATION_CHANNEL_ID, ANSWERS_IF_NO_ROLE, INDEX_CLASS_ROLE



logger.remove()
logger.add(sink='discord_bot.log', level=10, rotation='5 MB')
logger.add(sink=sys.stderr, level="INFO")

intents = discord.Intents.all()

bot = discord.Bot(intents=intents)
if settings.debug_server_id:
    bot = discord.Bot(intents=intents, debug_guilds=[settings.debug_server_id])


@bot.event
async def on_ready() -> None:
    """Событие запуска бота"""

    await async_orm.create_tables()
    app_channel = await bot.fetch_channel(APPLICATION_CHANNEL_ID)
    bot.add_view(RandomButton())
    bot.add_view(RenameButton(channel=app_channel))
    bot.add_view(ApplicationButton(channel=app_channel))
    bot.add_view(AccessDeniedView())
    bot.add_view(SetGroupButton())
    bot.add_view(StartRCDButton())
    bot.add_view(RcdPrivetMessage())
    bot.add_view(PvePrivetMessage())
    create_rcd_list_view = CreateRCDList()

    try:
        async with async_session_factory() as session:
            active_groups = await set_group_orm.get_all_active_groups(session)

            for group_id, data in active_groups.items():
                leader_id = data["leader_id"]
                member_ids = [int(m) for m in data["member_ids"] if m is not None]

                if leader_id is None:
                    from core import LEADER_ID
                    leader_id = int(LEADER_ID)
                    logger.warning(f"У группы {group_id} не найден лидер в БД, установлен дефолтный.")

                logger.info(
                    f"[БД ЗАГРУЗКА] Восстановлена группа: {group_id} | Лидер: {leader_id} | Участники: {member_ids}")

                bot.add_view(GroupManagementView(
                    group_id=group_id,
                    leader_id=leader_id,
                    member_ids=member_ids
                ))

        logger.info(f"Успешно восстановлено панелей управления группами: {len(active_groups)}")
    except Exception as e:
        logger.error(f"Ошибка при восстановлении GroupManagementView: {e}")

    async with async_session_factory() as session:
        role_app_channel = await role_app_orm.get_important_channel_data(session, 'role_app_channel_id')
        if role_app_channel:
            channel = bot.get_channel(int(role_app_channel))
            if channel:
                bot.add_view(ApplicationButton(channel=channel))
                logger.info(f"Восстановлена прослушка заявок в канал: {channel.name}")
            else:
                logger.warning("Канал для заявок найден в БД, но бот не имеет к нему доступа!")

    for index, role in INDEX_CLASS_ROLE.items():
        create_rcd_list_view.add_item(AddMemberToListButton(
            label=f'Редактировать "{role}"',
            custom_id=f'{index}КнопкаДобавления'
        ))
    bot.add_view(create_rcd_list_view)
    bot.add_view(create_rcd_list_view)
    cstm_btn_ids = await role_app_orm.get_btn_cstm_ids()
    for id in cstm_btn_ids:
        acc_btn_cstm_id, den_btn_cstm_id = id
        bot.add_view(RoleButton(acc_btn_cstm_id, den_btn_cstm_id))
    bot.add_view(discord.ui.View(PveAppButton(), timeout=None))
    create_list_view = discord.ui.View(timeout=None)
    create_list_view.add_item(PublishListButton())
    create_list_view.add_item(NotificationButton())
    create_list_view.add_item(StopAppButton())
    for index, role in INDEX_CLASS_ROLE.items():
        create_list_view.add_item(AddMemberToListButtonPve(
            label=f'Редактировать "{role}"',
            custom_id=f'{index}КнопкаДобавления'
        ))
    bot.add_view(view=create_list_view)
    logger.info('Бот запущен и готов к работе!')


@bot.command()
async def reload_extentions(ctx: discord.ApplicationContext):
    """
    Команда для перезагрузки расширений.

    Parameters
    ----------
        ctx: discord.ApplicationContext
            Контекст команды.

    Returns
    -------
        None
    """
    if not has_required_role(ctx.user):
        return await ctx.respond(
            ANSWERS_IF_NO_ROLE,
            ephemeral=True,
            delete_after=15
        )
    bot.reload_extension('regular_commands.regular_commands')
    bot.reload_extension('rename_request.rename_request')
    bot.reload_extension('embed_manager.embed_manager')
    bot.reload_extension('randomaizer.randomaizer')
    bot.reload_extension('reminder.reminder')
    bot.reload_extension('rcd_aplication.rcd_aplication')
    bot.reload_extension('auc_buttons.auc_buttons')
    bot.reload_extension('role_application.role_application')
    bot.reload_extension('set_group.set_group')
    bot.reload_extension('pve_application.pve_application')
    await ctx.respond(
        '_Расширения перезагружены!_',
        ephemeral=True,
        delete_after=10
    )
    logger.info('Расширения перезагружены')


bot.load_extension('regular_commands.regular_commands')
bot.load_extension('rename_request.rename_request')
bot.load_extension('build_embeds.embed_manager')
bot.load_extension('rcd_aplication.rcd_aplication')
bot.load_extension('reminder.reminder')
bot.load_extension('randomaizer.randomaizer')
bot.load_extension('auction.auc_buttons')
bot.load_extension('role_application.role_application')
bot.load_extension('set_group.set_group')
bot.load_extension('pve_application.pve_application')
logger.info('Приложения запущены')


if __name__ == '__main__':
    bot.run(settings.token)
