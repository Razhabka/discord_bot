from datetime import datetime
import re
import locale
import discord

from pygments.styles.dracula import comment

try:
    locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_ALL, 'ru_RU')

from discord import InputTextStyle, Interaction, utils, ButtonStyle, ComponentType, Forbidden
from discord.ui import Modal, InputText, View, Button, Select, select, button
from loguru import logger

from core import (async_session_factory, PVE_CHANNEL_ID,
                  TRANSLATION_ROLES, INDEX_CLASS_ROLE, PVE_APPLICATION_CHANNEL_ID, PVE_ROLE, GUEST_ROLE)
from core.orm import pve_app_orm
from .embeds import (
    start_pve_embed, app_list_embed, pve_list_embed,
    pve_notification_embed, publish_pve_embed, ask_pve_embed
)
from .static import StaticNamesPve
from role_application.functions import require_role, character_lookup


class PVEDate(Modal):
    """
    Модальное окно для ввода даты ПВЕ.
    """
    def __init__(self):
        super().__init__(title='Введи дату проведения ПВЕ рейда', timeout=None)

        self.add_item(
            InputText(
                style=InputTextStyle.short,
                label='Укажи дату в формате ДД.ММ ЧЧ:ММ',
                placeholder='ДД.ММ ЧЧ:ММ',
                max_length=11
            )
        )

        self.add_item(
            InputText(
                style=InputTextStyle.short,
                label='Укажи минимальный ГС',
                placeholder='число',
                max_length=5
        ))

    async def callback(self, interaction: Interaction):
        await interaction.response.defer(invisible=False, ephemeral=True)
        date_str: str = str(self.children[0].value)
        gs_value: str = str(self.children[1].value)
        if not gs_value.isdigit():
            return await interaction.respond('❌\n\nЗначение ГС только целочисленное', delete_after=3)
        min_gearscore: int = int(gs_value)
        formatted_gearscore = locale.format_string('%d', min_gearscore, grouping=True)
        pattern = r'^([0-2][0-9]|3[0-1])[.,/](0[1-9]|1[0-2]) ([0-1][0-9]|2[0-3])[:;]([0-5][0-9])$'
        match = re.match(pattern, date_str)

        if not match:
            return await interaction.respond('_Неверный формат. Ожидался ДД.ММ ЧЧ:ММ_', delete_after=5)
        
        day, month, hour, minute = map(int, match.groups())
        pve_app_channel = interaction.guild.get_channel(PVE_CHANNEL_ID)
        
        try:
            async with async_session_factory() as session:
                current_year = datetime.now().year
                pve_date = datetime(
                    year=current_year,
                    month=month,
                    day=day,
                    hour=hour,
                    minute=minute)
                if pve_date < datetime.now():
                    pve_date = pve_date.replace(year=current_year + 1)
                convert_pve_date = utils.format_dt(pve_date, style="F")
                await pve_app_orm.insert_date_info(
                    session, StaticNamesPve.PVE_DATE, convert_pve_date
                )
                app_channel_view = View(PveAppButton(min_gear_score=min_gearscore), timeout=None)
                await interaction.channel.send(embed=app_list_embed(convert_pve_date), view=StartPVEButton(min_gear_score=min_gearscore))
                await pve_app_channel.send(embed=start_pve_embed(convert_pve_date, formatted_gearscore), view=app_channel_view)
                await pve_app_orm.insert_message_id(
                    session=session,
                    message_name=StaticNamesPve.PVE_APPCHANNEL_MESSAGE,
                    message_id=pve_app_channel.last_message_id
                )
                await pve_app_orm.insert_message_id(
                    session=session,
                    message_name=StaticNamesPve.START_PVE_MESSAGE,
                    message_id=interaction.guild.get_channel(interaction.channel_id).last_message_id
                )
                pve_buttons_embed_list = [pve_list_embed(convert_pve_date)]
                create_list_view = View(timeout=None)
                create_list_view.add_item(PublishListButton())
                create_list_view.add_item(NotificationButton())
                create_list_view.add_item(StopAppButton())
                for index, role in INDEX_CLASS_ROLE.items():
                    create_list_view.add_item(AddMemberToListButtonPve(
                        label=f'Редактировать "{role}"',
                        custom_id=f'{index}КнопкаДобавления'
                    ))
                await interaction.channel.send(view=create_list_view, embeds=pve_buttons_embed_list)
                await pve_app_orm.insert_message_id(
                    session=session,
                    message_name=StaticNamesPve.PVE_LIST_MESSAGE,
                    message_id=interaction.guild.get_channel(interaction.channel_id).last_message_id
                )
                await pve_app_orm.insert_message_id(
                    session=session,
                    message_name=StaticNamesPve.PVE_LIST_CHANNEL,
                    message_id=interaction.guild.get_channel(interaction.channel_id).id
                )
                await session.commit()
                await interaction.respond('✅', delete_after=1)
        except Exception as error:
            await interaction.respond('❌', delete_after=1)
            logger.error(f'При вводе даты ПВЕ заявок возникла ошибка "{error}"')


class PveApplication(Modal):
    """
    Модальное окно для ввода данных на заявку ПВЕ.
    """
    def __init__(self, min_gear_score: int | None = None):
        super().__init__(title='Заявка на ПВЕ', timeout=None),
        self.min_gear_score = min_gear_score

        self.add_item(
            InputText(
                style=InputTextStyle.singleline,
                label='Укажи класс',
                placeholder='Любой, если не заполнить',
                required=False,
                max_length=10
            )
        )

        self.add_item(
            InputText(
                style=InputTextStyle.singleline,
                label='Укажи роль',
                placeholder='Танк | ДД | Саппорт',
                required=True,
                max_length=20
            )
        )

        self.add_item(
            InputText(
                style=InputTextStyle.singleline,
                label='Укажите ник персонажа, на котором пойдете',
                placeholder='Учитывай регистр (большие и маленькие буквы)',
                required=True,
                max_length=20
            )
        )

    async def callback(self, interaction: Interaction):
        try:
            await interaction.response.defer(invisible=False, ephemeral=True)
            async with async_session_factory() as session:
                user = interaction.user
                if not user or not user.id:
                    return await interaction.respond(
                        ' 🤷‍♂️\n\n_Ошибка реакции на кнопку, повтори снова\n\n'
                        'Button response error, try again_',
                        delete_after=3
                    )
                class_value: str = str(self.children[0].value)
                role_value: str = str(self.children[1].value)
                nickname: str = str(self.children[2].value)

                player_info = character_lookup(1, nickname)

                if interaction.user.display_name != nickname:
                    class_value = f"({nickname}) {class_value}"

                gear_score = player_info['gear_score']

                if not class_value:
                    class_value = 'Любой класс'

                if int(gear_score) > 100 and int(gear_score) < self.min_gear_score:
                    logger.info(f'У игрока"{interaction.user.display_name}" ГС: "{gear_score:}", что меньше минимального: "{self.min_gear_score}"')
                    return await interaction.respond(
                        'У тебя маленький ГС',
                        delete_after=3
                    )
                if int(gear_score) < 100 :
                    logger.info(
                        f'Игрок: "{interaction.user.display_name}" оказался клоуном и ввел ГС= "{gear_score}"')
                    return await interaction.respond(
                        'Блять, ты что КЛОУН?:clown:',
                        delete_after=3
                    )
                gearscore: int = int(gear_score)
                formatted_gearscore = locale.format_string('%d', gearscore, grouping=True)

                role_mapping = {
                    'tank': 'Танк',
                    'Tank': 'Танк',
                    'dd': 'ДД',
                    'support': 'Саппорт',
                    'sup': 'Саппорт',
                    'supp': 'Саппорт'
                }

                def translate_roles(role_value: str) -> str:
                    role_value = (
                        role_value.replace(" | ", ", ").replace("|", ", ")
                        .replace("/", ", ").replace(" / ", ", ").replace("\\", ", ").replace(" \\ ", ", ")
                    )

                    parts = role_value.split(", ")
                    translated_parts = []
                    
                    for part in parts:
                        part = part.strip()
                        if part.lower() in role_mapping:
                            translated_parts.append(role_mapping[part.lower()])
                        else:
                            translated_parts.append(part)

                    return ", ".join(translated_parts)

                role = translate_roles(role_value)
                
                guild = user.mutual_guilds[0]
                member = guild.get_member(user.id)
                field_index = 0 if discord.utils.get(member.roles, name=PVE_ROLE) else 1
                start_pve_message_obj = await pve_app_orm.get_message_data_obj(
                    session=session,
                    pk=StaticNamesPve.START_PVE_MESSAGE
                )
                pve_list_channel_obj = await pve_app_orm.get_message_data_obj(
                    session=session,
                    pk=StaticNamesPve.PVE_LIST_CHANNEL
                )
                if not pve_list_channel_obj or not start_pve_message_obj:
                    return await interaction.respond(
                        '🙌\n\n_Ошибка получения данных из БД, обратись к администратору сервера!\n\n'
                        'Error retrieving data from the database, please contact your server administrator!_',
                        delete_after=5
                    )

                pve_list_channel = guild.get_channel(pve_list_channel_obj.message_id)
                start_pve_message = await pve_list_channel.fetch_message(start_pve_message_obj.message_id)
                during_embed = start_pve_message.embeds[0]
                field_value = during_embed.fields[field_index].value
                pattern = re.compile(rf'{member.mention}: (🟡|🔴)')
                match = pattern.search(field_value)
                if match:
                    new_value = field_value.replace(
                        match.group(0), f'{member.mention}: {class_value} {role} ({int(float(gear_score)):,})'
                    )
                else:
                    new_value = field_value + f'\n{member.mention}: {class_value} {role} ({int(float(gear_score)):,})'
                during_embed.fields[field_index].value = new_value
                await start_pve_message.edit(embed=during_embed)
                await pve_app_orm.insert_appmember_id(session, user.id)
                await session.commit()
                await interaction.respond('_✅\n\nЗаявка принята!\n\nThe application was accepted!_', delete_after=2)
                logger.info(f'Принята заявка на ПВЕ от "{user.display_name}"')
        except Exception as error:
            await interaction.respond('❌', delete_after=1)
            logger.error(
                f'При отправке заявки на ПВЕ пользователем '
                f'"{user.display_name}" произошла ошибка "{error}"'
            )


class PveAppButton(Button):
    """Кнопка для подачи заявки на ПВЕ"""

    def __init__(self, min_gear_score: int | None = None):
        self.min_gear_score = min_gear_score
        super().__init__(
            label="Подать заявку на ПВЕ",
            style=ButtonStyle.green,
            custom_id="ПодатьЗаявкуНаПВЕ"
        )

    async def callback(self, interaction: Interaction):
        try:
            async with async_session_factory() as session:
                all_member_ids = await pve_app_orm.get_all_appmember_ids(session)
                if interaction.user.id in all_member_ids:
                    return await interaction.respond(
                        "✅\n\n_Ты уже подал заявку!\n\nYou've already applied!_",
                        delete_after=5,
                        ephemeral=True
                    )
                await interaction.response.send_modal(PveApplication(min_gear_score=self.min_gear_score))
        except Exception as error:
            await interaction.respond('❌', delete_after=1)
            logger.error(f'При нажатии на кнопку подачи заявки возникла ошибка "{error}"')


class AddMemberToListButtonPve(Button):
    """Кнопка для добавления игроков к классам"""

    def __init__(self, custom_id: str, label: str, style=ButtonStyle.green,):
        super().__init__(
            label=label,
            style=style,
            custom_id=custom_id
        )

    @require_role
    async def callback(self, interaction: Interaction):
        try:
            check_label: str = self.label.split()[1]
            for index, role in INDEX_CLASS_ROLE.items():
                if role[:-2] in check_label:
                    await interaction.respond(view=SelectMemberView(index=index))
        except Exception as error:
            await interaction.respond('❌', delete_after=1)
            logger.error(f'При нажатии на кнопку добавления игроков возникла ошибка "{error}"')



class PublishListButton(Button):
    """
    Кнопка для публикации списка ПВЕ.
    """
    def __init__(self):
        super().__init__(
            label='Опубликовать 📨',
            style=ButtonStyle.blurple,
            custom_id='ОпубликоватьПве'
        )

    @require_role
    async def callback(self, interaction: Interaction):
        try:
            async with async_session_factory() as session:
                pve_appchannel_message_obj = await pve_app_orm.get_message_data_obj(
                    session=session,
                    pk=StaticNamesPve.PVE_APPCHANNEL_MESSAGE
                )
                pve_app_channel = interaction.guild.get_channel(PVE_CHANNEL_ID)
                pve_app_message = await pve_app_channel.fetch_message(
                    pve_appchannel_message_obj.message_id
                )
                pve_app_message_embeds = pve_app_message.embeds
                during_embed_list = interaction.message.embeds[0]
                date_data_obj = await pve_app_orm.get_pve_date_obj(
                    session=session,
                    pk=StaticNamesPve.PVE_DATE
                )
                embed = publish_pve_embed(date=date_data_obj.date)
                for field in [field for field in during_embed_list.fields if field.value != '']:
                    name, value, inline = field.name, field.value, field.inline
                    embed.add_field(
                        name=f'{name[:-1]}:', value=value, inline=inline
                    )
                pve_app_message_embeds[0] = embed
                await pve_app_message.edit(embeds=pve_app_message_embeds, view=None)
                logger.info(
                    f'Список ПВЕ изменён в {pve_app_channel.name} '
                    f'пользователем {interaction.user.display_name}'
                )
                await interaction.respond('✅', delete_after=1)
        except Exception as error:
            logger.error(f'При публикации списка возникла ошибка "{error}"')


class NotificationButton(Button):
    """
    Кнопка для оповещения участников.
    """
    def __init__(
        self,
        label='Оповестить о ПВЕ из списка 📣',
        style=ButtonStyle.blurple,
        disabled=False
    ):
        super().__init__(
            label=label,
            style=style,
            custom_id='ОповеститьОСпискеПве',
            disabled=disabled
        )

    @require_role
    async def callback(self, interaction: Interaction):
        try:
            async def send_notification(member, pve_role: str, date, comment: str | None):
                try:
                    logger.info(f"{member.display_name} из send_notification")
                    await member.send(
                        embed=pve_notification_embed(
                            interaction_user=interaction.user.display_name,
                            date=date,
                            jump_url=jump_url,
                            pve_role=pve_role,
                            comment=comment

                        ),
                        # TODO: 10800
                        delete_after=10800
                    )
                except Forbidden:
                    logger.warning(f'Пользователю "{member.display_name}" запрещено отправлять сообщения')

            async def get_members_by_role(session, notice_data_list, date, current_embed):

                if not notice_data_list:
                    return False

                for dict_item in notice_data_list:
                    role = dict_item.get('role')
                    members_id = dict_item.get('members_id')

                    await pve_app_orm.delete_from_notice_list(session, role=role)

                    field_value = ""
                    if current_embed and current_embed.fields:
                        for field in current_embed.fields:
                            if field.name == role:
                                field_value = field.value
                                break

                    for member_id in members_id:
                        member = await interaction.guild.fetch_member(member_id)
                        player_comment = None

                        if field_value:
                            parts = field_value.split(',')
                            for part in parts:
                                if f"<@{member_id}>" in part or f"<@!{member_id}>" in part:
                                    clean_comment = part.replace(f"<@{member_id}>", "").replace(f"<@!{member_id}>",
                                                                                                "").strip()
                                    if clean_comment:
                                        player_comment = clean_comment
                                    break
                        await send_notification(member, role, date, player_comment)
                        logger.info(f'"{member.display_name}" оповещён об ПВЕ')
                
                return True

            async with async_session_factory() as session:
                date_data_obj = await pve_app_orm.get_pve_date_obj(session=session, pk=StaticNamesPve.PVE_DATE)
                pve_appchannel_message_obj = await pve_app_orm.get_message_data_obj(
                    session=session,
                    pk=StaticNamesPve.PVE_APPCHANNEL_MESSAGE
                )
                pve_app_channel = interaction.guild.get_channel(PVE_CHANNEL_ID)
                pve_app_message = await pve_app_channel.fetch_message(pve_appchannel_message_obj.message_id)

                if 'Заявки на ПВЕ' in pve_app_message.embeds[0].title:
                    return await interaction.respond('❌\n\n_Сначала опубликуй список_', delete_after=5)

                jump_url = pve_app_channel.jump_url if 'Список ПВЕ' in pve_app_message.embeds[0].title else None

                during_embed = interaction.message.embeds[0]

                if not await get_members_by_role(
                    session,
                    await pve_app_orm.get_notice_list_data(session),
                    date_data_obj.date,
                    during_embed
                ):
                    return await interaction.respond(
                        '🤔\n_Дядь, в списке пусто _\n',
                        delete_after=3,
                    )

                await session.flush()
                create_list_view = View(timeout=None)
                create_list_view.add_item(PublishListButton())
                create_list_view.add_item(
                    NotificationButton(
                    label='Все оповещения были отправлены ✅',
                    style=ButtonStyle.gray,
                    disabled=True
                ))
                create_list_view.add_item(StopAppButton())
                for index, role in INDEX_CLASS_ROLE.items():
                    create_list_view.add_item(AddMemberToListButtonPve(
                        label=f'Редактировать "{role}"',
                        custom_id=f'{index}КнопкаДобавления'
                    ))
                await interaction.message.edit(view=create_list_view)
                await session.commit()
                await interaction.respond('✅', delete_after=1)
        except Exception as error:
            await interaction.respond('❌', delete_after=1)
            logger.error(
                'При отправке уведомлений пользователям из списка '
                f'ПВЕ возникла ошибка: "{error}"!'
            )


class StopAppButton(Button):
    """
    Кнопка для оповещения участников.
    """
    def __init__(self):
        super().__init__(
            label='Завершить работу со списком ПВЕ',
            style=ButtonStyle.red,
            custom_id='ЗавершитьПВЕСписок'
        )

    @require_role
    async def callback(self, interaction: Interaction):
        try:
            async with async_session_factory() as session:
                await interaction.message.delete()
                pve_appchannel_message_obj = await pve_app_orm.get_message_data_obj(
                    session=session,
                    pk=StaticNamesPve.PVE_APPCHANNEL_MESSAGE
                )
                pve_app_channel = interaction.guild.get_channel(PVE_CHANNEL_ID)
                pve_app_message = await pve_app_channel.fetch_message(pve_appchannel_message_obj.message_id)
                if 'Заявки на ПВЕ' in pve_app_message.embeds[0].title:
                    await pve_app_message.delete()
                start_pve_message_obj = await pve_app_orm.get_message_data_obj(
                    session=session,
                    pk=StaticNamesPve.START_PVE_MESSAGE
                )
                start_pve_message = await interaction.channel.fetch_message(start_pve_message_obj.message_id)
                await start_pve_message.edit(view=None)
                await pve_app_orm.clear_pve_data(session)
                await session.commit()
                await interaction.respond('✅', delete_after=1)
                logger.info(f'Пользователь "{interaction.user.display_name}" завершил работу с ПВЕ списками')
        except Exception as error:
            await pve_app_orm.clear_pve_data(session)
            await session.commit()
            await interaction.respond('❌', delete_after=1)
            logger.error(f'При завершении работы с ПВЕ возникла ошибка "{error}"')


class StartPVEButton(View):
    """
    Кнопка для запуска ПВЕ заявок.
    """

    def __init__(
            self,
            timeout: float | None = None,
            min_gear_score: int | None = None
    ):
        super().__init__(timeout=timeout)
        self.min_gear_score = min_gear_score

    @select(
        select_type=discord.ComponentType.user_select,
        min_values=1,
        max_values=24,
        placeholder='Выбери игроков, которых спросить об ПВЕ',
        disabled=False,
        custom_id='ВыберитеИгроков'
    )
    async def ask_callback(
            self, select: discord.ui.Select, interaction: discord.Interaction
    ):
        try:
            await interaction.response.defer(invisible=False, ephemeral=True)
            async with async_session_factory() as session:
                during_embed: discord.Embed = interaction.message.embeds[0]
                ask_users: list[discord.Member] = [user for user in select.values]
                date_obj = await pve_app_orm.get_pve_date_obj(session=session, pk=StaticNamesPve.PVE_DATE)
                for user in ask_users:
                    during_embed.fields[0].value += (f'\n{user.mention}: 🟡')
                    try:
                        await user.send(
                            embed=ask_pve_embed(
                                member=interaction.user,
                                date=date_obj.date,
                                min_gearscore=self.min_gear_score
                            ),
                            view=PrivateMessageView(self.min_gear_score),
                            delete_after=86400
                        )
                        logger.info(f'Пользователю "{user.display_name}" был отправлен вопрос об ПВЕ')
                    except discord.Forbidden:
                        logger.warning(f'Пользователю "{user.display_name}" запрещено отправлять сообщения')
                await interaction.message.edit(embed=during_embed)
                await interaction.respond('✅', delete_after=1)
        except Exception as error:
            await interaction.respond('❌', delete_after=1)
            logger.error(
                f'При опросе игроков возникла ошибка "{error}"'
            )

    @button(
        label='Спросить всех с ролью ПВЕ', style=discord.ButtonStyle.green,
        emoji='📢', custom_id='СпроситьВсехПВЕ'
    )
    async def ask_all_veteran_callback(
            self,
            button: discord.ui.Button,
            interaction: discord.Interaction
    ):
        try:
            await interaction.response.defer(invisible=False, ephemeral=True)

            during_embed: discord.Embed = interaction.message.embeds[0]

            pve_role: discord.Role | None = discord.utils.get(interaction.guild.roles, name=PVE_ROLE)
            if not pve_role:
                return await interaction.respond("❌ Роль ПВЕ не найдена на этом сервере!", delete_after=5)

            async with async_session_factory() as session:
                date_obj = await pve_app_orm.get_pve_date_obj(session=session, pk=StaticNamesPve.PVE_DATE)

            notified_count = 0

            for pve in pve_role.members:
                if pve.bot:
                    continue

                if during_embed.fields[0].value and pve.mention in during_embed.fields[0].value:
                    continue

                if during_embed.fields[0].value:
                    during_embed.fields[0].value += f'\n{pve.mention}: 🟡'
                else:
                    during_embed.fields[0].value = f'{pve.mention}: 🟡'

                try:
                    logger.info(f'{pve.display_name} из ask_all_veteran_callback')
                    await pve.send(
                        embed=ask_pve_embed(
                            member=interaction.user,
                            date=date_obj.date,
                            min_gearscore=self.min_gear_score
                        ),
                        view=PrivateMessageView(self.min_gear_score, pve.display_name),
                        delete_after=86400
                    )
                    logger.info(f'Пользователю "{pve.display_name}" был отправлен вопрос об ПВЕ')
                    notified_count += 1
                except discord.Forbidden:
                    logger.warning(f'Пользователю "{pve.display_name}" запрещено отправлять сообщения в ЛС')

            if notified_count > 0:
                button.disabled = True
                button.style = discord.ButtonStyle.gray
                button.label = f"Опрос запущен (Оповещено: {notified_count})"
                button.emoji = "✅"
                await interaction.message.edit(embed=during_embed, view=self)

            await interaction.respond(f'✅ Опрос успешно разослан! Оповещено игроков: {notified_count}', delete_after=3)

        except Exception as error:
            await interaction.respond('❌ Ошибка при массовом опросе', delete_after=3)
            logger.error(
                f'При нажатии на кнопку "спросить ветеранов об РЧД" '
                f'пользователем "{interaction.user.display_name}" '
                f'возникла ошибка "{error}"'
            )

class PrivateMessageView(View):
    """
    Кнопка для отказа или соглашения идти в ПВЕ.
    """
    def __init__(self, min_gear_score: int | None = None, member: str| None = None):
        super().__init__(timeout=None),
        self.min_gear_score = min_gear_score
        self.member = member

    @button(
        label='Отправить заявку на ПВЕ', style=discord.ButtonStyle.green,
        emoji='📋', custom_id='ЗаявкаПВЕприват'
    )
    async def acces_callback(
        self,
        button: discord.ui.Button,
        interaction: discord.Interaction
    ):
        try:
            async with async_session_factory() as session:
                all_member_ids = await pve_app_orm.get_all_appmember_ids(session)
                logger.info(f'{self.member} PrivateMessageView')
                if interaction.user.id in all_member_ids:
                    return await interaction.respond('_Ты уже подал заявку! ✅_', delete_after=1)
                await interaction.response.send_modal(RaidChampionDominionApplication(self.min_gear_score, member=self.member))
        except Exception as error:
            await interaction.respond('❌', delete_after=1)
            logger.error(
                f'При нажатии на кнопку отправки заявки на ПВЕ '
                f'пользователем "{interaction.user.display_name}" '
                f'возникла ошибка "{error}"'
            )

    @button(
        label='Меня не будет ❌',
        style=discord.ButtonStyle.red,
        custom_id='МеняНеБудет'
    )
    async def denied_callback(
            self,
            button: discord.ui.Button,
            interaction: discord.Interaction
    ):
        try:
            await interaction.response.defer(invisible=False, ephemeral=True)
            async with async_session_factory() as session:
                guild = interaction.user.mutual_guilds[0]
                member = guild.get_member(interaction.user.id)
                start_pve_message_obj = await pve_app_orm.get_message_data_obj(
                    session=session,
                    pk=StaticNamesPve.START_PVE_MESSAGE
                )
                pve_list_channel_obj = await pve_app_orm.get_message_data_obj(
                    session=session,
                    pk=StaticNamesPve.PVE_LIST_CHANNEL
                )
                rcd_list_channel: discord.TextChannel = guild.get_channel(pve_list_channel_obj.message_id)
                start_rcd_message: discord.Message = (
                    await rcd_list_channel.fetch_message(start_pve_message_obj.message_id)
                )
                during_embed: discord.Embed = start_rcd_message.embeds[0]
                field_value = during_embed.fields[0].value
                if member.mention in field_value:
                    new_value = field_value.replace(f'{member.mention}: 🟡', f'{member.mention}: 🔴')
                    during_embed.fields[0].value = new_value
                    await start_rcd_message.edit(embed=during_embed)
                await interaction.message.delete()
                await interaction.respond('_Принято ✅_', delete_after=1)
                logger.info(f'"{interaction.user.display_name}" отказался быть на ПВЕ')
        except Exception as error:
            await interaction.respond('❌', delete_after=1)
            logger.error(
                f'При отправке отказа пользователем "{interaction.user.display_name}" '
                f'возникла ошибка "{error}"'
            )

class RaidChampionDominionApplication(Modal):
    """
    Модальное окно для ввода данных на заявку ПВЕ.
    """
    def __init__(self, min_gear_score: int | None = None, member: str | None = None):
        super().__init__(title='Заявка на ПВЕ', timeout=None)
        self.min_gear_score = min_gear_score
        self.member = member
        self.add_item(
            InputText(
                style=discord.InputTextStyle.short,
                label='Укажите ник персонажа, на котором пойдете',
                placeholder='Учитывай регистр (большие и маленькие буквы)',
                required=True,
                max_length=20
            )
        )

        self.add_item(
            InputText(
                style=discord.InputTextStyle.multiline,
                label='Укажи классы и роли, которыми пойдешь',
                placeholder='Если не заполнять, значит любой класс',
                required=False,
                max_length=80
            )
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(invisible=False, ephemeral=True)
            async with async_session_factory() as session:

                nickname: str = str(self.children[0].value)
                player_info = character_lookup(1, nickname)

                gear_score = player_info['gear_score']

                if int(gear_score) > 100 and int(gear_score) < self.min_gear_score:
                    logger.info(f'У игрока"{interaction.user.display_name}" ГС: "{gear_score:}", что меньше минимального: "{self.min_gear_score}"')
                    return await interaction.respond(
                        'Твоя заявка не будет принята, т.к. недостаточно ГС\n'
                        f'Минимальный необходимый ГС: {self.min_gear_score}',
                        delete_after=5
                    )
                if int(gear_score) < 100 :
                    logger.info(
                        f'Игрок: "{interaction.user.display_name}" оказался клоуном и ввел ГС = "{gear_score}"')
                    return await interaction.respond(
                        f'Блять, ты что КЛОУН?:clown:'
                        f'\nВведи нормальный ГС, пример: {self.min_gear_score}',
                        delete_after=5
                    )
                class_role: str = str(self.children[1].value)
                logger.info(f'{self.member}')
                if not class_role:
                    class_role = 'Любой класс'

                if self.member != nickname:
                    class_role = f"({nickname}) {class_role}"

                guild = interaction.user.mutual_guilds[0]
                member: discord.Member = guild.get_member(interaction.user.id)
                field_index = 0 if discord.utils.get(member.roles, name=PVE_ROLE) else 1
                start_rcd_message_obj = await pve_app_orm.get_message_data_obj(
                    session=session,
                    pk=StaticNamesPve.START_PVE_MESSAGE
                )
                rcd_list_channel_obj = await pve_app_orm.get_message_data_obj(
                    session=session,
                    pk=StaticNamesPve.PVE_LIST_CHANNEL
                )
                rcd_list_channel: discord.TextChannel = guild.get_channel(rcd_list_channel_obj.message_id)
                start_rcd_message: discord.Message = (
                    await rcd_list_channel.fetch_message(start_rcd_message_obj.message_id)
                )

                during_embed: discord.Embed = start_rcd_message.embeds[0]
                field_value = during_embed.fields[field_index].value
                pattern = re.compile(rf'{member.mention}: (🟡|🔴)')
                match = pattern.search(field_value)
                if match:
                    new_value = field_value.replace(
                        match.group(0), f'{member.mention}: {class_role} ({int(float(gear_score)):,})'
                    )
                else:
                    new_value = field_value + f'\n{member.mention}: {class_role} ({int(float(gear_score)):,})'
                during_embed.fields[field_index].value = new_value
                await start_rcd_message.edit(embed=during_embed)
                await pve_app_orm.insert_appmember_id(session, interaction.user.id)
                await session.commit()
                if interaction.channel.type.value == 1:
                    await interaction.message.delete()
                await interaction.respond(
                    '_Заявка принята ✅_',
                    delete_after=1
                )
                logger.info(f'Принята заявка на ПВЕ от "{interaction.user.display_name}"')
        except Exception as error:
            await interaction.respond('❌', delete_after=1)
            logger.error(
                f'При отправке заявки на РЧД пользователем '
                f'"{interaction.user.display_name}" произошла ошибка "{error}"'
            )

class PVECommentModal(Modal):
    """
    Модальное окно для ввода комментариев к выбранным игрокам в ПВЕ.
    """

    def __init__(self, index: int, users: list[discord.User], select_view: View):
        super().__init__(title="Ввод комментариев для ПВЕ", timeout=None)
        self.index = index
        self.users = users
        self.select_view = select_view

        for user in self.users:
            self.add_item(
                InputText(
                    style=InputTextStyle.short,
                    label=f"Комментарий для {user.display_name}",
                    placeholder="Кто он нахуй такой",
                    required=False,
                    max_length=50
                )
            )

    async def callback(self, interaction: Interaction):
        await interaction.response.defer(invisible=False, ephemeral=True)

        formatted_users_strings = []
        users_ids = []

        for i, user in enumerate(self.users):
            comment = str(self.children[i].value).strip()
            if comment:
                formatted_users_strings.append(f"{user.mention} ({comment})")
            else:
                formatted_users_strings.append(f"{user.mention}")
            users_ids.append(str(user.id))

        await self.select_view.update_embed(
            interaction,
            value=", ".join(formatted_users_strings),
            members_id=",".join(users_ids)
        )


class SelectMemberView(View):
    """
    Меню для выбора пользователей в РЧД список.
    """

    def __init__(self, index: int) -> None:
        super().__init__(timeout=None)
        self.index: int = index

    @select(
        select_type=ComponentType.user_select,
        min_values=1,
        max_values=1,
        placeholder='Выбери игроков...',
        custom_id="SelectPve"
    )
    async def select_callback(self, select: Select, interaction: Interaction):
        try:
            async with async_session_factory() as session:
                pve_list_message_obj = await pve_app_orm.get_message_data_obj(
                    session=session,
                    pk=StaticNamesPve.PVE_LIST_MESSAGE
                )
                pve_list_message = (
                    await interaction.channel.fetch_message(pve_list_message_obj.message_id)
                )
                during_embed = pve_list_message.embeds[0]
                check_set: set[str] = set()

                if during_embed and during_embed.fields:
                    for field in during_embed.fields:
                        if field.value:
                            for value in field.value.split(','):
                                clean_value = value.split('(')[0].strip()
                                if clean_value:
                                    check_set.add(clean_value)

                for user in select.values:
                    if user.mention in check_set:
                        return await interaction.respond(
                            '_Повторно добавлять одного и того же нельзя, проверь списки! ❌_',
                            delete_after=3
                        )
                await interaction.response.send_modal(
                    PVECommentModal(index=self.index, users=select.values, select_view=self)
                )
        except Exception as error:
            await interaction.respond('❌', delete_after=1)
            logger.error(
                f'При выборе игроков возникла ошибка "{error}"'
            )

    @button(label='Очистить', style=ButtonStyle.gray, custom_id='ОчиститьПве')
    async def button_callback(self, button: Button, interaction: Interaction):
        await interaction.response.defer(invisible=False, ephemeral=True)
        await self.update_embed(interaction, '', None)

    async def update_embed(
        self,
        interaction: Interaction,
        value: str,
        members_id: str | None
    ) -> None:
        try:
            async with async_session_factory() as session:
                pve_list_message_obj = await pve_app_orm.get_message_data_obj(
                        session=session,
                        pk=StaticNamesPve.PVE_LIST_MESSAGE
                    )
                pve_list_message = await interaction.channel.fetch_message(pve_list_message_obj.message_id)

                during_embed = pve_list_message.embeds[0]
                old_value = during_embed.fields[self.index].value
                if old_value and value:
                    during_embed.fields[self.index].value = f"{old_value}, {value}"
                else:
                    during_embed.fields[self.index].value = value if value else ""
                role = INDEX_CLASS_ROLE.get(self.index)

                if not members_id:
                    try:
                        await pve_app_orm.delete_from_notice_list(session, role=role)
                    except ValueError:
                        pass
                else:
                    await pve_app_orm.insert_members_to_notice_list(
                        session, members_id=members_id, role=role
                    )

                await pve_list_message.edit(embed=during_embed)
                await session.commit()
                try:
                    await interaction.delete_original_response()
                except Exception:
                    pass
        except Exception as error:
            await interaction.respond('❌', delete_after=1)
            logger.error(f'При обработке игроков возникла ошибка "{error}"')
