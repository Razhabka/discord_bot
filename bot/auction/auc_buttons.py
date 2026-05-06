import asyncio
import re
from datetime import datetime, timedelta

import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, InputText
from loguru import logger

from .embeds import start_auc_embed, results_embed, outbid_embed
from .functions import (
    convert_bid,
    convert_to_mention,
    convert_sorted_message,
    seconds_until_date,
    convert_bid_back
)
from core import MIN_BID_VALUE, NOT_SOLD, LEADER_NICKNAME


final_time: dict[str, datetime] = {}
channel_last_message_dict: dict[str, discord.Message] = {}


class StartAucModal(Modal):
    """
    Модальное окно для ввода данных для старта аукциона.
    """
    def __init__(
        self,
        channel: discord.TextChannel
    ):
        super().__init__(title='Параметры аукциона', timeout=None)
        self.channel = channel

        self.add_item(
            InputText(
                style=discord.InputTextStyle.short,
                label='Укажи название аукциона',
                placeholder='название лотов для розыгрыша'
            )
        )

        self.add_item(
            InputText(
                style=discord.InputTextStyle.short,
                label='Укажи количество разыгрываемых лотов',
                placeholder='кол-во лотов может быть от 1 до 25',
                min_length=1,
                max_length=2
            )
        )

        self.add_item(
            InputText(
                style=discord.InputTextStyle.short,
                label='Укажи начальную ставку',
                placeholder=f'минимальная ставка {MIN_BID_VALUE}',
            )
        )

        self.add_item(
            InputText(
                style=discord.InputTextStyle.short,
                label='Укажи дату и время в формате ДД.ММ ЧЧ:ММ',
                placeholder='ДД.ММ ЧЧ:ММ',
                max_length=11
            )
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(invisible=False, ephemeral=True)

        name_auc: str = str(self.children[0].value)
        lot_amount: int = int(self.children[1].value)
        start_bid: int = int(self.children[2].value)
        target_date_time: str = str(self.children[3].value)
        start_auc_user: discord.Member = interaction.user
        user_mention: str = start_auc_user.mention
        button_manager = View(timeout=None)
        button_mentions: dict[str, str] = {}
        today: datetime = datetime.now()

        if lot_amount < 1 or lot_amount > 25:
            return await interaction.respond(
                '_Количество лотов должно быть от 1 до 24_',
                delete_after=10
            )

        if final_time.get(name_auc) or channel_last_message_dict.get(name_auc):
            name_auc += ' 😊'

        try:
            stop_time: datetime = today + timedelta(
                seconds=seconds_until_date(target_date_time)
            )
            final_time[name_auc] = stop_time
        except Exception as error:
            await interaction.respond(
                'Неверный формат. Ожидался ДД.ММ ЧЧ:ММ'
            )
            logger.error(
                f'При вводе даты в команду аукциона возникла ошибка {error}'
            )

        for index in range(lot_amount):
            button_manager.add_item(BidButton(
                start_bid=start_bid,
                start_auc_user=start_auc_user,
                lot_amount=lot_amount,
                name_auc=name_auc,
                button_mentions=button_mentions,
                button_manager=button_manager,
                index=index
            ))

        await self.channel.send(embed=start_auc_embed(
                user_mention=user_mention,
                name_auc=name_auc,
                stop_time=stop_time,
                lot_count=lot_amount,
                first_bid=convert_bid(start_bid)
            ),
            view=button_manager)
        await interaction.respond('✅', delete_after=1)
        channel_last_message_dict[name_auc] = self.channel.last_message

        try:
            await discord.utils.sleep_until(stop_time - timedelta(seconds=60))
            await check_timer(
                view=button_manager,
                user_mention=user_mention,
                name_auc=name_auc,
                lot_amount=lot_amount,
                final_time=final_time,
                button_mentions=button_mentions
            )
        except Exception:
            logger.error("Аукцион был отменён. Сообщение удалёно")


class PassBid(Modal):
    def __init__(
        self,
        btn_label: str,
        start_bid: int,
        start_auc_user: discord.Member,
        lot_amount: int,
        name_auc: str,
        button_mentions: dict[str, str],
        button_manager: View,
        index: int,
        button_message: discord.Message
    ):
        super().__init__(title='Укажи свою ставку', timeout=None)
        self.btn_label = btn_label
        self.start_bid = start_bid
        self.start_auc_user = start_auc_user
        self.lot_amount = lot_amount
        self.name_auc = name_auc
        self.button_mentions = button_mentions
        self.button_manager = button_manager
        self.index = index
        self.button_message = button_message

        self.add_item(
            InputText(
                style=discord.InputTextStyle.short,
                label='Ставка кратная 100.000 и не более 99.9M',
                placeholder='Внимательно считаем количество ноликов!',
                min_length=6,
                max_length=8
            )
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):
        await interaction.response.defer(invisible=False, ephemeral=True)

        try:
            if not self.children[0].value.isdigit():
                return await interaction.respond(
                    '_Указанное значение не является положительным числом! ❌_',
                    delete_after=2
                )

            if int(self.children[0].value) % 100_000 != 0:
                return await interaction.respond(
                    '_Ставка должна быть кратна 100.000! ❌_',
                    delete_after=2
                )

            select_bid: int = int(self.children[0].value)
            reserve_button_manager = self.button_manager
            user_name: str = interaction.user.display_name
            user_mention: str = interaction.user.mention
            nowtime: datetime = datetime.now()
            sixty_seconds: timedelta = timedelta(seconds=60)
            plus_minute: datetime = nowtime + sixty_seconds
            during_button_label: str = self.btn_label

            if len(self.button_manager.children) == 0:
                await self.button_message.edit(view=reserve_button_manager)
                await interaction.respond(
                    f'В момент обработки, сделанной ставки возникла ошибка!'
                    f'Бот не сломался, попробуй сделать ставку снова. Если '
                    f'данное сообщение появляется снова, обратись к '
                    f'{LEADER_NICKNAME}, для скорейшего решения проблемы!',
                    delete_after=10
                )
                await self.start_auc_user.send(
                    f'_Сигнал об ошибке во время аукциона! '
                    f'При попытке пользователя "{interaction.user.display_name}" '
                    f'сделать ставку, произошла неизвестная ошибка! '
                    f'Отработала резервная view._'
                )
                logger.error(
                    f'При попытке сделать ставку пользователем '
                    f'"{interaction.user.mention}" возникла неизвестная ошибка, '
                    f'которая сносит кнопки. Во "view" сложили резервную копию.'
                )

            label_parts = self.btn_label.split()
            full_label_number = convert_bid_back(label_parts[0])
            error_response = {
                'low_bid': '_Ставка должна быть большей текущей! ❌_',
                'large_bid': (
                    '_Сработала защита, твоя ставка больше текущей на 5 000 000.⚠️\n'
                    'Ты точно не указал не ошибся с лишним ноликом?\n'
                    'Сделай ставку меньше, разница с текущей ставкой должна быть '
                    'не более 5 миллионов!👌_'
                )
            }

            if (
                self.button_manager.children[self.index].style
                == discord.ButtonStyle.green and full_label_number > select_bid
            ) or (full_label_number >= select_bid and len(label_parts) > 1):
                return await interaction.respond(
                    error_response.get('low_bid'),
                    delete_after=5
                )

            if (select_bid - full_label_number) > 5_000_000:
                return await interaction.respond(
                    error_response.get('large_bid'),
                    delete_after=4
                )

            self.button_manager.children[self.index].label = f'{convert_bid(select_bid)} {interaction.user.display_name}'
            self.button_manager.children[self.index].style = discord.ButtonStyle.blurple
            self.button_mentions[user_name] = user_mention

            if (final_time.get(self.name_auc) - nowtime) < sixty_seconds:
                await self.button_message.edit(
                    view=self.button_manager,
                    embed=start_auc_embed(
                        user_mention=self.start_auc_user.mention,
                        name_auc=self.name_auc,
                        stop_time=plus_minute,
                        lot_count=self.lot_amount,
                        first_bid=convert_bid(self.start_bid)
                    )
                )
                final_time[self.name_auc] = plus_minute
            logger.info(
                f'Пользователь "{interaction.user.display_name}" сделал ставку'
            )

            if len(label_parts) > 1:
                time_of_bid = None
                url = self.button_message.jump_url
                previous_bidder_name = during_button_label.split(' ', 1)[1].strip()
                if previous_bidder_name == user_name:
                    previous_bidder_name = ''

                during_member: discord.Member | None = None
                if interaction.guild and previous_bidder_name:
                    during_member = discord.utils.find(
                        lambda m: m.display_name == previous_bidder_name,
                        interaction.guild.members
                    )
                    if during_member is None:
                        during_member = discord.utils.get(
                            interaction.guild.members,
                            name=previous_bidder_name
                        )
                    if during_member is None:
                        during_member = discord.utils.get(
                            interaction.guild.members,
                            nick=previous_bidder_name
                        )
                    if during_member is None:
                        mention_value = self.button_mentions.get(previous_bidder_name)
                        if mention_value:
                            member_id_match = re.search(r'\d+', mention_value)
                            if member_id_match:
                                during_member = interaction.guild.get_member(
                                    int(member_id_match.group(0))
                                )
                if (datetime.now() + timedelta(seconds=60)) > final_time.get(self.name_auc) > datetime.now():
                    time_of_bid = plus_minute
                    delete_after = 60
                else:
                    time_of_bid = final_time.get(self.name_auc)
                    delete_after = 1800
                if during_member is not None:
                    try:
                        await during_member.send(
                            embed=outbid_embed(
                                url=url, stop_time=time_of_bid,
                                delete_after=delete_after
                            ),
                            delete_after=delete_after
                        )
                    except discord.Forbidden:
                        logger.warning(
                            f'Пользователю "{during_member.display_name}" запрещено отправлять сообщения'
                        )
                    logger.info(
                        f'Ставку "{during_member.display_name}" перебил "{interaction.user.display_name}"!'
                    )
                elif previous_bidder_name:
                    logger.warning(
                        f'Не удалось найти пользователя "{previous_bidder_name}" '
                        f'для отправки уведомления о перебитой ставке.'
                    )

            await self.button_message.edit(view=self.button_manager)
            await interaction.respond('✅', delete_after=1)
        except Exception as error:
            await interaction.respond('❌', delete_after=1)
            logger.error(
                f'При обработке нажатия на кнопку ставки '
                f'возникла ошибка "{error}"'
            )


class BidButton(Button):
    """Кнопка со ставкой и никнеймом, сделавшего ставку"""
    def __init__(
        self,
        start_bid: int,
        start_auc_user: discord.Member,
        lot_amount: int,
        name_auc: str,
        button_mentions: dict[str, str],
        button_manager: View,
        index: int,
    ):
        super().__init__(
            style=discord.ButtonStyle.green,
            label=convert_bid(start_bid)
        )
        self.start_bid = start_bid
        self.start_auc_user = start_auc_user
        self.lot_amount = lot_amount
        self.name_auc = name_auc
        self.button_mentions = button_mentions
        self.button_manager = button_manager
        self.index = index

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.send_modal(
                PassBid(
                    btn_label=self.label,
                    start_bid=self.start_bid,
                    start_auc_user=self.start_auc_user,
                    lot_amount=self.lot_amount,
                    name_auc=self.name_auc,
                    button_mentions=self.button_mentions,
                    button_manager=self.button_manager,
                    index=self.index,
                    button_message=interaction.message
                ))
        except Exception as error:
            await interaction.respond('❌', delete_after=1)
            logger.error(
                f'При обработке нажатия на кнопку ставки '
                f'возникла ошибка "{error}"'
            )


@commands.slash_command()
@commands.has_role('Аукцион')
async def go_auc(
    ctx: discord.ApplicationContext,
    channel: discord.Option(
        discord.TextChannel,
        description='Текстовый канал, в котором будет аукцион',
        name_localizations={'ru': 'канал'}
    ),  # type: ignore
) -> None:
    """
    Команда для запуска аукциона.
    """
    try:
        await ctx.response.send_modal(StartAucModal(channel=channel))
    except Exception as error:
        await ctx.respond('❌', delete_after=1)
        logger.error(
                f'При попытке запустить аукцион командой /go_auc '
                f'возникло исключение "{error}"'
            )


@go_auc.error
async def go_auc_error(
    ctx: discord.ApplicationContext, error: Exception
) -> None:
    """
    Обработчик ошибок для команды go_auc.
    """
    if isinstance(error, commands.errors.MissingRole):
        await ctx.respond(
            '_Команду может вызвать только Аукционер! ❌_',
            ephemeral=True,
            delete_after=10
        )
    elif isinstance(error, commands.errors.PrivateMessageOnly):
        await ctx.respond(
            '_Команду нельзя вызывать в личные сообщения бота!❌ _',
            ephemeral=True,
            delete_after=10
        )
    else:
        raise error


async def check_timer(
    view: View,
    user_mention: str,
    name_auc: str,
    lot_amount: int,
    final_time: dict,
    button_mentions: dict
) -> None:
    """
    Функция для полинга таймера, которая автоматически завершает аукцион.
    """
    while True:
        if final_time.get(name_auc) > datetime.now():
            await asyncio.sleep(0.5)
        else:
            await auto_stop_auc(
                view=view,
                user_mention=user_mention,
                name_auc=name_auc,
                lot_amount=lot_amount,
                button_mentions=button_mentions
            )
            break


async def auto_stop_auc(
        view: View,
        user_mention: str,
        name_auc: str,
        lot_amount: int,
        button_mentions: dict
) -> None:
    """
    Функция для автозавершения аукциона.
    """
    view.disable_all_items()
    label_values = [btn.label for btn in view.children]
    convert_label_values = convert_to_mention(
        label_values, button_mentions
    )
    count_not_bid = convert_label_values.count(NOT_SOLD)
    removed_not_bid: list = []
    for i in convert_label_values:
        if i != NOT_SOLD:
            removed_not_bid.append(i)
    sorted_list = sorted(
        removed_not_bid,
        key=convert_sorted_message,
        reverse=True
    )
    for _ in range(count_not_bid):
        sorted_list.append(NOT_SOLD)
    message = (
        '\n'.join([f'{i+1}. {val}' for i, val in enumerate(
            sorted_list
        )])
    )
    view.clear_items()
    try:
        await channel_last_message_dict.get(name_auc).edit(
            view=view,
            embed=results_embed(
                results_message=message,
                user_mention=user_mention,
                name_auc=name_auc,
                lot_amount=lot_amount
            )
        )
        logger.info(
            'Аукцион успешно завершён!'
        )
    except Exception as error:
        logger.error(
            f'При автоматическом завершении аукциона возникла ошибка '
            f'"{error}"'
        )
    finally:
        channel_last_message_dict.pop(name_auc)
        final_time.pop(name_auc)


def setup(bot: discord.Bot):
    bot.add_application_command(go_auc)
