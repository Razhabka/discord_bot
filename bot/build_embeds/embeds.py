from datetime import date, timedelta, datetime
import discord

from core import SMALL_GUILD_ICON_URL


# def attention_embed(header: str, message: str, color: int = 0xc00433) -> discord.Embed:
#     """
#     Функция для создания вложения с предупреждением.
#     """
#     embed = discord.Embed(
#         title=header,
#         description=f'{message}',
#         color=color
#     )
#     embed.set_thumbnail(url=SMALL_GUILD_ICON_URL)
#     return embed

def attention_embed(header: str, message: str, color: int = 0xc00433, link: str = SMALL_GUILD_ICON_URL) -> discord.Embed:
    """
    Функция для создания вложения с предупреждением.
    """
    embed = discord.Embed(
        title=header,
        description=f'{message}',
        color=color
    )
    embed.set_thumbnail(url=link)
    return embed


def symbols_list_embed(
    banner_list: str = '',
    cape_list: str | None = None,
    date: datetime | None = None,
) -> discord.Embed:
    """
    Функция для создания вложения с со списком за символы славы.
    """
    date_start = None
    if date:
        date_start = date
    else:
        date_start = date.today()

    next_week = date_start + timedelta(days=7)
    embed = discord.Embed(
        title=f'_Список знамён и чемпионских накидок за чистый авторитет_',
        color=0x5bd395
    )
    embed.add_field(
        name='_Знамёна:_',
        value=f'_{banner_list}_',
        inline=True
    )
    if cape_list:
        embed.add_field(
            name='_Чемпионские накидки:_',
            value=f'_{cape_list}_',
            inline=True
        )

    embed.add_field(
        name='\u200b',
        value=f'_*Все знамёна и чемпионские накидки выданы на период_ c {date_start} по {next_week} ✅',
        inline=False
    )
    embed.set_thumbnail(url=SMALL_GUILD_ICON_URL)
    return embed
