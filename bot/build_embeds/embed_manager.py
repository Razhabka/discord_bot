import base64
import csv
import json
import re
import io
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

import chardet
import discord
from discord.ext import commands
from discord.ui import Modal, InputText, View, select, button
from loguru import logger
from pydantic import color
from sqlalchemy.dialects.mysql import DECIMAL

from .functions import (
    validate_amount, generate_member_list, handle_selection,
    sort_nicknames_by_role
)
from .embeds import attention_embed, symbols_list_embed
from regular_commands.regular_commands import command_error
from core import (LEADER_ROLE, OFICER_ROLE, TREASURER_ROLE, async_session_factory, RANK_MAPPING, CLOAK_MAPPING,
                  GUEST_ROLE, VETERAN_ROLE, SERGEANT_ROLE, RATIO_FOR_LOSE, RATIO_FOR_WIN, ID_FROM_RANGE, RANGE_TOP,
                  RATIO_FOR_WIN_DEF, RATIO_FOR_LOSE_DEF_RANGE, RATIO_FOR_LOSE_DEF_EFFORTS)
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

class AddCommentsModal(Modal):
    """Модальное окно для добавления комментариев к выбранным игрокам."""

    def __init__(self, selected_members: list[discord.Member], list_type: str,
                 view_instance: 'CreateOrEditSymbolsList'):
        super().__init__(title='Добавление комментариев', timeout=None)
        self.selected_members = selected_members
        self.list_type = list_type
        self.view_instance = view_instance

        # Создаем одно удобное текстовое поле, где перечислены выбранные игроки
        initial_value = ""
        for idx, member in enumerate(selected_members, start=1):
            initial_value += f"{idx}. {member.display_name} — \n"

        self.add_item(
            InputText(
                style=discord.InputTextStyle.multiline,
                label=f'Напишите комментарии после знака "—"',
                value=initial_value,
                placeholder='Оставьте пустые строки или измените текст по желанию',
                max_length=2000
            )
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(invisible=False, ephemeral=True)

            raw_text = self.children[0].value
            lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

            final_lines = []
            for idx, member in enumerate(self.selected_members):
                comment = ""
                if idx < len(lines):
                    current_line = lines[idx]
                    if "—" in current_line:
                        comment = current_line.split("—", 1)[1].strip()

                if comment:
                    final_lines.append(f"{member.mention} — *{comment}*")
                else:
                    final_lines.append(f"{member.mention}")

            result_text = "\n".join(final_lines)

            if self.list_type == 'banner':
                self.view_instance.banner_list = result_text
            else:
                self.view_instance.cape_list = result_text

            await interaction.respond('✅ Комментарии сохранены! Нажмите "Опубликовать", чтобы применить изменения.',
                                      delete_after=5)
        except Exception as error:
            logger.error(f'Ошибка в модальном окне комментариев symbols_list: {error}')
            await interaction.respond(f'❌ Ошибка: {error}', ephemeral=True)

class CreateOrEditSymbolsList(View):
    """
    Универсальное окно для создания или
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
        lookup_message: discord.Message | None = None,
        date: datetime | None = None,
    ) -> None:
        super().__init__(timeout=None)
        self.lookup_message = lookup_message
        self.date = date

    @select(
        select_type=select_type,
        min_values=min_values,
        max_values=max_values,
        placeholder='Выбери игроков на ЗНАМЁНА'
    )
    async def banner_callback(
        self, select: discord.ui.Select, interaction: discord.Interaction
    ):
        selected_members = select.values
        if selected_members:
            await interaction.response.send_modal(
                AddCommentsModal(selected_members=selected_members, list_type='banner', view_instance=self)
            )

    @select(
        select_type=select_type,
        min_values=min_values,
        max_values=max_values,
        placeholder='Выбери игроков на НАКИДКИ'
    )
    async def cape_callback(
        self, select: discord.ui.Select, interaction: discord.Interaction
    ):
        selected_members = select.values
        if selected_members:
            await interaction.response.send_modal(
                AddCommentsModal(selected_members=selected_members, list_type='cape', view_instance=self)
            )

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
                        cape_list=self.cape_list,
                        date=self.date
                    )
                )
            await interaction.respond('✅ Список успешно опубликован!', delete_after=2)
        except Exception as error:
            logger.error(
                f'При создании списка знамён/накидок вышла "{error}"')


@commands.slash_command()
@commands.has_any_role(LEADER_ROLE, OFICER_ROLE, TREASURER_ROLE)
async def tabards_list(
    ctx: discord.ApplicationContext,
    message_id: discord.Option(
        str,
        description='ID сообщения, которое нужно изменить',
        name_localizations={'ru':'id_сообщения'},
        required=False
    ) = None,
    date: discord.Option(
        str,
        description="Введи дату отсета для накидок(Формат 'ДД.ММ.ГГГГ')",
        required=False
    ) = None# type: ignore
) -> None:
    """
    Команда для создания или изменения списка за символы.
    """
    try:
        await ctx.defer(ephemeral=True)

        logger.info(f'Получили дату {date}')
        parsed_date = date
        if date:
            try:
                parsed_date = datetime.strptime(date, "%d.%m.%Y").date()
                logger.info(f'Преобразовали дату {parsed_date}')
            except ValueError:
                 return await ctx.respond(
                    '_❌ Неверный формат даты! Используйте строго ДД.ММ.ГГГГ (например, 28.07.2026)._',
                    delete_after=5
                )

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
                view=CreateOrEditSymbolsList(lookup_message=lookup_message, date=parsed_date)
            )
        else:
            await ctx.respond(view=CreateOrEditSymbolsList(date=parsed_date))
        logger.info(
            f'Команда "/embed_manager" вызвана пользователем'
            f'"{ctx.user.display_name}"!'
        )
    except Exception as error:
        logger.error(
            f'Ошибка при вызове команды "/embed_manager"! '
            f'"{error}"'
        )


@tabards_list.error
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

            info_start = content.find('Info: ')
            if info_start == -1:
                await interaction.respond("Ошибка: в файле не найдено 'Info: '.")
                return
            info_start += len('Info: ')
            json_str = content[info_start:].strip()  # Убираем лишние пробелы и символы после

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

            validated_banner_amount = await validate_amount(
                value=banner_amount,
                interaction=interaction
            )
            banner_list = await generate_member_list(
                sorted_result[:validated_banner_amount],
                interaction=interaction
            )
            if cape_amount:
                validated_cape_amount = await validate_amount(
                    value=cape_amount,
                    interaction=interaction,
                    is_banner=False
                )
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

@commands.slash_command(
    name="clear_role",
    description="Загрузить файл file.txt (GuildStats) и вывести ТОПы по чистому авторитету.",
)
@commands.has_any_role(LEADER_ROLE, OFICER_ROLE, TREASURER_ROLE)
async def clear_role(
        ctx: discord.ApplicationContext,
        file: discord.Option(
            discord.Attachment,
            description="Файл user.cfg или текстовый лог GuildStats",
            name_localizations={'ru': 'файл_логов'}
        )
) -> None:
    try:
        await ctx.defer(ephemeral=True)

        if not file.filename.endswith(('.cfg', '.txt')):
            await ctx.respond("Ошибка: Пожалуйста, прикрепите файл с расширением .txt")
            return

        bytes_data = await file.read()

        try:
            content = bytes_data.decode('utf-8')
        except UnicodeDecodeError:
            content = bytes_data.decode('cp1251')

        members = []
        pattern = re.compile(r"Info:\s*([^|]+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)")

        for line in content.splitlines():
            match = pattern.search(line)
            if match:
                nick = match.group(1).strip()

                if nick.lower() == "nick":
                    continue

                rank_id = int(match.group(2))
                loyalty = int(match.group(3))
                raw_authority = int(match.group(4))
                cloak_id = int(match.group(5))

                rank_str = RANK_MAPPING.get(rank_id, f"Неизвестный ранг ({rank_id})")
                cloak_str = CLOAK_MAPPING.get(cloak_id, f"Неизвестная накидка ({cloak_id})")

                members.append(GuildMember(
                    nick=nick,
                    rank=rank_str,
                    loyalty=loyalty,
                    authority=raw_authority,
                    cloak=cloak_str
                ))
        role_sergeant = discord.utils.get(ctx.guild.roles, name=SERGEANT_ROLE)
        role_veteran = discord.utils.get(ctx.guild.roles, name=VETERAN_ROLE)
        role_guest = discord.utils.get(ctx.guild.roles, name=GUEST_ROLE)

        process_member_ids = set()

        if ctx.guild:
            all_members = {m.display_name.lower(): m for m in ctx.guild.members}


        change_ranks = []


        for m in members:
            nick_lower = m.nick.lower()

            if nick_lower not in all_members:
                continue

            discord_member = all_members[nick_lower]
            process_member_ids.add(discord_member.id)
            file_rank = m.rank
            if file_rank == SERGEANT_ROLE:
                if role_sergeant in discord_member.roles:
                    continue
                if role_veteran in discord_member.roles:
                    await discord_member.remove_roles(role_veteran)
                    await discord_member.add_roles(role_sergeant)
                    change_ranks.append(f'{discord_member.display_name}({VETERAN_ROLE} -> {SERGEANT_ROLE})')
                    logger.info(
                        f'У игрока {discord_member.display_name} была удалена роль {role_veteran} и выдана ему роль {role_sergeant}'
                    )
            elif file_rank == VETERAN_ROLE:
                if role_veteran in discord_member.roles:
                    continue
                if role_sergeant in discord_member.roles:
                    await discord_member.remove_roles(role_sergeant)
                    await discord_member.add_roles(role_veteran)
                    change_ranks.append(f'{discord_member.display_name}({SERGEANT_ROLE} -> {VETERAN_ROLE})')
                    logger.info(
                        f'У игрока {discord_member.display_name} была удалена роль {role_sergeant} и выдана ему роль {role_veteran}'
                    )

        for discord_member in ctx.guild.members:
            if discord_member.bot:
                continue

            if discord_member.id in process_member_ids:
                logger.info(
                    f'{discord_member.display_name} был пропущен'
                )
                continue

            if role_sergeant in discord_member.roles:
                await discord_member.remove_roles(role_sergeant)
                await discord_member.add_roles(role_guest)
                change_ranks.append(f'{discord_member.display_name}({SERGEANT_ROLE} -> {GUEST_ROLE})')
                logger.info(
                    f'У игрока {discord_member.display_name} была удалена роль {role_sergeant} и выдана ему роль {role_guest}'
                )
            if role_veteran in discord_member.roles:
                await discord_member.remove_roles(role_veteran)
                await discord_member.add_roles(role_guest)
                change_ranks.append(f'{discord_member.display_name}({VETERAN_ROLE} -> {GUEST_ROLE})')
                logger.info(
                    f'У игрока {discord_member.display_name} была удалена роль {role_veteran} и выдана ему роль {role_guest}'
                )

        embed = discord.Embed(
            title="📊 Отчет по синхронизации ролей",
            color = discord.Color.green()
        )
        has_change = False

        if change_ranks:
            has_change = True
            rank_change = '\n'.join(change_ranks)
            embed.add_field(name= "Изменение ролей", value=rank_change, inline=False)

        if not has_change:
            embed.description = "Никаких изменений не производилось"

        await ctx.respond(embed=embed, ephemeral=True)
    except Exception as error:
        logger.error(f'Ошибка в команде "/clear_role": "{error}"')
        await ctx.respond(f'Произошла ошибка при обработке файла: {error}')

@dataclass
class GuildMember:
    nick: str
    rank: str
    loyalty: int
    authority: int
    cloak: str


@commands.slash_command(
    name="auto_tabard_list",
    description="Загрузить файл file.txt (GuildStats) и вывести ТОПы по чистому авторитету.",
)
@commands.has_any_role(LEADER_ROLE, OFICER_ROLE, TREASURER_ROLE)
async def auto_tabard_list(
        ctx: discord.ApplicationContext,
        file: discord.Option(
            discord.Attachment,
            description="Файл user.cfg или текстовый лог GuildStats",
            name_localizations={'ru': 'файл_логов'}
        )
) -> None:
    try:
        await ctx.defer(ephemeral=True)

        if not file.filename.endswith(('.cfg', '.txt')):
            await ctx.respond("Ошибка: Пожалуйста, прикрепите файл с расширением .txt")
            return

        bytes_data = await file.read()

        try:
            content = bytes_data.decode('utf-8')
        except UnicodeDecodeError:
            content = bytes_data.decode('cp1251')

        members = []
        pattern = re.compile(r"Info:\s*([^|]+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)")

        for line in content.splitlines():
            match = pattern.search(line)
            if match:
                nick = match.group(1).strip()

                if nick.lower() == "nick":
                    continue

                rank_id = int(match.group(2))
                loyalty = int(match.group(3))
                raw_authority = int(match.group(4))
                cloak_id = int(match.group(5))

                if cloak_id == 1:
                    clean_authority = round(raw_authority / 1.5)
                elif cloak_id in [2, 3, 4, 5]:
                    clean_authority = round(raw_authority / 2.0)
                else:
                    clean_authority = raw_authority

                rank_str = RANK_MAPPING.get(rank_id, f"Неизвестный ранг ({rank_id})")
                cloak_str = CLOAK_MAPPING.get(cloak_id, f"Неизвестная накидка ({cloak_id})")

                members.append(GuildMember(
                    nick=nick,
                    rank=rank_str,
                    loyalty=loyalty,
                    authority=clean_authority,
                    cloak=cloak_str
                ))

        if not members:
            await ctx.respond("Не удалось найти данные об игроках в файле. Проверьте формат логов.")
            return

        members.sort(key=lambda m: m.authority, reverse=True)

        top_3_pool = [m for m in members if m.authority >= 800000][:3]

        members_without_top_3 = []
        for m in members:
            if m not in top_3_pool:
                logger.info(f'{m.nick} | {m.authority} ' )
                members_without_top_3.append(m)
        top_5_pool = [m for m in members_without_top_3 if m.authority >= 500000]


        embed = discord.Embed(
            title="🏆 Статистика ЧИСТОГО авторитета гильдии",
            color=discord.Color.green()
        )

        top_3_text = ""
        for i in range(3):
            if i < len(top_3_pool):
                m = top_3_pool[i]
                top_3_text += f"**{i+1}. {m.nick}** — {m.authority:,} авт. ({m.rank}, {m.cloak})\n"
            else:
                top_3_text += f"*{i + 1}. Место пусто*\n"
        embed.add_field(name="⭐ Топ для выдачи знамени", value=top_3_text, inline=False)

        top_5_text = ""
        for i in range(5):
            if i < len(top_5_pool):
                m = top_5_pool[i]
                top_5_text += f"**{i+1}. {m.nick}** — {m.authority:,} авт. ({m.rank}, {m.cloak})\n"
            else:
                top_5_text += f"*{i + 1}. Место пусто*\n"
        embed.add_field(name="🏅 Топ для выдачи чемпы", value=top_5_text, inline=False)

        # Выводим результат
        await ctx.respond(embed=embed)
        logger.info(f'Команда "/auto_simbols_list" обработана через файл. Загружено игроков: {len(members)}')

    except Exception as error:
        logger.error(f'Ошибка в команде "/auto_simbols_list": "{error}"')
        await ctx.respond(f'Произошла ошибка при обработке файла: {error}')


@dataclass
class PVPMember:
  nick: str
  cdWin: int
  streek: int
  multiplierRobbery: float
  ourScore: int
  opponentScore: int
  attackOrDef: int
  topOurGuild: int
  topOpponentGuild: int
  winOrLose: int
  pyament: int = None

@commands.slash_command(
    name="calculation_payments",
    description="Загрузка файла формата file.csv для расчета выплат за ЧД/РЧД"
)
async def calculation_payments(
        ctx: discord.ApplicationContext,
        file: discord.Option(
            discord.Attachment,
            description="файла формата file.csv"
        )
) -> None:

    await ctx.defer()

    if not file.filename.endswith('.csv'):
        await ctx.respond(':x: Ошибка приложите файл с расширением .csv')
        return

    try:
        file_bytes = await file.read()

        if b'\x00' in file_bytes:
            await ctx.respond(
                ":x: **Ошибка:** Этот файл является бинарным (скорее всего, это Excel `.xlsx`, "
                "которому просто переименовали расширение).\n"
                "Пожалуйста, откройте таблицу в Excel и нажмите `Файл -> Сохранить как -> CSV`."
            )
            return

        encodings = ['utf-8', 'utf-8-sig', 'cp866' , 'cp1251', 'utf-16', 'latin-1']
        content = None
        for enc in encodings:
            try:
                content = file_bytes.decode(enc)
                break
            except UnicodeDecodeError:
                continue

        if not content:
            await ctx.respond(":x: Не удалось распознать кодировку файла.")
            return

        file = io.StringIO(content, newline='')
        header_line = file.readline()
        data_start_pos = file.tell()
        sample = file.read(1024)
        file.seek(data_start_pos)

        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=';')
            reader = csv.reader(file, dialect)
        except csv.Error:
            reader = csv.reader(file, delimiter=';')

        pvp_members = []
        skipped_rows = 0

        for row_idx, row in enumerate(reader, start=2):
            if not row:
                continue
            if not any(cell.strip() for cell in row):
                continue

            try:
                pvp_members.append(PVPMember(
                    nick=str(row[0]).strip(),
                    cdWin=int(row[1]),
                    streek=int(row[2]),
                    multiplierRobbery=float(str(row[3]).replace(",", ".")),
                    ourScore=int(row[4]),
                    opponentScore=int(row[5]),
                    attackOrDef=int(row[6]),
                    topOurGuild=int(row[7]),
                    topOpponentGuild=int(row[8]),
                    winOrLose=int(row[9])
                ))
            except ValueError as e:
                logger.info(f"Пропущена строка {row_idx}: неверный формат данных. Ошибка: {e}")
                skipped_rows += 1
                continue
        final_string = ""
        minimal_payment = 200000
        for m in pvp_members:

            if m.attackOrDef == 1:
                max_realgar = (Decimal('0.25') * Decimal(str(m.multiplierRobbery)) +  Decimal('0.75') *
                               Decimal(str(m.multiplierRobbery))) * Decimal(RANGE_TOP[m.topOurGuild - m.topOpponentGuild])
                id_from_range = ID_FROM_RANGE[m.topOurGuild - m.topOpponentGuild]
                if m.winOrLose == 1:
                    base_ratio = RATIO_FOR_WIN[m.topOurGuild][id_from_range]
                    actual_realgar = ((Decimal('0.25') * Decimal(str(m.multiplierRobbery)) + (Decimal('0.75') *
                                   Decimal(str(m.multiplierRobbery))) *
                                   Decimal(m.ourScore / Decimal(m.ourScore + m.opponentScore))) *
                                   Decimal(RANGE_TOP[m.topOurGuild - m.topOpponentGuild]))
                    calc_ratio = (Decimal('0.25') * Decimal(base_ratio) +
                             Decimal(Decimal('0.75') * Decimal(base_ratio)
                                     * (Decimal(actual_realgar) / Decimal(max_realgar)))) - m.streek
                    ratio = max(Decimal('1'), calc_ratio)

                    calc_payment = int((minimal_payment * m.cdWin + minimal_payment) * Decimal(ratio))
                    m.payment = calc_payment
                if m.winOrLose == 2:
                    base_ratio = RATIO_FOR_LOSE[m.topOurGuild][id_from_range]
                    calc_ratio = (Decimal('0.25') * Decimal(base_ratio) +
                                  Decimal(Decimal('0.75') * Decimal(base_ratio)
                                          * Decimal(m.ourScore / 14400))) - m.streek
                    ratio = max(Decimal('1'), calc_ratio)
                    calc_payment = int((minimal_payment * m.cdWin + minimal_payment) * Decimal(ratio))
                    m.payment = calc_payment
            if m.attackOrDef == 2:

                max_realgar = Decimal(m.multiplierRobbery) * Decimal(RANGE_TOP[m.topOpponentGuild - m.topOurGuild])

                if m.winOrLose == 1:

                    base_ratio = RATIO_FOR_WIN_DEF[m.topOpponentGuild]
                    calc_ratio = Decimal((Decimal('0.25') * Decimal(base_ratio) +
                                  Decimal(Decimal('0.75') * Decimal(base_ratio))) - m.streek)
                    ratio = max(Decimal('1'), calc_ratio)

                    calc_payment = int((minimal_payment * m.cdWin + minimal_payment) * Decimal(ratio))
                    m.payment = calc_payment
                if m.winOrLose == 2:

                    first_ratio = Decimal('0.25') * Decimal(str(m.multiplierRobbery))

                    ratio_for_score = Decimal(m.opponentScore / (m.ourScore + m.opponentScore))

                    second_ration = (Decimal('0.75') *
                                    Decimal(str(m.multiplierRobbery))) * ratio_for_score

                    actual_realgar = Decimal(first_ratio + second_ration) * Decimal(RANGE_TOP[m.topOpponentGuild - m.topOurGuild])

                    calc_ratio = (Decimal(RATIO_FOR_LOSE_DEF_RANGE[m.topOpponentGuild]) +
                                    Decimal(RATIO_FOR_LOSE_DEF_EFFORTS[m.topOpponentGuild])
                                     * Decimal(Decimal('1') - Decimal(Decimal(actual_realgar) / Decimal(max_realgar)))) - m.streek
                    ratio = max(Decimal('1'), calc_ratio)

                    calc_payment = int((minimal_payment * m.cdWin + minimal_payment) * Decimal(ratio))
                    m.payment = calc_payment
            formated_string = f"{m.payment:,}".replace(",", " ")
            final_string += f'{m.nick} -> {formated_string}\n'

        embed = discord.Embed(
            title="Выплаты за ЧД/РЧД :money_with_wings:",
            description=final_string,
            color=discord.Color.green()
        )

        await ctx.respond(embed=embed)
    except Exception as error:
        logger.error(f'Ошибка в команде "/calculation_payments": "{error}"')
        await ctx.respond(f'Произошла ошибка при обработке файла: {error}')

@commands.slash_command(
    name="stat_auto_month",
    description="Загрузить файл file.txt (GuildStats) и вывести ТОПы по чистому авторитету.",
)
@commands.has_any_role(LEADER_ROLE, OFICER_ROLE, TREASURER_ROLE)
async def stat_auto_month(
        ctx: discord.ApplicationContext,
        file: discord.Option(
            discord.Attachment,
            description="Файл user.cfg или текстовый лог GuildStats",
            name_localizations={'ru': 'файл_логов'}
        ),
        some_number: discord.Option(
            int,
            description="Введите какое-то целое число (например, лимит или период)",
            name_localizations={'ru': 'сумма_выплаты'},
            required=True
        )
) -> None:
    try:
        await ctx.defer(ephemeral=True)

        if not file.filename.endswith(('.cfg', '.txt')):
            await ctx.respond("Ошибка: Пожалуйста, прикрепите файл с расширением .txt")
            return

        bytes_data = await file.read()

        try:
            content = bytes_data.decode('utf-8')
        except UnicodeDecodeError:
            content = bytes_data.decode('cp1251')

        members = []
        pattern = re.compile(r"Info:\s*([^|]+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)")

        for line in content.splitlines():
            match = pattern.search(line)
            if match:
                nick = match.group(1).strip()

                if nick.lower() == "nick":
                    continue

                rank_id = int(match.group(2))
                loyalty = int(match.group(3))
                raw_authority = int(match.group(4))
                cloak_id = int(match.group(5))
                if raw_authority == 0:
                    continue
                rank_str = RANK_MAPPING.get(rank_id, f"Неизвестный ранг ({rank_id})")
                cloak_str = CLOAK_MAPPING.get(cloak_id, f"Неизвестная накидка ({cloak_id})")

                members.append(GuildMember(
                    nick=nick,
                    rank=rank_str,
                    loyalty=loyalty,
                    authority=raw_authority,
                    cloak=cloak_str
                ))

        if not members:
            await ctx.respond("Не удалось найти данные об игроках в файле. Проверьте формат логов.")
            return

        members.sort(key=lambda m: m.authority, reverse=True)

        embed = discord.Embed(
            title="🏆 Всех членов гильдии по авторитету",
            color=discord.Color.green()
        )

        current_text = ""
        first_chunk = True

        for i, m in enumerate(members):
            raw_val = m.authority / 1000000 * some_number
            calculated_val = round(raw_val)

            line = f"**{i + 1}. {m.nick}** — {m.authority:,} ➔ {calculated_val:,}\n"

            if len(current_text) + len(line) > 3500:
                if first_chunk:
                    embed.description = current_text
                    await ctx.respond(embed=embed)
                    first_chunk = False
                else:
                    next_embed = discord.Embed(description=current_text, color=discord.Color.green())
                    await ctx.send(embed=next_embed)

                current_text = line
            else:
                current_text += line

        if current_text:
            if first_chunk:
                embed.description = current_text
                await ctx.respond(embed=embed)
            else:
                next_embed = discord.Embed(description=current_text, color=discord.Color.green())
                await ctx.send(embed=next_embed)
        logger.info(f'Команда "/stat_auto_month" обработана через файл. Загружено игроков: {len(members)}')

    except Exception as error:
        logger.error(f'Ошибка в команде "/stat_auto_month": "{error}"')
        await ctx.respond(f'Произошла ошибка при обработке файла: {error}')


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


@auto_tabard_list.error
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
    bot.add_application_command(tabards_list)
    bot.add_application_command(auto_tabard_list)
    bot.add_application_command(clear_role)
    bot.add_application_command(stat_auto_month)
    bot.add_application_command(calculation_payments)

