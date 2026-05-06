import datetime
import re

from core import NOT_SOLD


def convert_bid(bid: int) -> str:
    """
    Функция для конвертирования стартовой стоимости лота
    в вид к примеру "800K" или "1.2M" в десятичную систему.
    """
    if bid < 1000:
        return str(bid)
    elif 1000 <= bid < 1000000:
        return f"{bid / 1000:.0f}K"
    else:
        return f"{bid / 1000000:.1f}M" if bid % 1000000 != 0 else f"{bid / 1000000:.0f}M"


def convert_bid_back(bid: str) -> int:
    """
    Функция для конвертирования строки в формате "800K" или "1.2M"
    в десятичную систему.
    """
    if bid.endswith('K'):
        return int(float(bid[:-1]) * 1000)
    elif bid.endswith('M'):
        return int(float(bid[:-1]) * 1000000)
    else:
        return int(bid)


def convert_to_mention(
    label_values: list,
    button_mentions: dict
) -> list:
    """
    Функция преобразует никнейм игрока на кнопке в тэг,
    для вывода списка победителей.
    """
    result = list()
    for value in label_values:
        split_value = value.split()
        if len(split_value) > 1:
            split_value[-1] = button_mentions[split_value[-1]]
            result.append(' '.join(split_value))
        else:
            result.append(NOT_SOLD)
    return result


def convert_sorted_message(values: str) -> str | float:
    """
    Функция помощник для сортировки с учетом тысяч или миллионов.
    """
    if values == NOT_SOLD:
        return values
    cost = values.split()[0]
    cost_mult = (
        1_000_000 if cost[-1] == 'M' else 1_000 if cost[-1] == 'K' else 1
    )
    cost = float(cost[:-1]) * cost_mult
    return cost


def seconds_until_date(target_date_time: str) -> int | str:
    """
    Функция считает количество секунд до определенной даты и времени.
    """
    pattern = r'^([0-2][0-9]|3[0-1])[.,/](0[1-9]|1[0-2]) ([0-1][0-9]|2[0-3])[:;]([0-5][0-9])$'
    match = re.match(pattern, target_date_time)
    if not match:
        return 'Неверный формат. Ожидался ДД.ММ ЧЧ:ММ'
    day, month, hour, minute = map(int, match.groups())
    target_datetime = datetime.datetime(
        datetime.date.today().year,
        month, day, hour, minute
    )
    if target_datetime < datetime.datetime.now():
        target_datetime = target_datetime.replace(
            year=(datetime.datetime.now().year) + 1
        )
    now = datetime.datetime.now()
    time_diff = target_datetime - now
    seconds_until = time_diff.total_seconds()
    return int(seconds_until)
