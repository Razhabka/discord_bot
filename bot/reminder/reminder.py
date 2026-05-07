from datetime import datetime
import re

import discord
from discord.ext import commands
from discord.ui import InputText, Modal
from loguru import logger

from .functions import add_remind_to_db, delete_remind_from_db
from .embeds import remind_embed, remind_send_embed
from core import (
    LEADER_ROLE, OFICER_ROLE, TREASURER_ROLE,
    SERGEANT_ROLE, VETERAN_ROLE
)


class StartRemindModal(Modal):
    """
    Модальное окно для ввода данных напоминания.
    """
    def __init__(self, target_member: discord.Member):
        self.target_member = target_member
        super().__init__(title=f'Напоминаниме для {target_member.display_name}', timeout=None)

        self.add_item(
            InputText(
                style=discord.InputTextStyle.multiline,
                label='Укажи содержание сообщения',
                placeholder='Не более 500 символов',
                max_length=500
            )
        )

        self.add_item(
            InputText(
                style=discord.InputTextStyle.short,
                label='Укажи дату отправки в формате "ДД.ММ"',
                placeholder='ДД.ММ',
                max_length=5
            )
        )

        self.add_item(
            InputText(
                style=discord.InputTextStyle.short,
                label='Укажи время отправки в формате "ЧЧ:ММ"',
                placeholder='ЧЧ:ММ',
                max_length=5
            )
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(invisible=False, ephemeral=True)
        message: str = str(self.children[0].value)
        date_str: str = str(self.children[1].value)
        time_str: str = str(self.children[2].value)

        # Регулярное выражение для проверки даты в формате ДД.ММ
        date_pattern = r'^([0-2][0-9]|3[0-1])[.,/](0[1-9]|1[0-2])$'
        date_match = re.match(date_pattern, date_str)

        # Регулярное выражение для проверки времени в формате ЧЧ:ММ
        time_pattern = r'^([0-1][0-9]|2[0-3])[:;]([0-5][0-9])$'
        time_match = re.match(time_pattern, time_str)

        if not date_match:
            return await interaction.respond(
                'Неправильный формат даты. Пожалуйста, используйте формат ДД.ММ',
                delete_after=10
            )

        if not time_match:
            return await interaction.respond(
                'Неправильный формат времени. Пожалуйста, используйте формат ЧЧ:ММ',
                delete_after=10
            )

        try:
            day, month = map(int, date_match.groups())
            hour, minute = map(int, time_match.groups())
            current_year = datetime.now().year
            remind_date = datetime(
                year=current_year,
                month=month,
                day=day,
                hour=hour,
                minute=minute,
            )
            if remind_date < datetime.now():
                remind_date = remind_date.replace(year=current_year + 1)
            convert_remind_date = discord.utils.format_dt(remind_date, style="F")
            add_remind_to_db(interaction.user.id, message, remind_date, self.target_member.id)
            await interaction.respond(
                embed=remind_embed(convert_remind_date, message, self.target_member.display_name),
                delete_after=20
            )
            logger.info(
                f'Пользователю {self.target_member.display_name} создали напоминалку'
                f'на {remind_date}!'
            )
            await discord.utils.sleep_until(remind_date)
            try:
                await self.target_member.send(
                    embed=remind_send_embed(convert_remind_date, message, self.target_member.display_name),
                    delete_after=3600
                )
                logger.info(
                    f'Пользователь {self.target_member.display_name} получил напоминалку!'
                )
            except discord.Forbidden:
                logger.warning(f'Пользователю "{self.target_member.display_name}" запрещено отправлять сообщения')
                delete_remind_from_db(self.target_member.id, remind_date)
        except Exception as error:
            logger.error(
                f'Пользователь {self.target_member.display_name} попытался сделать напоминание '
                f'но получил ошибку {error}!'
            )


@commands.slash_command()
@commands.has_any_role(
    LEADER_ROLE, OFICER_ROLE, TREASURER_ROLE, SERGEANT_ROLE, VETERAN_ROLE
)
async def remind(ctx: discord.ApplicationContext,
                 member: discord.Member = None
                 ) -> None:
    """
    Команда для отправки сообщения с напоминанием.
    """
    try:
        target_member = member or ctx.author
        await ctx.response.send_modal(StartRemindModal(target_member))
    except Exception as error:
        logger.error(
                f'При попытке запустить аукцион командой /remind '
                f'возникло исключение "{error}"'
            )


@remind.error
async def remind_error(
    ctx: discord.ApplicationContext,
    error: Exception
) -> None:
    """
    Обрабатывать ошибки, возникающие
    при выполнении команды remind.
    """
    if isinstance(error, commands.errors.MissingAnyRole):
        await ctx.respond(
            'Команду может вызвать только "Согильдеец"!',
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
    bot.add_application_command(remind)
