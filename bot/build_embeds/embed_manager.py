import base64
import json
import re
from datetime import datetime

import chardet
import discord
from discord.ext import commands
from discord.ui import Modal, InputText, View, select, button
from loguru import logger

from .functions import (
    validate_amount, generate_member_list, handle_selection,
    sort_nicknames_by_role
)
from .embeds import attention_embed, symbols_list_embed
from regular_commands.regular_commands import command_error
from core import LEADER_ROLE, OFICER_ROLE, TREASURER_ROLE, async_session_factory
from core.orm import authority_stat_orm


def _decode_text_file(bytes_data: bytes) -> str:
    detected = chardet.detect(bytes_data)
    encoding = detected['encoding'] if detected['encoding'] else 'utf-8'
    try:
        return bytes_data.decode(encoding)
    except UnicodeDecodeError:
        return bytes_data.decode('windows-1251')


def _decode_export_json(base64_value: str) -> dict:
    normalized = re.sub(r'\s+', '', base64_value)
    padding = len(normalized) % 4
    if padding:
        normalized += '=' * (4 - padding)

    decoded_data = base64.b64decode(normalized)
    decode_errors: list[Exception] = []

    for encoding in ('utf-8', 'windows-1251'):
        try:
            return json.loads(decoded_data.decode(encoding))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            decode_errors.append(error)

    raise ValueError(f'Failed to decode jsonBase64: {decode_errors[-1]}')


def _extract_block_datetime(export_block: str) -> tuple[int, str]:
    datetime_match = re.search(
        r't_b (?:dateTime|datetime)(.*?)t_e (?:dateTime|datetime)',
        export_block,
        re.S
    )
    if not datetime_match:
        raise ValueError('dateTime/datetime block not found inside exportData.')

    datetime_body = datetime_match.group(1)
    parts: dict[str, int] = {}
    for key in ('overallMs', 'y', 'm', 'd'):
        value_match = re.search(rf'(?m)^\s*{key}=(-?\d+)\s*$', datetime_body)
        if not value_match:
            raise ValueError(f'dateTime/datetime field "{key}" not found.')
        parts[key] = int(value_match.group(1))

    snapshot_date = f'{parts["y"]:04d}-{parts["m"]:02d}-{parts["d"]:02d}'
    return parts['overallMs'], snapshot_date


def _extract_latest_authority_data(content: str) -> tuple[int, str, list[tuple[str, int]]]:
    export_blocks = re.finditer(r't_b exportData(.*?)t_e exportData', content, re.S)
    latest_data: tuple[int, str, list[tuple[str, int]]] | None = None

    for block in export_blocks:
        block_text = block.group(1)
        try:
            overall_ms, snapshot_date = _extract_block_datetime(block_text)
        except ValueError:
            continue

        json_match = re.search(r'jsonBase64=l"([^"]+)"', block_text)
        if not json_match:
            continue

        decoded_json = _decode_export_json(json_match.group(1))
        check_data = decoded_json.get('check', [])
        if not isinstance(check_data, list):
            continue

        rows: list[tuple[str, int]] = []
        for item in check_data:
            if not isinstance(item, dict):
                continue

            name = item.get('name')
            authority_without = item.get('authorityWithout')
            if not isinstance(name, str):
                continue

            try:
                authority_value = int(authority_without)
            except (TypeError, ValueError):
                continue

            rows.append((name, authority_value))

        if not rows:
            continue

        if latest_data is None or overall_ms > latest_data[0]:
            latest_data = (overall_ms, snapshot_date, rows)

    if latest_data is None:
        raise ValueError('No valid exportData block with jsonBase64/authorityWithout found.')

    return latest_data

class AttentionMessage(Modal):
    """Модальное окно для отправки важного сообщения."""
    def __init__(self, channel: discord.TextChannel):
        super().__init__(title='Важное сообщение', timeout=None)
        self.channel = channel

        self.add_item(
            InputText(
                style=discord.InputTextStyle.short,
                label='Укажите заголовок',
                placeholder='Не более 100 символов',
                max_length=100,
                required=False
            )
        )
        self.add_item(
            InputText(
                style=discord.InputTextStyle.multiline,
                label='Укажи содержание сообщения',
                placeholder='Не более 4000 символов',
                max_length=4000
            )
        )
        self.add_item(
            InputText(
                style=discord.InputTextStyle.short,
                label='Укажите код цвета (HEX)',
                placeholder='Например: #ff0000 или 00ff29 (Оставь пустым для стандартного)',
                max_length=7,
                required=False
            )
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(invisible=False, ephemeral=True)
            header = self.children[0].value if self.children[0].value != "" else None
            message: str = str(self.children[1].value)
            raw_color: str = str(self.children[2].value).strip()
            embed_color = 0xc00433

            if raw_color:
                hex_color = raw_color.replace('#', '')
                try:
                    embed_color = int(hex_color, 16)
                except ValueError:
                    await interaction.respond(
                        '⚠️ Неверный формат цвета! Используйте HEX-код, например: `#ff0000` или `00ff00`. '
                        'Сообщение отправлено со стандартным цветом.',
                        ephemeral=True,
                        delete_after=7
                    )
            await self.channel.send(embed=attention_embed(header=header, message=message, color=embed_color))
            await interaction.respond('✅', delete_after=1)
        except Exception as error:
            logger.error(
                f'Пользователь {interaction.user.display_name} попытался сделать объявление '
                f'но получил ошибку {error}!'
            )


@commands.slash_command()
@commands.has_any_role(LEADER_ROLE, OFICER_ROLE, TREASURER_ROLE)
async def attention(
    ctx: discord.ApplicationContext,
    channel: discord.Option(
        discord.abc.GuildChannel,
        description='Куда отправить сообщение?',
        name_localizations={'ru':'текстовый_канал'},
        channel_types=[
            discord.ChannelType.text,
            discord.ChannelType.public_thread,
            discord.ChannelType.private_thread,
            discord.ChannelType.news_thread
        ]
    ),  # type: ignore
) -> None:
    """
    Команда для отправки сообщения с пометкой 'Внимание!'.
    """
    await ctx.response.send_modal(AttentionMessage(channel=channel))
    logger.info(
        f'Команда "/attention" вызвана пользователем '
        f'"{ctx.user.display_name}" в канал "{channel}"!'
    )
    await ctx.respond(
        f'_Сообщение отправлено в канал {channel.mention}!_',
        ephemeral=True,
        delete_after=3
    )


@attention.error
async def attention_error(
    ctx: discord.ApplicationContext,
    error: Exception
) -> None:
    """
    Обработчик ошибок для команды attention.
    """
    await command_error(ctx, error, "attention")


class SetNewDescription(Modal):
    """Модальное окно для установки нового описания embed"""
    def __init__(self, message_id: int, channel: discord.abc.GuildChannel, current_title: str | None, description: str | None, current_color: str | None) -> None:
        super().__init__(title='Укажи новое описание embed', timeout=None)
        self.message_id = message_id
        self.channel = channel

        self.add_item(
            InputText(
                style=discord.InputTextStyle.short,
                label='Укажите новый заголовок',
                placeholder= "Оставь пустым, чтобы убрать заголовок",
                max_length=100,
                required=False,
                value=current_title
            )
        )

        self.add_item(
            InputText(
                style=discord.InputTextStyle.multiline,
                label='Укажи содержание сообщения',
                placeholder='Не более 4000 символов',
                max_length=4000,
                value=description
            )
        )
        self.add_item(
            InputText(
                style=discord.InputTextStyle.short,
                label='Укажите код цвета (HEX)',
                placeholder='Например: #ff0000 или 00ff29 (Оставь пустым для стандартного)',
                max_length=7,
                required=False,
                value= current_color
            )
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(invisible=False, ephemeral=True)
            message: discord.Message = await self.channel.fetch_message(self.message_id)
            try:
                embed: discord.Embed = message.embeds[0]
            except Exception as error:
                logger.error(f'Ошибка при поиске embed! "{error}"')
            raw_title = self.children[0].value
            raw_description = self.children[1].value
            raw_color = self.children[2].value
            embed.title = raw_title if raw_title != "" else None
            embed.description = raw_description if raw_description != "" else None
            if raw_color:
                hex_color = raw_color.replace('#', '')
                try:
                    embed.color = discord.Color(int(hex_color, 16))
                except ValueError:
                    await interaction.respond(
                        '⚠️ Неверный формат цвета! Используйте HEX-код, например: `#ff0000`. '
                        'Цвет оставлен без изменений.',
                        ephemeral=True,
                        delete_after=7
                    )
            else:
                embed.color = None
            await message.edit(embed=embed)
            await interaction.respond('✅', delete_after=1)
        except Exception as error:
            logger.error(
                f'Пользователь {interaction.user.display_name} попытался изменить embed '
                f'но получил ошибку {error}!'
            )


@commands.slash_command()
@commands.has_any_role(LEADER_ROLE, OFICER_ROLE, TREASURER_ROLE)
async def edit_embed_description(
    ctx: discord.ApplicationContext,
    message_id: discord.Option(
        str,
        description='ID сообщения, которое нужно изменить',
        name_localizations={'ru':'id_сообщения'}
    ),
    channel: discord.Option(
        discord.abc.GuildChannel,
        description='Канал, где находится сообщение ',
        name_localizations={'ru': 'канал_или_ветка'},
        required=False,
        channel_types=[
            discord.ChannelType.text,
            discord.ChannelType.public_thread,
            discord.ChannelType.private_thread,
            discord.ChannelType.news_thread
        ]
        ) # type: ignore
) -> None:
    """
    Команда для изменения embed description, написанное ботом.
    """
    try:
        target_channel = channel or ctx.channel
        if not message_id.isdigit():
            await ctx.respond('_ID сообщения должен состоять только из цифр!_', delete_after=3)
            return
        try:
            message: discord.Message = await target_channel.fetch_message(int(message_id))
        except discord.NotFound:
            await ctx.respond(
                f'_Сообщение с ID `{message_id}` не найдено в канале {target_channel.mention}!_',
                delete_after=5
            )
            return
        current_title = None
        if message.embeds:
            embed = message.embeds[0]
            current_title = message.embeds[0].title
            current_description = message.embeds[0].description
            current_color = message.embeds[0].color
            if embed.color and embed.color.value is not None:
                current_color = f"#{embed.color.value:06x}"
        await ctx.response.send_modal(SetNewDescription(
            message_id=int(message_id),
            channel=target_channel,
            current_title=current_title,
            description=current_description,
            current_color=current_color
        ))
        logger.info(
            f'Команда "/edit_embed_description" вызвана пользователем'
            f'"{ctx.user.display_name}"!'
        )
    except Exception as error:
        logger.error(
            f'Ошибка при вызове команды "/edit_embed_description"! '
            f'"{error}"'
        )


@edit_embed_description.error
async def edit_embed_error(
    ctx: discord.ApplicationContext,
    error: Exception
) -> None:
    """
    Обработчик ошибок для команды edit_embed_description.
    """
    await command_error(ctx, error, "edit_embed_description")


class CreateOrEditSymbolsList(View):
    """
    Универсальное модальное окно для создания или
    редактирования списка за символы свершения
    """
    banner_list: str | None = None
    cape_list: str | None = None
    select_type: discord.ComponentType = discord.ComponentType.user_select
    min_values: int = 1
    max_values: int = 24
    placeholder: str = 'Выбери игроков'

    def __init__(
        self,
        lookup_message: discord.Message | None = None
    ) -> None:
        super().__init__(timeout=None)
        self.lookup_message = lookup_message

    @select(
        select_type=select_type,
        min_values=min_values,
        max_values=max_values,
        placeholder=placeholder
    )
    async def banner_callback(
        self, select: discord.ui.Select, interaction: discord.Interaction
    ):
        await handle_selection(self, select, interaction, 'banner')

    @select(
        select_type=select_type,
        min_values=min_values,
        max_values=max_values,
        placeholder=placeholder
    )
    async def cape_callback(
        self, select: discord.ui.Select, interaction: discord.Interaction
    ):
        await handle_selection(self, select, interaction, 'cape')

    @button(
        label='Опубликовать',
        style=discord.ButtonStyle.green,
        emoji='📨'
    )
    async def create_callback(
        self,
        button: discord.ui.Button,
        interaction: discord.Interaction
    ):
        try:
            await interaction.response.defer(invisible=False, ephemeral=True)
            if self.lookup_message:
                embed: discord.Embed = self.lookup_message.embeds[0]
                if self.banner_list is not None and len(embed.fields) > 0:
                    safe_banner_value = self.banner_list or '\u200b'
                    banner_field: discord.EmbedField = embed.fields[0]
                    embed.set_field_at(
                        index=0,
                        name=banner_field.name,
                        value=safe_banner_value,
                        inline=banner_field.inline
                    )
                if self.cape_list is not None:
                    safe_cape_value = self.cape_list or '\u200b'
                    if len(embed.fields) > 1:
                        cape_field: discord.EmbedField = embed.fields[1]
                        embed.set_field_at(
                            index=1,
                            name=cape_field.name,
                            value=safe_cape_value,
                            inline=cape_field.inline
                        )
                    else:
                        embed.add_field(
                            name='_Накидки:_',
                            value=safe_cape_value,
                            inline=True
                        )
                await self.lookup_message.edit(embed=embed)
            else:
                await interaction.channel.send(
                    embed=symbols_list_embed(
                        banner_list=self.banner_list,
                        cape_list=self.cape_list
                    )
                )
            await interaction.respond('✅', delete_after=1)
        except Exception as error:
            logger.error(
                f'При создании списка знамён/накидок вышла "{error}"'
            )


@commands.slash_command()
@commands.has_any_role(LEADER_ROLE, OFICER_ROLE, TREASURER_ROLE)
async def symbols_list(
    ctx: discord.ApplicationContext,
    message_id: discord.Option(
        str,
        description='ID сообщения, которое нужно изменить',
        name_localizations={'ru':'id_сообщения'},
        required=False
    ),  # type: ignore
) -> None:
    """
    Команда для создания или изменения списка за символы.
    """
    try:
        await ctx.defer(ephemeral=True)

        if message_id:
            try:
                lookup_message: discord.Message = (
                    await ctx.channel.fetch_message(int(message_id))
                )
            except discord.NotFound:
                await ctx.respond(
                    '_Сообщение не найдено по этому ID_', delete_after=2
                )
                logger.warning(f'Не найдено сообщение по id = {message_id}')

            if not lookup_message.embeds[0]:
                await ctx.respond(
                    '_У этого сообщения нет embed!_', delete_after=2
                )

            await ctx.respond(
                view=CreateOrEditSymbolsList(lookup_message=lookup_message)
            )
        else:
            await ctx.respond(view=CreateOrEditSymbolsList())
        logger.info(
            f'Команда "/embed_manager" вызвана пользователем'
            f'"{ctx.user.display_name}"!'
        )
    except Exception as error:
        logger.error(
            f'Ошибка при вызове команды "/embed_manager"! '
            f'"{error}"'
        )


@symbols_list.error
async def embed_manager_error(
    ctx: discord.ApplicationContext,
    error: Exception
) -> None:
    """
    Обработчик ошибок для команды symbols_list.
    """
    await command_error(ctx, error, "symbols_list")


class ChooseSimbolsAmount(Modal):
    """Модальное окно для выбора количества топ за символы."""
    def __init__(
        self,
        ctx: discord.ApplicationContext,
        message_id: str,
        channel: discord.TextChannel
    ):
        super().__init__(
            title='Укажи сколько знамён и чемпионок',
            timeout=None
        )
        self.ctx = ctx
        self.message_id = message_id
        self.channel = channel

        self.add_item(
            InputText(
                style=discord.InputTextStyle.short,
                label='Укажи количество победителей для знамён',
                placeholder='Не более 30',
                max_length=2
            )
        )

        self.add_item(
            InputText(
                style=discord.InputTextStyle.short,
                label='Укажи количество победителей для чемпионок',
                placeholder='Не более 10',
                max_length=2,
                required=False
            )
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(invisible=False, ephemeral=True)
            checking_message: discord.Message = (
                await self.ctx.channel.fetch_message(int(self.message_id))
            )
            attachment = checking_message.attachments[0]
            bytes_data = await attachment.read()
            detected = chardet.detect(bytes_data)
            encoding = detected['encoding'] if detected['encoding'] else 'utf-8'
            try:
                content = bytes_data.decode(encoding)
            except UnicodeDecodeError:
                try:
                    content = bytes_data.decode('windows-1251')
                except UnicodeDecodeError as e:
                    logger.error(f"Ошибка декодирования файла: {e}")
                    await interaction.respond("Ошибка: файл не может быть прочитан. Проверьте кодировку файла.")
                    return
            
            # Находим позицию "Info: " в содержимом
            info_start = content.find('Info: ')
            if info_start == -1:
                await interaction.respond("Ошибка: в файле не найдено 'Info: '.")
                return
            info_start += len('Info: ')
            json_str = content[info_start:].strip()  # Убираем лишние пробелы и символы после
            
            # Предполагаем, что JSON начинается с '[' и заканчивается ']'
            # Если есть несколько, берем первый после "Info: "
            json_start = json_str.find('[')
            if json_start == -1:
                await interaction.respond("Ошибка: после 'Info: ' не найден JSON-массив.")
                return
            json_end = json_str.rfind(']') + 1
            if json_end == 0:
                await interaction.respond("Ошибка: после 'Info: ' не найден завершающий ']' для JSON-массива.")
                return
            json_data = json_str[json_start:json_end]
            
            try:
                data_list = json.loads(json_data)
            except json.JSONDecodeError as e:
                logger.error(f"Ошибка декодирования JSON: {e}")
                await interaction.respond("Ошибка: не удалось распарсить JSON-данные.")
                return
            members: list[discord.Member] = interaction.guild.members
            roles: list[discord.Role] = interaction.guild.roles
            banner_amount: str | None = self.children[0].value
            cape_amount: str | None = self.children[1].value
            result: list[str] = [item['name'] for item in data_list]
            sorted_result: list[str] = await sort_nicknames_by_role(
                members, roles, result
            )

            # Валидируем вводимое значение пользователем для знамён
            validated_banner_amount = await validate_amount(
                value=banner_amount,
                interaction=interaction
            )
            # Генерируем список знамён
            banner_list = await generate_member_list(
                sorted_result[:validated_banner_amount],
                interaction=interaction
            )
            # Валидируем вводимое значение пользователем для накидок
            if cape_amount:
                validated_cape_amount = await validate_amount(
                    value=cape_amount,
                    interaction=interaction,
                    is_banner=False
                )
                # Генерируем список накидок, если нужно
                cape_list = await generate_member_list(
                    sorted_result[
                        validated_banner_amount:validated_cape_amount
                        + validated_banner_amount
                    ],
                    interaction=interaction
                )

            await self.channel.send(
                embed=symbols_list_embed(
                    banner_list=banner_list,
                    cape_list=cape_list if cape_amount else None
                )
            )
            await interaction.respond('✅', delete_after=1)
        except Exception as error:
            logger.error(
                f'Пользователь {interaction.user.display_name} попытался выбрать кол-во '
                f'за накидки/чемпы, но получил ошибку {error}!'
            )


@commands.slash_command()
@commands.has_any_role(LEADER_ROLE, OFICER_ROLE, TREASURER_ROLE)
async def auto_simbols_list(
    ctx: discord.ApplicationContext,
    message_id: discord.Option(
        str,
        description='ID сообщения с прикрепленным user.cfg',
        name_localizations={'ru': 'id_сообщения'}
    )  # type: ignore
) -> None:
    """
    Загружает статистику авторитета из user.cfg и сохраняет в базу данных.
    """
    try:
        await ctx.defer(ephemeral=True)
        if not message_id.isdigit():
            await ctx.respond('Некорректный ID сообщения.')
            return

        checking_message: discord.Message = await ctx.channel.fetch_message(int(message_id))
        if not checking_message.attachments:
            await ctx.respond('В указанном сообщении нет вложения.')
            return

        bytes_data = await checking_message.attachments[0].read()
        content = _decode_text_file(bytes_data)
        latest_overall_ms, snapshot_date, rows = _extract_latest_authority_data(content)

        async with async_session_factory() as session:
            await authority_stat_orm.replace_snapshot_data(
                session=session,
                snapshot_overall_ms=latest_overall_ms,
                snapshot_date=snapshot_date,
                rows=rows
            )
            await session.commit()

        await ctx.respond(
            f'Загружено записей: {len(rows)}.\n'
            f'Дата среза: {snapshot_date} (overallMs={latest_overall_ms}).'
        )
        logger.info(
            f'Команда "/auto_simbols_list" вызвана "{ctx.user.display_name}", '
            f'сохранено записей авторитета: {len(rows)}.'
        )
    except Exception as error:
        await ctx.respond(f'Ошибка: {error}')
        logger.error(f'Ошибка в команде "/auto_simbols_list": "{error}"')


@commands.slash_command()
@commands.has_any_role(LEADER_ROLE, OFICER_ROLE, TREASURER_ROLE)
async def get_statistic_authority(
    ctx: discord.ApplicationContext,
    date_from: discord.Option(
        str,
        description='Начальная дата (ГГГГ-ММ-ДД)',
        name_localizations={'ru': 'дата_от'}
    ),  # type: ignore
    date_to: discord.Option(
        str,
        description='Конечная дата (ГГГГ-ММ-ДД)',
        name_localizations={'ru': 'дата_до'}
    ),  # type: ignore
    limit: discord.Option(
        int,
        description='Лимит строк',
        required=False,
        default=25,
        min_value=1,
        max_value=50,
        name_localizations={'ru': 'лимит'}
    )  # type: ignore
) -> None:
    """
    Показывает статистику авторитета за выбранный период.
    """
    try:
        await ctx.defer(ephemeral=True)
        try:
            start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            end_date = datetime.strptime(date_to, '%Y-%m-%d').date()
        except ValueError:
            await ctx.respond('Даты должны быть в формате ГГГГ-ММ-ДД.')
            return

        if start_date > end_date:
            await ctx.respond('Начальная дата не может быть больше конечной.')
            return

        start_iso = start_date.isoformat()
        end_iso = end_date.isoformat()

        async with async_session_factory() as session:
            top_rows, snapshots_pair = await authority_stat_orm.get_delta_for_period(
                session=session,
                date_from=start_iso,
                date_to=end_iso,
                limit=limit
            )
            total_rows, snapshots = await authority_stat_orm.get_period_meta(
                session=session,
                date_from=start_iso,
                date_to=end_iso
            )
            snapshot_dates: tuple[str | None, str | None] = (None, None)
            if snapshots_pair is not None:
                snapshot_dates = await authority_stat_orm.get_snapshot_dates(
                    session=session,
                    start_snapshot=snapshots_pair[0],
                    end_snapshot=snapshots_pair[1]
                )

        if not top_rows:
            await ctx.respond('За выбранный период данные не найдены.')
            return

        lines = [
            f'`{idx:>2}.` **{name}** - `{delta}` (`{start_value}` -> `{end_value}`)'
            for idx, (name, delta, start_value, end_value) in enumerate(top_rows, start=1)
        ]
        embed = discord.Embed(
            title='Статистика авторитета',
            description='\n'.join(lines),
            color=0x00ff29
        )
        embed.add_field(
            name='Период',
            value=f'{start_iso} — {end_iso}',
            inline=False
        )
        embed.add_field(
            name='Срезы/Строки',
            value=f'{snapshots}/{total_rows}',
            inline=False
        )
        if snapshots_pair is not None:
            start_snap_date = snapshot_dates[0] or 'не найдено'
            end_snap_date = snapshot_dates[1] or 'не найдено'
            embed.add_field(
                name='Использованные срезы',
                value=(
                    f'дата_от: {start_snap_date} (id={snapshots_pair[0]})\n'
                    f'дата_до: {end_snap_date} (id={snapshots_pair[1]})'
                ),
                inline=False
            )
        await ctx.respond(embed=embed)
    except Exception as error:
        await ctx.respond(f'Ошибка: {error}')
        logger.error(f'Ошибка в команде "/get_statistic_authority": "{error}"')


@auto_simbols_list.error
async def auto_simbols_list_error(
    ctx: discord.ApplicationContext,
    error: Exception
) -> None:
    """
    Обработчик ошибок для команды auto_simbols_list.
    """
    await command_error(ctx, error, "auto_simbols_list")


@get_statistic_authority.error
async def get_statistic_authority_error(
    ctx: discord.ApplicationContext,
    error: Exception
) -> None:
    """
    Обработчик ошибок для команды get_statistic_authority.
    """
    await command_error(ctx, error, "get_statistic_authority")


def setup(bot: discord.Bot):
    bot.add_application_command(attention)
    bot.add_application_command(edit_embed_description)
    bot.add_application_command(symbols_list)
    bot.add_application_command(auto_simbols_list)
    bot.add_application_command(get_statistic_authority)

