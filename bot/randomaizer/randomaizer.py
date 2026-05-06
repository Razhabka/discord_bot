import discord
from discord.ext import commands
from discord.ui import Modal, InputText, View, button
from loguru import logger

from .embeds import number_range, nickname_range
from .functions import rand_choice
from core import (
    DEAFAULT_RANDOMISE_VALUE, WRONG_PARMS,
    LEADER_ROLE, OFICER_ROLE, TREASURER_ROLE
)


class RandomModal(Modal):
    """
    Модальное окно для ввода значения,
    диапазон чисел или никнеймы через разделитель.

    Returns:
    --------
        None
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, title='Рандомайзер', timeout=None)

        self.add_item(
            InputText(
                style=discord.InputTextStyle.multiline,
                label='Параметры для рандомайзера',
                placeholder='Необязательно(если пусто то, рандом число 1-100)',
                max_length=1000,
                required=False
            )
        )

    async def callback(self, interaction: discord.Interaction):
        if len(self.children[0].value) == 0:
            if not rand_choice(DEAFAULT_RANDOMISE_VALUE):
                return await interaction.respond(
                    WRONG_PARMS,
                    ephemeral=True,
                    delete_after=15
                )
            return await interaction.respond(
                embed=number_range(
                    rand_choice(DEAFAULT_RANDOMISE_VALUE),
                    DEAFAULT_RANDOMISE_VALUE
                ),
                delete_after=30
            )
        else:
            if not rand_choice(self.children[0].value):
                return await interaction.respond(
                    WRONG_PARMS,
                    ephemeral=True,
                    delete_after=15
                )
            if not isinstance(rand_choice(self.children[0].value), int):
                return await interaction.respond(
                    embed=nickname_range(rand_choice(self.children[0].value)),
                    delete_after=30
                )
            return await interaction.respond(
                embed=number_range(
                    rand_choice(self.children[0].value),
                    self.children[0].value
                ),
                delete_after=30
            )


class RandomButton(View):
    """
    Кнопка для запуска модального окна рандомайзера.

    Returns:
    --------
        None
    """
    def __init__(
        self,
        timeout: float | None = None
    ):
        super().__init__(timeout=timeout)

    @button(
        label='Рандомайзер', style=discord.ButtonStyle.green,
        emoji='🎲', custom_id='Рандомайзер'
    )
    async def callback(
        self,
        button: discord.ui.Button,
        interaction: discord.Interaction
    ):
        await interaction.response.send_modal(RandomModal())


@commands.slash_command()
@commands.has_any_role(LEADER_ROLE, OFICER_ROLE, TREASURER_ROLE)
async def random(
    ctx: discord.ApplicationContext,
    channel: discord.Option(
        discord.TextChannel,
        description='Куда отправить кнопку?',
        name_localizations={'ru':'текстовый_канал'}
    ), # type: ignore
    message_id: discord.Option(
        str,
        description='ID сообщения, в котором есть кнопка кнопка',
        name_localizations={'ru':'id_сообщения'},
        required=False
    )  # type: ignore
) -> None:
    """
    Команда для отправки кнопки рандомайзера.
    """
    try:
        if message_id:
            message = ctx.channel.get_partial_message(int(message_id))
            await message.edit(view=RandomButton())
            await ctx.respond(
                f'_Кнопка рандомайзера обновлена и снова работает в '
                f'канале {channel.mention}!_',
                ephemeral=True,
                delete_after=3
            )
        else:
            await channel.send(view=RandomButton())
            await ctx.respond(
                f'_Кнопка рандомайзера отправлена в канал '
                f'{channel.mention}!_',
                ephemeral=True,
                delete_after=3
            )
        logger.info(
            f'Команда "/random" вызвана пользователем'
            f'"{ctx.user.display_name}" в канал "{channel}"!'
        )
    except Exception as error:
        logger.error(
            f'При запуске команды /random возникла ошибка '
            f'"{error}"!'
        )


@random.error
async def random_error(
    ctx: discord.ApplicationContext,
    error: Exception
) -> None:
    """
    Обрабатывать ошибки, возникающие
    при выполнении команды запросов на выдачу доступа.
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
    bot.add_application_command(random)
