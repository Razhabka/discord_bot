import discord

from core import PLAYING_DICES_URL_ICON


def number_range(value: str, ranje: str) -> discord.Embed:
    """
    Функция для создания вложения с рандомным числом в заданном диапазоне.
    """
    embed = discord.Embed(
        title='_Рандомайзер!_',
        description=f'_Диапазон чисел {ranje}._',
        color=0x00ff00
    )
    embed.add_field(
        name='_Твоё рандомное число:_',
        value=value,
        inline=False
    )
    embed.set_thumbnail(url=PLAYING_DICES_URL_ICON)
    return embed


def nickname_range(value: str) -> discord.Embed:
    """
    Функция для создания вложения с рандомным участником.
    """
    embed = discord.Embed(
        title='_Рандомайзер!_',
        color=0x00ff00
    )
    embed.add_field(
        name='_Участники:_',
        value=value,
        inline=False
    )
    embed.set_thumbnail(url=PLAYING_DICES_URL_ICON)
    return embed
