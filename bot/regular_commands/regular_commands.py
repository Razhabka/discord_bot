import re

import chardet
import discord
from discord.ext import commands
from loguru import logger

from .embeds import technical_works_embed, removed_role_list_embed
from core import (
    async_session_factory,
    LEADER_ROLE, OFICER_ROLE, TREASURER_ROLE,
    WIZARD_PARTY,
    CAT_WORLD, PISAT_DVA,
    MENT_ID, WIZARD_ID, PVP_GODZILLA_ID,
    SERGEANT_ROLE, VETERAN_ROLE, GUEST_ROLE,
)
from core.orm import rcd_app_orm, pve_app_orm


async def command_error(
    ctx: discord.ApplicationContext, error: Exception, command_name: str
) -> None:
    """
    Обработчик ошибок для команд.
    """
    if isinstance(error, commands.errors.MissingAnyRole):
        await ctx.respond(
            f'_Команду_ {command_name} _может вызвать только '
            f'"Лидер", "Казначей" или "Офицер"!_ ❌',
            ephemeral=True,
            delete_after=10
        )
        logger.info(
            f'Пользователь "{ctx.user.display_name}" '
            f'пытался вызвать команду "{command_name}"! '
            f'В результате возникло исключение "{error}"!'
        )
    elif isinstance(error, commands.errors.PrivateMessageOnly):
        await ctx.respond(
            f'_Команду_ {command_name} _нельзя вызывать в личные сообщения бота!_',
            ephemeral=True,
            delete_after=5
        )
        logger.info(
            f'Пользователь "{ctx.user.display_name}" '
            f'пытался вызвать команду "{command_name}" в лс! '
            f'В результате возникло исключение "{error}"!'
        )
    else:
        logger.error(
            f'Пользователь "{ctx.user.display_name}" '
            f'пытался вызвать команду "{command_name}"! '
            f'В результате возникло исключение "{error}"!'
        )
        raise error


@commands.slash_command()
@commands.has_any_role(LEADER_ROLE, OFICER_ROLE, TREASURER_ROLE)
async def technical_works(
    ctx: discord.ApplicationContext,
    channel: discord.Option(
        discord.TextChannel,
        description='Куда отправить сообщение?',
        name_localizations={'ru':'текстовый_канал'},
    )  # type: ignore
) -> None:
    """
    Команда для отправки сообщения о технических работах.
    """
    await channel.send(embed=technical_works_embed())
    logger.info(
        f'Команда "/technical_works" вызвана пользователем '
        f'"{ctx.user.display_name}" в канал "{channel}"!'
    )
    await ctx.respond(
        f'_Сообщение о тех работах отправлено в канал {channel.mention}!_',
        ephemeral=True,
        delete_after=3
    )


@technical_works.error
async def technical_works_error(
    ctx: discord.ApplicationContext,
    error: Exception
) -> None:
    """
    Обработчик ошибок для команды technical_works.
    """
    await command_error(ctx, error, "technical_works")


@commands.slash_command()
@commands.has_any_role(LEADER_ROLE, OFICER_ROLE, TREASURER_ROLE)
async def clear_all(
    ctx: discord.ApplicationContext,
    channel: discord.Option(
        discord.TextChannel,
        description='Канал для очистки',
        name_localizations={'ru':'текстовый_канал'},
    ),  # type: ignore
    limit: discord.Option(
        int,
        description='Кол-во сообщений для удаления',
        name_localizations={'ru':'сколько_удалить'},
        default=100,
        required=False
    )  # type: ignore
) -> None:
    """
    Команда для удаления сообщений в текстовом канале.
    """
    try:
        await ctx.defer(ephemeral=True)
        await channel.purge(
            limit=limit,
            bulk=True
        )
        logger.info(
            f'Команда "/clear_all" вызвана пользователем '
            f'"{ctx.user.display_name}" в канале "{channel}"!'
        )
        await ctx.respond(
            f'_Сообщения удалены в канале {channel.mention}!_',
            delete_after=3
        )
    except Exception as error:
        logger.error(
            f'_При использовании команды "clear_all" в канале '
            f'{channel} возникла ошибка: "{error}"!_'
        )


@clear_all.error
async def clear_all_error(
    ctx: discord.ApplicationContext,
    error: Exception
) -> None:
    """
    Обработчик ошибок для команды clear_all.
    """
    await command_error(ctx, error, "clear_all")


@commands.slash_command()
@commands.has_any_role(
    WIZARD_PARTY, CAT_WORLD, PISAT_DVA
)
async def give_role_to(
    ctx: discord.ApplicationContext,
    member: discord.Option(
        discord.Member,
        description='Пользователь дискорда, кому нужна роль',
        name_localizations={'ru':'выбери_пользователя'}
    )  # type: ignore
) -> None:
    """
    Команда для выдачи роли.
    """
    wizard_paty = discord.utils.get(
            ctx.guild.roles, name=WIZARD_PARTY)
    cat_world = discord.utils.get(
            ctx.guild.roles, name=CAT_WORLD)
    pisat_dva = discord.utils.get(
            ctx.guild.roles, name=PISAT_DVA)
    check_group_leaders = {
        WIZARD_ID: WIZARD_PARTY,
        MENT_ID: CAT_WORLD,
        PVP_GODZILLA_ID: PISAT_DVA,
    }
    try:
        if str(ctx.user.id) in check_group_leaders:
            await member.add_roles(check_group_leaders.get(str(ctx.user.id)))
            await ctx.respond(
                f'_**Роль**\n{check_group_leaders.get(str(ctx.user.id)).mention}\n'
                f'**выдана**\n{member.mention}!_',
                ephemeral=True,
                delete_after=5
            )
            logger.info(
                f'Команда "/give_role_to" вызвана пользователем'
                f'"{ctx.user.display_name}", роль выдана "{member.display_name}"!'
            )
        else:
            await ctx.respond(
                '_У тебя нет доступа к этой команде!_',
                ephemeral=True,
                delete_after=3
            )
    except Exception as error:
        logger.error(f'Ошибка при вызове команды "/give_role_to": {error}')


@give_role_to.error
async def give_role_to_error(
    ctx: discord.ApplicationContext,
    error: Exception
) -> None:
    """
    Обработчик ошибок для команды random.
    """
    await command_error(ctx, error, "give_role_to")


@commands.slash_command()
@commands.has_any_role(LEADER_ROLE, TREASURER_ROLE, OFICER_ROLE)
async def check_roles(
    ctx: discord.ApplicationContext,
    message_id: discord.Option(
        str,
        description='ID сообщения, в котором есть файл',
        name_localizations={'ru':'id_сообщения'}
    )  # type: ignore
) -> None:
    """
    Команда для проверки ролей на сервере.
    """
    guild_member_list: dict[str, str] = {}
    removed_role_members: list[str] = []
    changed_role_members: list[str] = []
    embed: discord.Embed = removed_role_list_embed()
    try:
        await ctx.defer(ephemeral=True)
        
        # Получаем объекты ролей один раз в начале, чтобы избежать повторных обращений к API
        guest_role: discord.Role = discord.utils.get(ctx.guild.roles, name=GUEST_ROLE)
        sergeant_role: discord.Role = discord.utils.get(ctx.guild.roles, name=SERGEANT_ROLE)
        veteran_role: discord.Role = discord.utils.get(ctx.guild.roles, name=VETERAN_ROLE)
        officer_role: discord.Role = discord.utils.get(ctx.guild.roles, name=OFICER_ROLE)
        treasurer_role: discord.Role = discord.utils.get(ctx.guild.roles, name=TREASURER_ROLE)
        leader_role: discord.Role = discord.utils.get(ctx.guild.roles, name=LEADER_ROLE)
        
        # Создаем словарь для быстрого доступа к объектам ролей по имени
        role_dict = {
            LEADER_ROLE: leader_role,
            OFICER_ROLE: officer_role,
            VETERAN_ROLE: veteran_role,
            SERGEANT_ROLE: sergeant_role,
            GUEST_ROLE: guest_role,
            TREASURER_ROLE: treasurer_role,
        }
        
        members: list[discord.Member] = await ctx.guild.fetch_members(limit=None).flatten()
        checking_message: discord.Message = await ctx.channel.fetch_message(int(message_id))
        attachment = checking_message.attachments[0]
        bytes_data = await attachment.read()
        detected = chardet.detect(bytes_data)
        encoding = detected['encoding'] if detected['encoding'] else 'utf-8'
        try:
            lines = bytes_data.decode(encoding).splitlines()
        except UnicodeDecodeError:
            try:
                lines = bytes_data.decode('windows-1251').splitlines()
            except UnicodeDecodeError as e:
                logger.error(f"Ошибка декодирования файла: {e}")
                await ctx.respond("Ошибка: файл не может быть прочитан. Проверьте кодировку файла.")
                return

        for line in lines:
            parts = line.split(';')
            if len(parts) > 20:
                guild_member_list[parts[2]] = parts[6]
        
        for member in members:
            member_name = re.sub(r'[^a-zA-Zа-яА-ЯеЕёЁ0-9]', '', member.display_name)
            guild_rank_name = guild_member_list.get(member_name)

            guild_rank_role = role_dict.get(guild_rank_name) if guild_rank_name else None
            
            if (
                any(role in member.roles for role in [sergeant_role, veteran_role, officer_role, treasurer_role])
                and member_name not in guild_member_list
            ):
                removed_role_members.append(member.display_name)
                await member.remove_roles(sergeant_role, veteran_role, officer_role, treasurer_role)
                await member.add_roles(guest_role)
                logger.info(f'У пользователя {member.display_name} забрали роль!')
            elif (
                member_name in guild_member_list
                and guest_role not in member.roles
                and guild_rank_role not in member.roles
                and leader_role not in member.roles
            ):
                changed_role_members.append(member.display_name)
                all_roles = [sergeant_role, veteran_role, officer_role, treasurer_role, guest_role]
                await member.add_roles(guild_rank_role)
                roles_to_remove = [role for role in all_roles if role != guild_rank_role]
                for role in roles_to_remove:
                    await member.remove_roles(role)
                logger.info(f'Пользователю {member.display_name} сменили роль на {guild_rank_name}!')
        
        for i, members in enumerate([removed_role_members, changed_role_members]):
            if members:
                embed.fields[i].value += '\n'.join(f'_{member}_' for member in members)
        await ctx.respond(embed=embed)
    except Exception as error:
        await ctx.respond("❌")
        logger.error(f'Ошибка при вызове команды "/check_roles"! "{error}"')




@check_roles.error
async def check_roles_error(
    ctx: discord.ApplicationContext,
    error: Exception
) -> None:
    """
    Обработчик ошибок для команды check_roles.
    """
    await command_error(ctx, error, "check_roles")


@commands.slash_command()
@commands.has_any_role(LEADER_ROLE, OFICER_ROLE, TREASURER_ROLE)
async def clear_rcd_db_data(ctx: discord.ApplicationContext) -> None:
    """
    Команда для очистки базы данных.
    """
    await ctx.defer(ephemeral=True)
    try:
        async with async_session_factory() as session:
            await rcd_app_orm.clear_rcd_data(session)
            await ctx.respond('_Почистил_ ✅', delete_after=2)
            logger.info(
                'Команда "/clear_rcd_db_data" вызвана пользователем '
                f'"{ctx.user.display_name}"!'
            )
            await session.commit()
    except Exception as error:
        await ctx.respond(f'_Ошибка ❌: {error}_')
        logger.error(f'Ошибка при вызове команды "/clear_rcd_db_data"! "{error}"')


@clear_rcd_db_data.error
async def clear_rcd_db_data_error(
    ctx: discord.ApplicationContext,
    error: Exception
) -> None:
    """
    Обработчик ошибок для команды clear_rcd_db_data.
    """
    await command_error(ctx, error, "clear_rcd_db_data")


@commands.slash_command()
@commands.has_any_role(LEADER_ROLE, OFICER_ROLE, TREASURER_ROLE)
async def clear_pve_db_data(ctx: discord.ApplicationContext) -> None:
    """
    Команда для очистки базы данных.
    """
    await ctx.defer(ephemeral=True)
    try:
        async with async_session_factory() as session:
            await pve_app_orm.clear_pve_data(session)
            await ctx.respond('_Почистил_ ✅', delete_after=2)
            logger.info(
                'Команда "/clear_pve_db_data" вызвана пользователем '
                f'"{ctx.user.display_name}"!'
            )
            await session.commit()
    except Exception as error:
        await ctx.respond(f'_Ошибка ❌: {error}_')
        logger.error(f'Ошибка при вызове команды "/clear_pve_db_data"! "{error}"')


@clear_pve_db_data.error
async def clear_pve_data_error(
    ctx: discord.ApplicationContext,
    error: Exception
) -> None:
    """
    Обработчик ошибок для команды clear_pve_db_data.
    """
    await command_error(ctx, error, "clear_pve_db_data")


def setup(bot: discord.Bot):
    bot.add_application_command(technical_works)
    bot.add_application_command(clear_all)
    # bot.add_application_command(give_role_to)
    # bot.add_application_command(check_roles)
    bot.add_application_command(clear_rcd_db_data)
    bot.add_application_command(clear_pve_db_data)
