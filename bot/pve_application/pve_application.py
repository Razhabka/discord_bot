import discord
from discord.ext import commands
from loguru import logger

from core import LEADER_ROLE, OFICER_ROLE, TREASURER_ROLE
from .discord_ui import PVEDate


@commands.slash_command()
@commands.has_any_role(LEADER_ROLE, OFICER_ROLE, TREASURER_ROLE)
async def pve_application(ctx: discord.ApplicationContext) -> None:
    """
    Команда для запуска кнопки старта ПВЕ заявок.
    """
    try:
        await ctx.response.send_modal(PVEDate())
        logger.info(
            f'Команда "/pve_application" вызвана пользователем'
            f'"{ctx.user.display_name}"!'
        )
    except Exception as error:
        logger.error(
            f'Ошибка при вызове команды "/pve_application"! '
            f'"{error}"'
        )


@pve_application.error
async def pve_application_error(
    ctx: discord.ApplicationContext,
    error: Exception
) -> None:
    """
    Обрабатывать ошибки, возникающие
    при выполнении команды заявок на ПВЕ.
    """
    if isinstance(error, commands.errors.MissingAnyRole):
        await ctx.respond(
            'Команду может вызвать только "Лидер, Казначей или Офицер"!',
            ephemeral=True,
            delete_after=10
        )
    elif isinstance(error, commands.errors.PrivateMessageOnly):
        await ctx.respond(
            'Команду нельзя вызывать в личные сообщения бота!',
            ephemeral=True,
            delete_after=10
        )
    else:
        raise error


def setup(bot: discord.Bot):
    bot.add_application_command(pve_application)
