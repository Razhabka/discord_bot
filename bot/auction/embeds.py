from datetime import datetime

import discord

from core import ATTENTION, AUCTION_IMAGE_URL, REMIND


def start_auc_embed(
    user_mention: str,
    name_auc: str,
    stop_time: datetime,
    lot_count: int,
    first_bid: str
) -> discord.Embed:
    """
    Создает встраиваемое сообщение об открытии аукциона.
    """
    embed = discord.Embed(
        title=ATTENTION,
        description=(
            f'_**{user_mention} начал аукцион "{name_auc}"!**\n\n'
            f'Количество лотов: {lot_count}.\n'
            f'Начальная ставка: {first_bid}.\n\n'
            f'**Аукцион закончится\n'
            f'<t:{int(stop_time.timestamp())}:R>!**_'
        ),
        color=0xfffb00
    )
    embed.set_thumbnail(url=AUCTION_IMAGE_URL)
    return embed


def results_embed(
    results_message: str,
    user_mention: str,
    name_auc: str,
    lot_amount: int
) -> discord.Embed:
    """
    Создает встраиваемое сообщение с результатами аукциона.
    """
    embed = discord.Embed(
        title=ATTENTION,
        description=(
            f'_**{user_mention} провёл аукцион "{name_auc}"!\n\n'
            f'Аукцион был завершён в {discord.utils.format_dt(datetime.now(), style="F")}!**\n\n'
            f'Количество лотов: {lot_amount}.\n\n'
            f'**Результаты аукциона:**\n'
            f'{results_message}_'
        ),
        color=0xfffb00
    )
    embed.set_thumbnail(url=AUCTION_IMAGE_URL)
    return embed


def outbid_embed(
    url: str,
    stop_time: datetime,
    delete_after: int
) -> discord.Embed:
    """
    Создает встраиваемое сообщение о перебивании ставки.
    """
    embed = discord.Embed(
        title=ATTENTION,
        description=(
            f'_**Твоя ставка на аукционе была перебита!\n'
            f'Аукцион закончится <t:{int(stop_time.timestamp())}:R>\n\n'
            f'{url}**_\n\n'
            f'-# Данное сообщение автоматически удалится через '
            f'{"минуту" if delete_after == 60 else "30 минут"}.'
        ),
        color=0xfffb00
    )
    embed.set_thumbnail(url=AUCTION_IMAGE_URL)
    return embed


def end_auc_notification_embed():
    """
    Создает встраиваемое сообщение о перебивании ставки.
    """
    embed = discord.Embed(
        title=REMIND,
        description=(
            '_**Что аукцион скоро завершится!\n\n'
            '❗❗❗ НЕ УПУСТИ СВОЮ СТАВКУ ❗❗❗**_.'
        ),
        color=0xfffb00
    )
    embed.set_thumbnail(url=AUCTION_IMAGE_URL)
    return embed
