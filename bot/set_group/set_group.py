from idlelib import history

import discord
from discord.ext import commands
from discord.ui import View, button, Select
from loguru import logger
import uuid

from core import async_session_factory
from core import (
    LEADER_ROLE, TREASURER_ROLE, OFICER_ROLE,
    VETERAN_ROLE, SERGEANT_ROLE, LEADER_ID,
    YAGUAR_ID
)

from core.orm import set_group_orm
from .embeds import (
    set_group_embed, set_group_discription_embed,
    group_create_instruction_embed
)


class GroupManagementView(View):
    """Единая панель управления созданной группой."""

    def __init__(self, group_id: str, leader_id: int, member_ids: list):
        super().__init__(timeout=None)
        self.group_id = group_id
        self.leader_id = leader_id
        self.member_ids = member_ids

        self.grant_roles_btn = discord.ui.Button(
            label='Создать и выдать роли',
            style=discord.ButtonStyle.success,
            emoji='👑',
            custom_id=f'roles_grant_{self.group_id}',
            row=0
        )
        self.grant_roles_btn.callback = self.grant_roles_callback
        self.add_item(self.grant_roles_btn)

        self.create_channel_btn = discord.ui.Button(
            label='Создать личный канал',
            style=discord.ButtonStyle.primary,
            emoji='💬',
            custom_id=f'create_channel_{self.group_id}',
            row=0
        )
        self.create_channel_btn.callback = self.create_channel_callback
        self.add_item(self.create_channel_btn)

        self.add_player_btn = discord.ui.Button(
            label='Добавить игрока',
            style=discord.ButtonStyle.primary,
            emoji='➕',
            custom_id=f'add_player_{self.group_id}',
            row=1
        )
        self.add_player_btn.callback = self.add_player_callback
        self.add_item(self.add_player_btn)

        self.remove_player_btn = discord.ui.Button(
            label='Удалить игрока',
            style=discord.ButtonStyle.secondary,
            emoji='➖',
            custom_id=f'remove_player_{self.group_id}',  # Уникальный ID
            row=1
        )
        self.remove_player_btn.callback = self.remove_player_callback
        self.add_item(self.remove_player_btn)

        self.delete_group_btn = discord.ui.Button(
            label='Удалить группу полностью',
            style=discord.ButtonStyle.red,
            emoji='❎',
            custom_id=f'delete_group_{self.group_id}',  # Уникальный ID
            row=2
        )

        self.delete_group_btn.callback = self.delete_callback
        self.add_item(self.delete_group_btn)

    async def grant_roles_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(invisible=False, ephemeral=True)
        guild = interaction.guild

        guild_leader_role = discord.utils.get(interaction.guild.roles, name=LEADER_ROLE)
        if (interaction.user.id != self.leader_id
                and interaction.user.id != int(LEADER_ID)
                and (guild_leader_role not in interaction.user.roles)
        ):
            return await interaction.respond('_Управлять ролями может только капитан этой группы!_', delete_after=3)

        try:
            leader_user = guild.get_member(self.leader_id) or await guild.fetch_member(self.leader_id)

            async with async_session_factory() as session:
                members_in_db = await set_group_orm.get_members_by_group(session, self.group_id)

            db_users = {db_m.user_id: db_m.role_id for db_m in members_in_db}

            role_leader_id = None
            role_member_id = None

            if db_users:
                if self.leader_id in db_users and db_users[self.leader_id]:
                    role_leader_id = db_users[self.leader_id]

                for m_id in self.member_ids:
                    if m_id in db_users and db_users[m_id]:
                        role_member_id = db_users[m_id]
                        break

            base_role_name = f"КП {leader_user.display_name}"
            leader_role_name = f"{base_role_name} (ПЛ)"

            if not role_leader_id:
                role_leader = discord.utils.get(guild.roles, name=leader_role_name) or await guild.create_role(
                    name=leader_role_name, mentionable=True)
                role_leader_id = role_leader.id
            else:
                role_leader = guild.get_role(role_leader_id) or discord.utils.get(guild.roles, name=leader_role_name)

            if not role_member_id:
                role_member = discord.utils.get(guild.roles, name=base_role_name) or await guild.create_role(
                    name=base_role_name, mentionable=True)
                role_member_id = role_member.id
            else:
                role_member = guild.get_role(role_member_id) or discord.utils.get(guild.roles, name=base_role_name)

            if role_leader and role_leader not in leader_user.roles:
                await leader_user.add_roles(role_leader)

            users_to_insert = []

            if self.leader_id not in db_users:
                users_to_insert.append({
                    "user_id": leader_user.id,
                    "username": leader_user.display_name,
                    "role_id": role_leader_id,
                    "is_leader": True
                })

            for m_id in self.member_ids:
                try:
                    if m_id is None:
                        continue

                    member = guild.get_member(m_id) or await guild.fetch_member(m_id)
                    if not member:
                        continue

                    if role_member and role_member not in member.roles:
                        await member.add_roles(role_member)

                    if m_id not in db_users:
                        users_to_insert.append({
                            "user_id": member.id,
                            "username": member.display_name,
                            "role_id": role_member_id,
                            "is_leader": False
                        })
                        logger.info(f"Игроку {member.display_name} успешно выдана роль.")
                except Exception as member_err:
                    logger.error(f"Ошибка при обработке участника {m_id}: {member_err}")

            if users_to_insert:
                async with async_session_factory() as session:
                    for user_data in users_to_insert:
                        await set_group_orm.insert_group_member(
                            session,
                            user_id=user_data["user_id"],
                            username=user_data["username"],
                            role_id=user_data["role_id"],
                            group_id=str(self.group_id),
                            is_leader=user_data["is_leader"]
                        )
                    await session.commit()
                    logger.info(f"Успешно сохранено новых записей в БД: {len(users_to_insert)}")

            await interaction.respond('✅ Состав группы проверен. Роли довыданы только новым участникам!',
                                      delete_after=5)
        except Exception as error:
            logger.error(f'Ошибка при выдаче ролей: {error}')
            await interaction.respond('_Произошла ошибка при обработке ролей._', delete_after=3)

    async def create_channel_callback(self, interaction: discord.Interaction):
        try:
            guild_leader_role = discord.utils.get(interaction.guild.roles, name=LEADER_ROLE)
            if (guild_leader_role not in interaction.user.roles):
                return await interaction.respond('_Тебе не стоит этого делать!:rage: _', delete_after=5)
            view = View(CategorySelect(self.group_id, self.leader_id, self.member_ids))
            await interaction.response.send_message("Выберите категорию, в которой необходимо создать канал:",
                                                    view=view, ephemeral=True)
        except Exception as error:
            logger.error(f'Ошибка при инициализации создания канала: {error}')

    async def add_player_callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(invisible=False, ephemeral=True)
            interaction_message_embed: discord.Embed = interaction.message.embeds[0]
            interaction_message: discord.Message = interaction.message
            guild_leader_role = discord.utils.get(interaction.guild.roles, name=LEADER_ROLE)

            if (interaction.user.id != self.leader_id
                    and interaction.user.id != int(LEADER_ID)
                    and (guild_leader_role not in interaction.user.roles)
            ):
                return await interaction.respond('_Добавлять игроков может только Лидер Гильдии! ❌_', delete_after=2)

            total_current_members = len(self.member_ids) + 1
            if total_current_members >= 6:
                return await interaction.respond('_В группе уже достигнут лимит в 6 человек! ❌_', delete_after=4)

            available_slots = 6 - total_current_members

            view = View(AddPlayerSelect(
                max_values=available_slots,
                message_embed=interaction_message_embed,
                interaction_message=interaction_message,
                group_id=self.group_id,
                leader_id=self.leader_id,
                member_ids=self.member_ids
            ))
            return await interaction.respond(view=view, embed=group_create_instruction_embed(), delete_after=60)
        except Exception as error:
            logger.error(f'Ошибка при нажатии на Добавить игрока: {error}')

    async def remove_player_callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(invisible=False, ephemeral=True)
            interaction_message_embed: discord.Embed = interaction.message.embeds[0]
            interaction_message: discord.Message = interaction.message
            guild_leader_role = discord.utils.get(interaction.guild.roles, name=LEADER_ROLE)

            if (interaction.user.id != self.leader_id
                    and interaction.user.id != int(LEADER_ID)
                    and (guild_leader_role not in interaction.user.roles)
            ):
                return await interaction.respond('_Удалять игроков может только Лидер Гильдии! ❌_', delete_after=2)

            self.member_ids = [int(m) for m in self.member_ids if m is not None]
            if not self.member_ids:
                return await interaction.respond('_В составе группы нет обычных участников для удаления! ❌_',
                                                 delete_after=3)

            view = View(RemovePlayerSelect(
                message_embed=interaction_message_embed,
                interaction_message=interaction_message,
                group_id=self.group_id,
                leader_id=self.leader_id,
                member_ids=self.member_ids
            ))
            return await interaction.respond(view=view, content="**Выберите участников для удаления:**",
                                             delete_after=60)
        except Exception as error:
            logger.error(f'Ошибка при нажатии на Удалить игрока: {error}')

    async def delete_callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(invisible=False, ephemeral=True)
            interaction_message: discord.Message = interaction.message
            guild = interaction.guild
            guild_leader_role = discord.utils.get(guild.roles, name=LEADER_ROLE)

            if (guild_leader_role in interaction.user.roles
            ):
                async with async_session_factory() as session:
                    channels_data = await set_group_orm.get_group_channels(session, self.group_id)
                    members_in_db = await set_group_orm.get_members_by_group(session, self.group_id)

                for c_key in ['text', 'voice']:
                    if channels_data and channels_data.get(c_key):
                        try:
                            channel = guild.get_channel(channels_data[c_key]) or await guild.fetch_channel(
                                channels_data[c_key])
                            if channel:
                                await channel.delete()
                        except Exception as ch_err:
                            logger.error(f"Не удалось удалить канал {c_key}: {ch_err}")

                roles_to_delete_ids = set()
                for db_m in members_in_db:
                    if db_m.role_id:
                        roles_to_delete_ids.add(db_m.role_id)

                for r_id in roles_to_delete_ids:
                    role_obj = guild.get_role(r_id)
                    if role_obj:
                        try:
                            await role_obj.delete()
                            logger.info(f"Роль с ID {r_id} удалена с сервера.")
                        except Exception as role_del_err:
                            logger.error(f"Не удалось стереть роль {r_id}: {role_del_err}")

                async with async_session_factory() as session:
                    await set_group_orm.clear_group_data(session, self.group_id)
                    await session.commit()
                await interaction_message.delete()
                return await interaction.respond('✅ Группа полностью расформирована, каналы и роли удалены.',
                                                 delete_after=3)

            await interaction.respond(
                '_Удалить группу может только Лидер Гильдии! ❌_', delete_after=2)
        except Exception as error:
            logger.error(f'Ошибка при удалении группы: {error}')


class AddPlayerSelect(Select):
    """Компонент добавления новых игроков"""

    def __init__(self, max_values: int, message_embed: discord.Embed, interaction_message: discord.Message,
                 group_id: str, leader_id: int, member_ids: list):
        super().__init__(
            select_type=discord.ComponentType.user_select,
            min_values=1,
            max_values=max_values,
            placeholder='Выберите игроков для добавления'
        )
        self.message_embed = message_embed
        self.interaction_message = interaction_message
        self.group_id = group_id
        self.leader_id = leader_id
        self.member_ids = member_ids

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(invisible=False, ephemeral=True)
            embed = self.message_embed
            embed.fields[0].value = ''
            guild = interaction.guild

            new_selected_users = [user for user in self.values if
                                  user.id != self.leader_id and user.id not in self.member_ids]

            if not new_selected_users:
                return await interaction.respond('❌ Все выбранные игроки уже состоят в этой группе.', delete_after=3)

            updated_member_ids = [int(m) for m in self.member_ids if m is not None]

            async with async_session_factory() as session:
                existing_role_id = None
                if self.member_ids:
                    existing_role_id = await set_group_orm.get_role_id_by_user_and_group(session, self.member_ids[0],
                                                                                         self.group_id)

                if not existing_role_id:
                    leader_role_id = await set_group_orm.get_role_id_by_user_and_group(session, self.leader_id,
                                                                                       self.group_id)
                    if leader_role_id:
                        l_role = guild.get_role(leader_role_id)
                        if l_role:
                            base_name = l_role.name.replace(" (ПЛ)", "")
                            role_obj = discord.utils.get(guild.roles, name=base_name)
                            if role_obj:
                                existing_role_id = role_obj.id

                for user in new_selected_users:
                    updated_member_ids.append(user.id)
                    await set_group_orm.insert_group_member(
                        session, user_id=user.id, username=user.display_name,
                        role_id=existing_role_id if existing_role_id else 0, group_id=self.group_id
                    )
                    if existing_role_id:
                        member_obj = guild.get_member(user.id) or await guild.fetch_member(user.id)
                        role_obj = guild.get_role(existing_role_id)
                        if member_obj and role_obj:
                            await member_obj.add_roles(role_obj)

                await session.commit()

            leader_member = guild.get_member(self.leader_id) or await guild.fetch_member(self.leader_id)
            embed.description = f'1. {leader_member.mention}'

            members_mentions = []
            for m_id in updated_member_ids:
                m_user = guild.get_member(m_id) or await guild.fetch_member(m_id)
                if m_user:
                    members_mentions.append(m_user.mention)

            for number, member in enumerate(members_mentions):
                embed.fields[0].value += f'\n{number + 2}. {member}'

            total_slots_filled = len(updated_member_ids) + 1
            if total_slots_filled < 6:
                for extra_number in range(6 - total_slots_filled):
                    embed.fields[0].value += f'\n{extra_number + total_slots_filled + 1}.'

            new_view = GroupManagementView(self.group_id, self.leader_id, updated_member_ids)
            await self.interaction_message.edit(embed=embed, view=new_view)
            await interaction.respond('Новая обезьянка:see_no_evil: была успешно добавлена', delete_after=2)
        except Exception as error:
            logger.error(f'Ошибка при добавлении игроков: {error}')


class RemovePlayerSelect(Select):
    """Компонент удаления игроков из группы"""

    def __init__(self, message_embed: discord.Embed, interaction_message: discord.Message, group_id: str,
                 leader_id: int, member_ids: list):
        cleaned_members = [int(m) for m in member_ids if m is not None]

        super().__init__(
            select_type=discord.ComponentType.user_select,
            placeholder='Выберите участников из списка для удаления',
            min_values=1,
            max_values=len(cleaned_members) if len(cleaned_members) > 0 else 1
        )
        self.message_embed = message_embed
        self.interaction_message = interaction_message
        self.group_id = group_id
        self.leader_id = leader_id
        self.member_ids = member_ids

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(invisible=False, ephemeral=True)
            embed = self.message_embed
            embed.fields[0].value = ''
            guild = interaction.guild

            to_remove_ids = [user.id for user in self.values]

            if self.leader_id in to_remove_ids:
                return await interaction.respond(
                    'Ты хочешь удалить лидера, серьезно? А кто поведет в бой этих обезьян? :monkey:',
                    delete_after=7)
            
            current_member_ids = [int(m_id) for m_id in self.member_ids if m_id is not None]
            invalid_users = [u_id for u_id in to_remove_ids if int(u_id) not in current_member_ids]
            if invalid_users:
                return await interaction.respond(
                    'Кого ты пытаешься удалить!!! Там и нет таких людей',
                    delete_after=7)

            async with async_session_factory() as session:
                for u_id in to_remove_ids:
                    role_id = await set_group_orm.get_role_id_by_user_and_group(session, u_id, self.group_id)
                    if role_id:
                        member_obj = guild.get_member(u_id) or await guild.fetch_member(u_id)
                        role_obj = guild.get_role(role_id)
                        if member_obj and role_obj and role_obj in member_obj.roles:
                            await member_obj.remove_roles(role_obj)
                            logger.info(f"Роль с ID {role_id} снята с пользователя {member_obj.display_name}")

                db_members = await set_group_orm.get_members_by_group(session, self.group_id)
                for db_m in db_members:
                    if db_m.user_id in to_remove_ids:
                        await session.delete(db_m)
                await session.commit()

            updated_member_ids = [int(m_id) for m_id in self.member_ids if m_id is not None and int(m_id) not in to_remove_ids]

            group_leader = guild.get_member(self.leader_id) or await guild.fetch_member(self.leader_id)
            embed.description = f'1. {group_leader.mention}'

            members_mentions = []
            for m_id in updated_member_ids:
                m_user = guild.get_member(m_id) or await guild.fetch_member(m_id)
                if m_user:
                    members_mentions.append(m_user.mention)

            for number, member in enumerate(members_mentions):
                embed.fields[0].value += f'\n{number + 2}. {member}'

            total_slots_filled = len(updated_member_ids) + 1
            if total_slots_filled < 6:
                for extra_number in range(6 - total_slots_filled):
                    embed.fields[0].value += f'\n{extra_number + total_slots_filled + 1}.'

            new_view = GroupManagementView(self.group_id, self.leader_id, updated_member_ids)
            await self.interaction_message.edit(embed=embed, view=new_view)

            await interaction.respond(
                'ДОБИ теперь свободен!!!\n'
                'Игрок был удален из списка',
                delete_after=5)
        except Exception as error:
            logger.error(f'Ошибка при удаления игроков из КП: {error}')


class CategorySelect(Select):
    """Селект-меню для выбора категории под скрытые каналы"""

    def __init__(self, group_id: str, leader_id: int, member_ids: list):
        super().__init__(
            select_type=discord.ComponentType.channel_select,
            channel_types=[discord.ChannelType.category],
            placeholder='Укажите категорию для канала',
            min_values=1,
            max_values=1
        )
        self.group_id = group_id
        self.leader_id = leader_id
        self.member_ids = member_ids

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(invisible=False, ephemeral=True)
        guild = interaction.guild
        category = self.values[0]

        try:
            async with async_session_factory() as session:
                members_in_db = await set_group_orm.get_members_by_group(session, self.group_id)

            if not members_in_db:
                return await interaction.respond(
                    '_Ошибка: Данные о ролях группы не найдены в БД. Сначала нажмите "Создать и выдать роли"!_',
                    delete_after=5)

            role_leader_id = None
            role_member_id = None

            for db_m in members_in_db:
                if db_m.is_leader:
                    role_leader_id = db_m.role_id
                else:
                    role_member_id = db_m.role_id

            if not role_member_id and role_leader_id:
                pass

            role_leader = guild.get_role(role_leader_id) if role_leader_id else None
            role_member = guild.get_role(role_member_id) if role_member_id else None

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                guild.me: discord.PermissionOverwrite(view_channel=True, manage_channels=True)
            }

            if role_leader:
                overwrites[role_leader] = discord.PermissionOverwrite(
                    view_channel=True,
                    connect=True,
                    speak=True,
                    send_messages=True,
                    manage_messages=True,
                    read_message_history= True

                )

            if role_member:
                overwrites[role_member] = discord.PermissionOverwrite(
                    view_channel=True,
                    connect=True,
                    speak=True,
                    send_messages=True,
                    read_message_history=True
                )

            leader_user = guild.get_member(self.leader_id) or await guild.fetch_member(self.leader_id)
            leader_name = leader_user.display_name.lower().replace(' ', '-') if leader_user else "кп"

            channel_name_text = f"чат-{leader_name}"
            channel_name_voice = f"КП {leader_user.display_name if leader_user else ''}"

            text_channel = await guild.create_text_channel(name=channel_name_text, category=category,
                                                           overwrites=overwrites)
            voice_channel = await guild.create_voice_channel(name=channel_name_voice, category=category,
                                                             overwrites=overwrites)
            async with async_session_factory() as session:
                await set_group_orm.update_group_channel_by_type(session, self.group_id, text_channel.id, 'text')
                await set_group_orm.update_group_channel_by_type(session, self.group_id, voice_channel.id, 'voice')
                await session.commit()

            await interaction.respond(
                f"✅ Приватные каналы {text_channel.mention} и {voice_channel.mention} успешно созданы!", delete_after=5)

        except Exception as error:
            logger.error(f'Ошибка создания приватного канала: {error}')
            await interaction.respond('_Не удалось создать каналы._', delete_after=3)


class SetGroup(Select):
    """Компонент первичного выбора игроков"""

    def __init__(self, select_type=discord.ComponentType.user_select, min_values=1, max_values=6,
                 placeholder='Выбери игроков', if_edit: bool = False, message_embed: discord.Embed = None,
                 interaction_message: discord.Message = None, group_id: str = None):
        super().__init__(select_type=select_type, min_values=min_values, max_values=max_values, placeholder=placeholder)
        self.if_edit = if_edit
        self.message_embed = message_embed
        self.interaction_message = interaction_message
        self.group_id = group_id or str(uuid.uuid4())

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(invisible=False, ephemeral=True)
            guild = interaction.guild
            guild_leader_role = discord.utils.get(guild.roles, name=LEADER_ROLE)

            if guild_leader_role not in interaction.user.roles:
                return await interaction.respond('_У вас нет прав для управления группами КП! ❌_', delete_after=5)

            if not self.values:
                return await interaction.respond('_Вы не выбрали ни одного игрока! ❌_', delete_after=3)

            embed: discord.Embed = set_group_embed()
            if self.if_edit:
                embed = self.message_embed
                embed.fields[0].value = ''

            group_leader = self.values[0]
            leader_id = group_leader.id
            embed.description = f'1. {group_leader.mention}'

            raw_members = self.values[1:]
            members_mentions = [val.mention for val in raw_members]
            member_ids = [val.id for val in raw_members]

            for number, member in enumerate(members_mentions):
                embed.fields[0].value += f'\n{number + 2}. {member}'

            total_slots_filled = len(raw_members) + 1
            if total_slots_filled < 6:
                for extra_number in range(6 - total_slots_filled):
                    embed.fields[0].value += f'\n{extra_number + total_slots_filled + 1}.'

            main_view = GroupManagementView(self.group_id, leader_id, member_ids)

            if self.if_edit:
                await self.interaction_message.edit(embed=embed, view=main_view)
            else:
                await interaction.channel.send(view=main_view, embed=embed)

            monkey_str = ""
            temp = 0
            while len(self.values) > temp:
                monkey_str += ":hear_no_evil: "
                temp += 1

            await interaction.respond(
                f':white_check_mark: Новая группа обезьян, была успешно сформирована их предводитель {guild.get_member(leader_id).display_name}\n'
                f'{monkey_str}'
                , delete_after=7)
        except Exception as error:
            logger.error(f'Ошибка при обработке выбора игроков: {error}')


class SetGroupButton(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label='Создать группу', style=discord.ButtonStyle.green, emoji='📋', custom_id='СозданиеГруппы')
    async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        try:
            await interaction.response.defer(invisible=False, ephemeral=True)
            max_values = 7 if interaction.user.id in [int(YAGUAR_ID), int(LEADER_ID)] else 6
            new_group_id = str(uuid.uuid4())
            view = View(SetGroup(max_values=max_values, group_id=new_group_id))
            await interaction.respond(view=view, embed=group_create_instruction_embed(), delete_after=60)
        except Exception as error:
            logger.error(f'Ошибка при создании группы через кнопку: {error}')


@commands.slash_command()
@commands.has_any_role(LEADER_ROLE, TREASURER_ROLE, OFICER_ROLE, VETERAN_ROLE, SERGEANT_ROLE)
async def set_group(ctx: discord.ApplicationContext) -> None:
    try:
        await ctx.respond(embed=set_group_discription_embed(guild_leader=ctx.user.mention), view=SetGroupButton())
        await ctx.respond('_Кнопка для создания групп запущена!_', ephemeral=True, delete_after=2)
    except Exception as error:
        logger.error(f'Ошибка выполнения команды /set_group: {error}')


@set_group.error
async def role_application_error(ctx: discord.ApplicationContext, error: Exception) -> None:
    if isinstance(error, commands.errors.MissingAnyRole):
        await ctx.respond('Команду может вызвать только "Согильдеец"!', ephemeral=True, delete_after=10)
    else:
        raise error


def setup(bot: discord.Bot):
    bot.add_application_command(set_group)