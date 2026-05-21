from discord import Embed

from core import (
    ATTENTION, RCD_LIST_IMAGE_URL, INDEX_CLASS_ROLE,
    EXCLAMATION_MARK_URL, PVE_URL, TRANSLATION_ROLES
)


def start_pve_embed(date: str, min_gearscore: str) -> Embed:
    """
    Функция для создания вложения о старте ПВЕ заявок.
    """
    embed = Embed(
        title=f'_**Заявки на ПВЕ (PVE Applications)\n{date}**_',
        description=(
            f'_Минимальный ГС (min gearscore): {min_gearscore}\n'
            'Тыкай на кнопку ниже, чтобы подать заявку на ПВЕ!\n\n'
            'Click the button below to submit your PVE application!_ ⬇️'
        ),
        color=0x9900ff
    )
    embed.set_thumbnail(url=PVE_URL)
    return embed

def app_list_embed(date: str) -> Embed:
    """
    Функция для создания вложения о списке поданных ПВЕ заявок.
    """
    embed = Embed(
        title=f'_**Список поданных заявок на ПВЕ\n{date}**_',
        color=0x9900ff
    )
    embed.add_field(
        name='=========================================',
        value='',
        inline=False
    )
    embed.set_thumbnail(url=RCD_LIST_IMAGE_URL)
    return embed

def pve_list_embed(date: str) -> Embed:
    """
    Функция для создания вложения о финальном списке ПВЕ.
    """
    embed = Embed(
        title=f'_**Список ПВЕ {date}**_',
        color=0x9900ff
    )
    for role in INDEX_CLASS_ROLE.values():
        embed.add_field(
            name=role,
            value='',
            inline=False
        )
    embed.set_thumbnail(url=RCD_LIST_IMAGE_URL)
    return embed

def pve_notification_embed(
    interaction_user: str,
    date: str,
    jump_url: str | None,
    pve_role: str,
    comment:str | None
) -> Embed:
    """
    Функция для создания вложения о включении пользователя в список ПВЕ.
    """
    delete_notification_ru = "-# Сообщение автоматически удалится через 3 часа!"
    delete_notification_en = "-# The message will be automatically deleted in 3 hours!"

    role_ru = pve_role[:-2]
    
    embed = Embed(
        title=f'_**ПВЕ (PVE)\n{date}**_',
        description=(
            '_**Сообщаем то, что тебя включили в список ПВЕ!**'
            '\n'
            '**We inform you that you have been included in the PVE list!**'
            '\n\n'
            f'Требуемая роль: **{comment[1:-1]}**'
            '\n'
            f'Требуемый класс: **{role_ru}**'
            '\n\n'
            f'Если по какой-то причине ты не можешь присутствовать, отпишись {interaction_user}❗'
            '\n'
            f'If for some reason you cannot attend, message {interaction_user}❗'
            '\n\n'
            'Ссылка на список ПВЕ'
            '\n'
            'Link to the PVE list'
            '\n\n'
            f'{jump_url}_'
            '\n\n'
            f'{delete_notification_ru}'
            '\n'
            f'{delete_notification_en}'
        ),
        color=0x9900ff
    )
    embed.set_thumbnail(url=PVE_URL)
    return embed

def mailing_notification_embed(date: str) -> Embed:
    """
    Функция для отправки уведомления о рассылке.
    """
    embed = Embed(
        title=ATTENTION,
        description=(
            f'_**Сообщаем то, что уведомления участникам ПВЕ из списка на {date} были разосланы! '
            'Если бот не прислал вам сообщение, значит вы не попали в список!**_'
        ),
        color=0x9900ff
    )
    embed.set_thumbnail(url=EXCLAMATION_MARK_URL)
    return embed

def publish_pve_embed(date: str) -> Embed:
    """
    Функция для создания вложения с публикацией списка РЧД.
    """
    embed = Embed(
        title=f'_**Список ПВЕ (PVE List)\n{date}**_',
        color=0x9900ff
    )
    embed.set_thumbnail(url=PVE_URL)
    return embed