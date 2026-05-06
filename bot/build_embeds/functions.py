import discord

from loguru import logger

from core import VETERAN_ROLE, OFICER_ROLE


async def handle_selection(
    self,
    select: discord.ui.Select,
    interaction: discord.Interaction,
    list_type: str
):
    try:
        await interaction.response.defer(invisible=False, ephemeral=True)
        select_value: list[discord.User] = select.values
        selected_list = '\n'.join(
            f'{number}. {user.mention}' for number, user
            in enumerate(select_value, start=1)
        )
        if list_type == 'banner':
            self.banner_list = selected_list
        elif list_type == 'cape':
            self.cape_list = selected_list
        await interaction.respond('✅', delete_after=1)
    except Exception as error:
        logger.error(
            f'При оформлении списка {list_type} вышла "{error}"'
        )


async def validate_amount(
    value: str,
    interaction: discord.Interaction,
    is_banner: bool = True
):
    error_message = (
        f'❌\n_Значение должно быть числом от 1 до {30 if is_banner else 10}!_'
    )

    max_value = 31 if is_banner else 11
    if value.isdigit():
        amount = int(value)
        if 0 < amount < max_value:
            return amount
    return await interaction.respond(error_message, delete_after=3)


async def generate_member_list(
    nicknames: list,
    interaction: discord.Interaction
) -> str:
    member_list = ''
    members: list[discord.Member] = interaction.guild.members

    for index, nickname in enumerate(nicknames, start=1):
        member: discord.Member | None = discord.utils.get(
            members,
            display_name=nickname
        )
        member_list += f'{index}. {nickname}'
        if member:
            member_list += f' | Discord: {member.mention}'
        member_list += '\n'

    return member_list


async def sort_nicknames_by_role(
    members: list[discord.Member],
    roles: list[discord.Role],
    result: list[str]
) -> list[str]:
    veteran_role: discord.Role | None = discord.utils.get(
        roles, name=VETERAN_ROLE
    )
    sorted_result: list[str] = []

    for nickname in result:
        member: discord.Member | None = discord.utils.get(
            members,
            display_name=nickname
        )
        if member and veteran_role in member.roles:
            continue
        sorted_result.append(nickname)
    return sorted_result
