import sqlite3
from datetime import datetime

import discord

from .embeds import remind_send_embed


# Создание базы данных
conn = sqlite3.connect('discord_bot.db')
cursor = conn.cursor()


def add_remind_to_db(user_id, message, remind_date):
    """Добавляет напоминание в базу данных"""
    cursor.execute(
        'INSERT OR REPLACE INTO reminds (user_id, message, remind_date) VALUES (?, ?, ?)',
        (user_id, message, remind_date)
    )
    conn.commit()


def delete_remind_from_db(user_id, remind_date):
    """Удаляет напоминание из базы данных"""
    cursor.execute(
        'DELETE FROM reminds WHERE user_id = ? AND remind_date = ?',
        (user_id, remind_date)
    )
    conn.commit()


async def send_reminders(bot: discord.Bot, cursor, logger):
    """
    Send reminders to users based on the reminders stored in the database.

    :param bot: The Discord bot instance
    :param cursor: The database cursor
    :param logger: The logger instance
    """
    cursor.execute('SELECT * FROM reminds ORDER BY remind_date ASC')
    reminds = cursor.fetchall()

    for remind in reminds:
        user_id, message, remind_date = remind
        remind_date = datetime.strptime(remind_date, '%Y-%m-%d %H:%M:%S')
        if remind_date < datetime.now():
            remind_date = remind_date.replace(year=(datetime.now().year) + 1)
        await discord.utils.sleep_until(remind_date)
        user = await bot.fetch_user(user_id)
        if user:
            await user.send(
                embed=remind_send_embed(
                    discord.utils.format_dt(remind_date, style="F"), message
                ),
                delete_after=300
            )
            logger.info(
                f'Напоминание отправлено пользователю {user.display_name} '
                f'после проверки БД.'
            )
            delete_remind_from_db(user_id, remind_date)
        else:
            logger.error(f'Пользователь с данным ID {user_id} не найден')
