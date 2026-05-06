import discord

from core import ATTENTION, SMALL_GUILD_ICON_URL


def attention_embed(value: str) -> discord.Embed:
    """
    Функция для создания вложения с предупреждением.
    """
    embed = discord.Embed(
        title=ATTENTION,
        description=f'{value}',
        color=0xfffb00
    )
    embed.set_thumbnail(url=SMALL_GUILD_ICON_URL)
    return embed


def symbols_list_embed(
    banner_list: str = '',
    cape_list: str | None = None
) -> discord.Embed:
    """
    Функция для создания вложения с со списком за символы славы.
    """
    embed = discord.Embed(
        title='_Список знамён и накидок за чистый авторитет_',
        color=0x00ff29
    )
    embed.add_field(
        name='_Знамёна:_',
        value=f'_{banner_list}_',
        inline=True
    )
    if cape_list:
        embed.add_field(
            name='_Накидки:_',
            value=f'_{cape_list}_',
            inline=True
        )
    embed.set_thumbnail(url=SMALL_GUILD_ICON_URL)
    return embed
