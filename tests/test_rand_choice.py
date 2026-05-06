import pytest
from bot.randomaizer.functions import rand_choice


def test_single_nickname():
    """Тест для проверки количества введённых параметров"""
    result = rand_choice('nickname')
    assert result is None, 'Функция должна вернуть None для одного никнейма'

@pytest.mark.parametrize('nicknames', [
    ('nickname1, nickname2 nickname3'),
    ('user1_user2, user3 user4'),
    ('winner loser'),
])
def test_multiple_nicknames(nicknames):
    """Тест для проверки знаков перечисления в ведённых параметрах"""
    result = rand_choice(nicknames)
    assert result is not None, 'Функция должна вернуть сообщение для нескольких никнеймов'
    assert 'Победитель:' in result, 'Результат должен содержать информацию о победителе'

@pytest.mark.parametrize('range_str, expected_min, expected_max', [
    ('1-10', 1, 10),
    ('5-15', 5, 15),
    ('100-200', 100, 200),
])
def test_numerical_range(range_str, expected_min, expected_max):
    """Тест для проверки правильности выбора вводимых диапазонов"""
    result = rand_choice(range_str)
    assert isinstance(result, int), 'Функция должна вернуть целое число для числового диапазона'
    assert expected_min <= result <= expected_max, f'Случайное число должно быть в диапазоне от {expected_min} до {expected_max}'

@pytest.mark.parametrize('range_str', [('15-5'), ('5-nickname')])
def test_numerical_range_invalid(range_str):
    """Тест на валидность введённого диапазона"""
    result = rand_choice(range_str)
    assert result is None, 'Функция должна вернуть None для некорректного диапазона'
