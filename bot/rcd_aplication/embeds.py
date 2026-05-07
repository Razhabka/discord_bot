import discord

from core import (
    ATTENTION, CROSSED_SWORDS_IMAGE_URL,
    RCD_LIST_IMAGE_URL, QUESTION_IMAGE_URL, INDEX_CLASS_ROLE,
    EXCLAMATION_MARK_URL
)


def start_rcd_embed(date: str) -> discord.Embed:
    """
    Функция для создания вложения о старте РЧД заявок.
    """
    embed = discord.Embed(
        title=f'_**Заявки на РЧД {date}**_',
        description=(
            '_Тыкай на кнопку ниже, чтобы подать заявку ⬇️\n\n'
            'Ряд приоритетных классов:\n'
            '- Воин (танк)\n- Инженер (саппорт)\n- Жрец (хилл)\n- Мистик\n'
            '- Лучник\n- Паладин\n- Маг\n\n'
            'Остальные классы не вписываются в мету и попросту не играются на РЧД. '
            'В связи с этим убедительная просьба искать возможность заливать '
            'классы в соответствии со списком выше. Если у вас нет возможности '
            'залить нужный класс, то приоритет выбора игрока на РЧД у вас будет '
            'минимальным.\n'
            'Уведомление о том, что ты входишь в состав и на каком классе пришлёт '
            'бот в личные сообщения! Если уведомлений нет, значит вы не попали в рейд.\n' 
            'Сами списки обычно готовятся во вторник к ~22:00 по МСК!\n\n'
            f'Игроков в составе ждём в\n 2️⃣0️⃣:1️⃣5️⃣ {date} на сбор_ 💪!'
        ),
        color=0xfffb00
    )
    embed.set_thumbnail(url=CROSSED_SWORDS_IMAGE_URL)
    return embed


def app_list_embed(date: str) -> discord.Embed:
    """
    Функция для создания вложения о списке поданных РЧД заявок.
    """
    embed = discord.Embed(
        title=f'_**Список поданных заявок на РЧД {date}**_',
        color=0xfffb00
    )
    embed.add_field(
        name='-------------------- **Ветераны** --------------------',
        value='',
        inline=False
    )
    embed.add_field(
        name='-------------------- **Старшины** --------------------',
        value='',
        inline=False
    )
    embed.set_thumbnail(url=RCD_LIST_IMAGE_URL)
    return embed


def ask_veteran_embed(member: discord.Member, date: str) -> discord.Embed:
    """
    Функция для создания вложения всем ветеранам.
    """
    embed = discord.Embed(
        title=ATTENTION,
        description=(
            f'_Рассылка от пользователя {member.display_name}\n\n'
            f'Вопрос - можешь пойти на РЧД {date}?\n'
            f'Если да, заполни пожалуйста заявку на РЧД 😊_!\n\n'
            f'-# Сообщение автоматически удалится через сутки, если не ответить!'
        ),
        color=0xfffb00
    )
    embed.set_thumbnail(url=QUESTION_IMAGE_URL)
    return embed


def rcd_list_embed(date: str, action: str) -> discord.Embed:
    """
    Функция для создания вложения о финальном списке РЧД.
    """
    embed = discord.Embed(
        title=f'_**Список РЧД ({action}) {date}**_',
        color=0xfffb00
    )
    for role in INDEX_CLASS_ROLE.values():
        embed.add_field(
            name=role,
            value='',
            inline=False
        )
    embed.set_thumbnail(url=RCD_LIST_IMAGE_URL)
    return embed


def publish_rcd_embed(date: str) -> discord.Embed:
    """
    Функция для создания вложения с публикацией списка РЧД.
    """
    embed = discord.Embed(
        title=f'_**Список РЧД (АТАКА) {date}**_',
        color=0xfffb00
    )
    embed.set_thumbnail(url=CROSSED_SWORDS_IMAGE_URL)
    return embed


def publish_rcd_second_embed(date: str) -> discord.Embed:
    """
    Функция для создания вложения с публикацией списка РЧД.
    """
    embed = discord.Embed(
        title=f'_**Список РЧД (ЗАЩИТА) {date}**_',
        color=0xfffb00
    )
    embed.set_thumbnail(url=CROSSED_SWORDS_IMAGE_URL)
    return embed


def rcd_notification_embed(
    interaction_user: str,
    date: str,
    jump_url: str | None,
    rcd_role: str
) -> discord.Embed:
    """
    Функция для создания вложения о включении пользователя в список РЧД.
    """
    delete_notification = "\n\n-# Сообщение автоматически удалится через 18 часов!"
    embed = discord.Embed(
        title=f'_**РЧД {date}**_',
        description=(
            '_**Сообщаем то, что тебя включили в список РЧД!**'
            f'\n\nТребуемый класс: **{rcd_role[:-2]}**_'
            f'\n\n_Если по какой-то причине ты не можешь присутствовать, отпишись {interaction_user}❗_'
            # f'{
            #     f"\n\n_Не забудь оставить реакцию, о прочтении ✅ в канале:\n{jump_url}_"
            #     f"{delete_notification}" if jump_url else f"{delete_notification}"ь
            # }'
        ),
        color=0xfffb00
    )
    embed.set_thumbnail(url=CROSSED_SWORDS_IMAGE_URL)
    return embed


def mailing_notification_embed(date: str) -> discord.Embed:
    """
    Функция для отправки уведомления о рассылке.
    """
    embed = discord.Embed(
        title=ATTENTION,
        description=(
            f'_**Сообщаем то, что уведомления участникам РЧД из списка на {date} были разосланы! '
            'Если бот не прислал вам сообщение, значит вы не попали в список!**_'
        ),
        color=0xfffb00
    )
    embed.set_thumbnail(url=EXCLAMATION_MARK_URL)
    return embed
