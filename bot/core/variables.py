from core import settings


# Никнейм лидера гильдии
LEADER_NICKNAME: str = 'Mirra'

LEADER_ID: str = '421014252707512373'

# Числовые переменные
DEAFAULT_RANDOMISE_VALUE: str = '1-100'

MIN_BID_VALUE: int = 100000

APPLICATION_CHANNEL_ID = settings.application_channel_id

RCD_APPLICATION_CHANNEL_ID = settings.rcd_application_channel_id

PVE_CHANNEL_ID = settings.pve_channel_id

PVE_APPLICATION_CHANNEL_ID = settings.pve_app_channel_id

ASK_RCD_MESSAGE_DELETION = 86400

# Текстовые переменные с фразами
AUC_CHEAT: str = (
    '_Не дружище, это кнопка была сделана для того '
    'можно было отменить случайную ставку! 😊\n'
    'Абузить в обратную сторону эту механику не '
    'получится 😈_'
)

ACCESS_VALUE: str = (
    '_Рекомендую посетить текстовый канал '
    '[НАВИГАЦИЯ](https://discord.com/channels/1017533668341850112/1497562750153392229) '
    'там ты сможешь найти полезную информацию о том, '
    'где что находится и к кому можно обратиться за помощью!_'
)

ANSWER_IF_CHEAT: str = (
    f'🤷‍♂️\n_В оружейке Аллодов\nНа сервере: НитьСудьбы\nВо фракции: Империя\n'
    f'такого никнейма не нашлось.\n'
    f'Проверь, правильно ли ты ввел свой ник, а именно:\n\n'
    f'1) Проверь написание больших и маленьких букв\n'
    f'2) В никнейме не должно быть пробелов\n'
    f'3) Не нужно в скобках указывать своё реальное имя\n\n'
    f'Как все проверил, попробуй снова отправить форму👌\n'
    f'Если ничгео не помогло, обратись к "{LEADER_NICKNAME}" в ЛС👍_'
)

ANSWER_IF_CLICKED_THE_SAME_TIME: str = (
    '_Ты одновременно с кем-то нажал на кнопку'
    'Ниче не сломалось, ответ был отправлен!👍_'
)

ANSWER_IF_DUPLICATE_APP: str = (
    f'☝️\n_Ты уже подал заявку, повторное отправление будет игнорироваться.\n\n'
    f'Если ты не подавал заявку, но при этом видишь это собщение, '
    f'обратись к {LEADER_NICKNAME} в ЛС_!'
)

ANSWER_IF_DUPLICATE_NICK: str = (
    f'🤷‍♂️\n_Такой никнейм уже имеется среди игроков с доступом.\n\n'
    f'Если твой ник кто-то использует в этом дискорде, '
    f'обратись к {LEADER_NICKNAME} в ЛС_!'
)

ANSWERS_IF_NO_ROLE: str = '_У тебя нет доступа ❌_'

ATTENTION: str = '【В】【Н】【И】【М】【А】【Н】【И】【Е】'

REMIND: str = '【Н】【А】【П】【О】【М】【Н】【Ю】'

TO_REMIND: str = '【Н】【А】【П】【О】【М】【Н】【И】【Т】【Ь】'

CATCH_BUG_MESSAGE: str = (
    f'_Ботец словил багулю, попробуй еще раз! Если не поможет, '
    f'напиши {LEADER_NICKNAME} 👍_'
)

GUILD_NAME: str = 'Мрачный Жнец'

TEСHNICAL_WORKS: str = '_Скоро запустим!_👌'

WRONG_PARMS: str = '_Неверно заданы параметры, повтори снова!🔁_'

RANK_MAPPING = {
    0: "Лидер",
    1: "Казначей",
    2: "Офицер",
    3: "Ветеран",
    4: "Старшина",
    5: "Рядовой",
    6: "Дублёр",
    7: "Новобранец",
    8: "Штрафник",
    9: "Изгой"
}

CLOAK_MAPPING = {
    0: "Нет накидки",
    1: "Гильдейская накидка (красная)",
    2: "Чемпионская накидка",
    3: "Знамя 1-го поколения",
    4: "Знамя 2-го поколения",
    5: "Знамя 3-го поколения"
}

INDEX_CLASS_ROLE: dict[int, str] = {
    0: 'Воины:',
    1: 'Инженеры:',
    2: 'Язычники:',
    3: 'Барды:',
    4: 'Жрецы:',
    5: 'Некроманты:',
    6: 'Храмовники:',
    7: 'Мистики:',
    8: 'Разведчики:',
    9: 'Волшебники:',
    10: 'Демонологи:'
}

TRANSLATION_ROLES: dict[str, str] = {
    'Воин': 'Warrior',
    'Инженер': 'Engineer',
    'Жрец': 'Priest',
    'Паладин': 'Paladin',
    'Шаман': 'Druid',
    'Мистик': 'Psyonic',
    'Лучник': 'Scout',
    'Маг': 'Mage',
    'Некромант': 'Necromancer',
    'Бард': 'Bard',
    'Демон': 'Demonologist'
}

# Роли на сервере Discord для проверки
NOT_NOTICE_FOR_RCD: int= 1528343688072138772

AUCTIONEER_ROLE: str = 'Аукцион'

LEADER_ROLE: str = 'Лидер гильдии'

OFICER_ROLE: str = 'Офицер'

TREASURER_ROLE: str = 'Казначей'

SERGEANT_ROLE: str = 'Старшина'

VETERAN_ROLE: str = 'Ветеран'

PVE_ROLE: str = 'ПВЕ'

DULL_LIGHTS_ROLE: str = 'Глухие Огни'

GUEST_ROLE: str = 'На краю тишины'

WIZARD_PARTY: str = 'Пачка Визарда'

MENT_ID: str = '692306305301610536'

CAT_WORLD: str = 'Кошкомир'

PVP_GODZILLA_ID: str = '1017736389950963763'

PISAT_DVA: str = '+7(952)812(52)'

WIZARD_ID: str = '356014672450945034'

NOT_SOLD: str = 'Лот не был выкуплен'

YAGUAR_ID: str = '598205276121726996'


class StaticNames:
    """Костантные наименования для работы с РЧД списками"""
    ATACK: str = 'АТАКА'
    DEFENCE: str = 'ЗАЩИТА'
    RCD_DATE: str = 'rcd_date'
    RCD_LIST_MESSAGE: str = 'rcd_list_message'
    RCD_APPCHANNEL_MESSAGE: str = 'rcd_appchannel_message'
    START_RCD_MESSAGE: str = 'start_rcd_message'
    RCD_LIST_CHANNEL: str = 'rcd_list_channel'


ACCESS_IMAGE_URL: str = 'https://cdn.discordapp.com/attachments/1492227631821619323/1510029209731338370/content_1.png?ex=6a1b53ca&is=6a1a024a&hm=78d5edc01fac16abe6c519c34d67d0c32d1a2f15dfdb7237743890cb9aa89170&'

AUCTION_IMAGE_URL: str = 'https://media.discordapp.net/attachments/1182584501147279491/1243512304918859899/bdf1f4750907e2d7.png?ex=6651be94&is=66506d14&hm=b53497728a4f60c4d9a801401a64b9dad4fdcf150eb09bcefdae51b0bbb94c72&=&format=webp&quality=lossless&width=825&height=477'

# DENIED_IMAGE_URL: str = 'https://media.discordapp.net/attachments/1182584501147279491/1235613979468890203/620aa731fdd06c8a3fcbb87c_X-p-3200.png?ex=663502b1&is=6633b131&hm=aea28542a471088120a83b916423296a7e31076ef5194ea03fac5dc7cb8d8c55&=&format=webp&quality=lossless&width=640&height=640'
DENIED_IMAGE_URL: str = 'https://cdn.discordapp.com/attachments/1492227631821619323/1510029523650089210/content_2.png?ex=6a1b5415&is=6a1a0295&hm=5e20a0d0be25661541ab446b8d6f1135b18437d5a689ae192a2460f227ecf3ce&'

GUILD_IMAGE_URL: str = 'https://media.discordapp.net/attachments/1416557848992677939/1497593815568093274/ChatGPT_Image_Apr_25_2026_03_41_08_PM.png?ex=69ee166d&is=69ecc4ed&hm=408280cd2320d2987b826166c7aa30aef7e1b328296031b41b7a87ba3d289ef4&=&format=webp&quality=lossless&width=968&height=968'

PLAYING_DICES_URL_ICON: str = 'https://media.discordapp.net/attachments/1182584501147279491/1235613464194584689/dice_PNG64.png?ex=66350236&is=6633b0b6&hm=d7df1ef64c9d647e0fa292199bf7be5160d2f95d6fecc4aa61622fe4bd9649e1&=&format=webp&quality=lossless&width=951&height=640'

SMALL_GUILD_ICON_URL: str = 'https://media.discordapp.net/attachments/1416557848992677939/1497594289679765534/ChatGPT_Image_Apr_25_2026_03_42_18_PM.png?ex=69ee16de&is=69ecc55e&hm=4edd9203bc410a469bd8a18fe2232d40030bb2ceb82ab3b3145ead95ffef7935&=&format=webp&quality=lossless&width=968&height=968'

WRENCH_IMAGE_URL: str = 'https://media.discordapp.net/attachments/1182584501147279491/1235611311896002600/1672451474_flomaster-club-p-gaechnii-klyuch-risunok-dlya-detei-vkontak-16.png?ex=66350035&is=6633aeb5&hm=0055b69a7b0ba64d904bc8e2b1fb4057ae3ee781312920e5b6508b036b707d35&=&format=webp&quality=lossless&width=960&height=480'

RENAME_IMAGE_URL: str = 'https://media.discordapp.net/attachments/1182584501147279491/1263864947536953364/img_179340.png?ex=669bc974&is=669a77f4&hm=fe1145063b7db4d0a9800f58a89b8f6e346147cfb505ac2667723ddf340340c4&=&format=webp&quality=lossless&width=640&height=640'

REMIND_IMAGE_URL: str = 'https://media.discordapp.net/attachments/1416557848992677939/1497594289679765534/ChatGPT_Image_Apr_25_2026_03_42_18_PM.png?ex=69ee16de&is=69ecc55e&hm=4edd9203bc410a469bd8a18fe2232d40030bb2ceb82ab3b3145ead95ffef7935&=&format=webp&quality=lossless&width=968&height=968'

CROSSED_SWORDS_IMAGE_URL: str = 'https://media.discordapp.net/attachments/1182584501147279491/1269949509949980683/5fe0343e0f96803c.png?ex=66b1ec25&is=66b09aa5&hm=6bad797e84b11945ab62856b5622e76e51f07dc0cb8881653af79699feb623ad&=&format=webp&quality=lossless&width=655&height=655'

RCD_LIST_IMAGE_URL: str = 'https://media.discordapp.net/attachments/1182584501147279491/1269955937477595186/53ceb6140f73a909.png?ex=66b1f222&is=66b0a0a2&hm=e4ca7be4622f4f57266d1de76d976dfef5cc35d5ea271690e2ba16197988e2b7&=&format=webp&quality=lossless&width=655&height=655'

QUESTION_IMAGE_URL: str = 'https://media.discordapp.net/attachments/1182584501147279491/1269967902736515192/ad65f1ccea7e0e37.png?ex=66b1fd46&is=66b0abc6&hm=bbd1f02d4997fc7652427d220754cb689456635c9d9c4dea8fd84e4a2e998121&=&format=webp&quality=lossless&width=492&height=655'

EXCLAMATION_MARK_URL: str = 'https://media.discordapp.net/attachments/1416557848992677939/1497594289679765534/ChatGPT_Image_Apr_25_2026_03_42_18_PM.png?ex=69ee16de&is=69ecc55e&hm=4edd9203bc410a469bd8a18fe2232d40030bb2ceb82ab3b3145ead95ffef7935&=&format=webp&quality=lossless&width=968&height=968'

PVE_URL: str = 'https://media.discordapp.net/attachments/1182584501147279491/1452272864928596100/PVEpng.png?ex=69493600&is=6947e480&hm=2f1e0ccfa0b80368425afa6a5439623e4eab5ce41ce71b096f18cd73735d585c&=&format=webp&quality=lossless'