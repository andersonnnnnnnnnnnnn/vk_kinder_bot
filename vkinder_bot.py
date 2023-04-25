import vk_api
from vk_api import longpoll
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from datetime import datetime
import time
import operator
import psycopg2
from vk_api.utils import get_random_id

TOKEN = "vk1.a.t2m2uvRInlGHKRERKsFonZ2Af2nhRDxIvlhp6AO9NqVx1lVx7Y3EIjzn93k4T54ctiWQJx9RtEYzAYasC9PHBl3nnIYAc-1uCeivJvVP6xemgDulUOapNtaeneE4irgpga0mDpbD3feZi-S7LL-ca0TO7r0SVQp4A2o2xQnBcZs5e267gfOzJS4ytxQmVn8fgqp58Gfb0vjBlkYdpQE5aQ"
GROUP_ID = 220038781
APP_ID = '51622190'
USER_LOGIN = '89859593227'
USER_PASSWORD = 'gaueish238_Sj#'


import sqlite3

def create_database():
    conn = sqlite3.connect('vk_bot.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS shown_users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER UNIQUE
                     )''')
    conn.commit()
    conn.close()

def add_shown_user(user_id):
    conn = sqlite3.connect('vk_bot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO shown_users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def was_user_shown(user_id):
    conn = sqlite3.connect('vk_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM shown_users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def create_keyboard():
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button('Поиск людей группы', color=VkKeyboardColor.POSITIVE)
    keyboard.add_line()
    keyboard.add_button('Информация обо мне', color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button('Начать поиск', color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()

def connect_to_db():
    conn = psycopg2.connect(
        user='postgres',
        password='12345',
        host='localhost',
        port='5432',
        database='vkinder'
    )
    return conn

def update_or_insert_user(conn, user_info):
    cursor = conn.cursor()
    select_query = f"SELECT * FROM users WHERE vk_id = {user_info['id']}"
    cursor.execute(select_query)
    existing_user = cursor.fetchone()

    if existing_user:
        update_query = f"""UPDATE users SET
                           first_name = %s,
                           last_name = %s,
                           sex = %s,
                           city = %s,
                           age = %s,
                           relation_status = %s
                           WHERE vk_id = %s"""
        cursor.execute(update_query, (
            user_info['first_name'],
            user_info['last_name'],
            user_info.get('sex', None),
            user_info.get('city', {}).get('title', None),
            calculate_age(user_info.get('bdate')),
            user_info.get('relation', None),
            user_info['id']
        ))
    else:
        insert_query = f"""INSERT INTO users (vk_id, first_name, last_name, sex, city, age, relation_status)
                           VALUES (%s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(insert_query, (
            user_info['id'],
            user_info['first_name'],
            user_info['last_name'],
            user_info.get('sex', None),
            user_info['city']['title'] if isinstance(user_info.get('city'), dict) else None,
            calculate_age(user_info.get('bdate')),
            user_info.get('relation', None)
        ))

    conn.commit()
    cursor.close()

def get_user_from_db(conn, vk_id):
    cursor = conn.cursor()
    select_query = f"SELECT * FROM users WHERE vk_id = {vk_id}"
    cursor.execute(select_query)
    existing_user = cursor.fetchone()
    cursor.close()
    return existing_user

def captcha_handler(captcha):
    url = captcha.get_url()
    print(f"Откройте ссылку и введите код с изображения: {url}")
    captcha_key = input("Введите код с капчи: ")
    return captcha.try_again(captcha_key)

def format_user_info(user_info):
    if isinstance(user_info, tuple):
        _, vk_id, first_name, last_name, sex, city, age, relation, *_ = user_info
        sex = 'Мужской' if sex == '2' else 'Женский' if sex == '1' else 'Не указан'
        relation = get_relation_status(int(relation))
    else:
        first_name = user_info['first_name']
        last_name = user_info['last_name']
        vk_id = user_info['id']
        sex = 'Мужской' if user_info.get('sex') == 2 else 'Женский' if user_info.get('sex') == 1 else 'Не указан'
        city = user_info.get('city')
        if city:
            city = city.get('title', 'Не указан')
        else:
            city = 'Не указан'
        relation = get_relation_status(user_info.get('relation', 0))
        age = calculate_age(user_info.get('bdate'))

    user_link = f"vk.com/id{vk_id}"

    user_text = f"{first_name} {last_name} - {user_link}\n" \
                 f"Пол: {sex}\n" \
                 f"Город: {city}\n" \
                 f"Возраст: {age}\n" \
                 f"Семейное положение: {relation}"
    return user_text



def get_user_info(vk, user_id):
    user_fields = 'city,bdate,sex,relation'
    user_info = vk.users.get(user_id=user_id, fields=user_fields)
    return user_info[0]


def find_matching_users(user_info, members_info):
    matching_users = []

    for member_info in members_info:
        if member_info.get('sex') == user_info.get('sex'):
            continue

        if user_info.get('city', {}).get('id') != member_info.get('city', {}).get('id'):
            continue

        if member_info.get('relation', 0) not in [0, 1, 6]:
            continue

        age = calculate_age(member_info.get('bdate'))
        user_age = calculate_age(user_info.get('bdate'))

        if age == 'Не указан' or user_age == 'Не указан' or abs(user_age - age) > 5:
            continue

        matching_users.append(member_info)

    return matching_users

def get_group_members(vk):
    members = []
    offset = 0
    while True:
        response = vk.groups.getMembers(group_id=GROUP_ID, offset=offset)
        if not response['items']:
            break
        members.extend(response['items'])
        offset += 1000
    return members


def get_members_info(vk, member_ids):
    user_fields = 'city,bdate,sex,relation'
    users_info = vk.users.get(user_ids=member_ids, fields=user_fields)
    return users_info


def calculate_age(bdate):
    if not bdate:
        return 'Не указан'
    try:
        birth_date = datetime.strptime(bdate, "%d.%m.%Y")
        today = datetime.today()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        return age
    except ValueError:
        return 'Не указан'

def create_yes_no_keyboard():
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button('Да', color=VkKeyboardColor.POSITIVE)
    keyboard.add_line()
    keyboard.add_button('Нет', color=VkKeyboardColor.NEGATIVE)
    return keyboard.get_keyboard()

def calculate_age_range(bdate):
    age = calculate_age(bdate)
    if age == 'Не указан':
        return None, None
    age_from = age - 5 if age > 5 else 1
    age_to = age + 5
    return age_from, age_to


def ask_for_missing_data(vk_bot, user_id):
    vk_session_bot = vk_api.VkApi(token=TOKEN)
    longpoll = VkBotLongPoll(vk_session_bot, GROUP_ID)
    questions = [
        {"question": "Введите ваше имя:", "field": "first_name"},
        {"question": "Введите вашу фамилию:", "field": "last_name"},
        {"question": "Введите ваш пол (Мужской/Женский):", "field": "sex"},
        {"question": "Введите ваш город:", "field": "city"},
        {"question": "Введите ваш возраст:", "field": "age"},
        {"question": "Введите ваше семейное положение:", "field": "relation_status"},
    ]

    user_info = {"id": user_id}

    for question in questions:
        vk_bot.messages.send(
            user_id=user_id,
            message=question["question"],
            random_id=0
        )

        for event in longpoll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW and event.from_user:
                answer = event.obj.message['text']
                user_info[question["field"]] = answer.strip()
                break


    if user_info['sex'].lower() in ['мужской', 'male']:
        user_info['sex'] = 2
    elif user_info['sex'].lower() in ['женский', 'female']:
        user_info['sex'] = 1
    else:
        user_info['sex'] = 0


    try:
        user_info['age'] = int(user_info['age'])
    except ValueError:
        user_info['age'] = None


    relation_status = user_info['relation_status'].lower()
    relation_id = get_relation_status(relation_status)
    user_info['relation_status'] = relation_id

    return user_info


def get_relation_status(relation):
    statuses = {
        0: "Не указан",
        1: "Не женат/не замужем",
        2: "Есть друг/подруга",
        3: "Помолвлен/помолвлена",
        4: "Женат/замужем",
        5: "Всё сложно",
        6: "В активном поиске",
        7: "Влюблён/влюблена",
        8: "В гражданском браке"
    }
    return statuses.get(relation, "Не указан")


def get_top_3_photos(vk, user_id):
    try:
        photos = vk.photos.get(owner_id=user_id, album_id='profile', extended=1)
    except vk_api.exceptions.ApiError as e:
        if e.code == 30:
            return []
        else:
            raise e

    top_photos = sorted(photos['items'], key=lambda x: x['likes']['count'], reverse=True)[:3]

    attachments = []
    for photo in top_photos:
        attachments.append(f"photo{photo['owner_id']}_{photo['id']}")

    return attachments

def extract_name_tag_from_link(link):
    if link.startswith('https://'):
        link = link[8:]
    elif link.startswith('http://'):
        link = link[7:]

    if link.startswith('vk.com/'):
        name_tag = link[7:]
    elif link.startswith('www.vk.com/'):
        name_tag = link[11:]
    else:
        name_tag = None

    return name_tag

def two_factor_handler():
    code = input("Enter two-factor authentication code: ")
    remember_device = False
    return code, remember_device


def get_user_preferences(user_id, vk_bot):
    user_info = get_user_info(vk_bot, user_id)
    age = calculate_age(user_info.get('bdate'))
    sex = user_info.get('sex')
    city = user_info.get('city', {}).get('title')
    relation = user_info.get('relation')

    return {
        'age': age,
        'sex': sex,
        'city': city,
        'relation': relation
    }

def find_matches(vk_bot, user_id, user_preferences):
    search_params = {
        'age_from': user_preferences['age'] - 2,
        'age_to': user_preferences['age'] + 2,
        'sex': 1 if user_preferences['sex'] == 2 else 2,
        'city': user_preferences['city'],
        'status': user_preferences['relation'],
        'count': 10
    }

    search_results = vk_bot.users.search(**search_params)

    return search_results['items']


def get_top_photos(vk_user, user_id):
    try:
        photos = vk_user.photos.getAll(owner_id=user_id, extended=1, no_service_albums=1)
    except vk_api.exceptions.ApiError:
        return []

    if not photos['items']:
        return []

    sorted_photos = sorted(photos['items'],
                           key=lambda x: x['likes']['count'] + (x['comments']['count'] if 'comments' in x else 0),
                           reverse=True)
    top_photos = sorted_photos[:3]
    top_photos_attachments = []
    for photo in top_photos:
        attachment = f"photo{photo['owner_id']}_{photo['id']}"
        top_photos_attachments.append(attachment)

    return top_photos_attachments


def create_next_keyboard():
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button('Далее', color=VkKeyboardColor.PRIMARY)
    return keyboard.get_keyboard()


def send_match_info(vk_bot, user_id, match, top_photos_attachments):
    try:
        first_name = match['first_name']
        last_name = match['last_name']
        sex = 'Мужской' if match.get('sex') == 2 else 'Женский' if match.get('sex') == 1 else 'Не указан'
        city = match.get('city', {}).get('title', 'Не указан')
        relation = get_relation_status(match.get('relation', 0))
        age = calculate_age(match.get('bdate'))
        member_link = f"vk.com/id{match['id']}"
        match_text = f"{first_name} {last_name} - {member_link}\n" \
                     f"Пол: {sex}\n" \
                     f"Город: {city}\n" \
                     f"Возраст: {age}\n" \
                     f"Семейное положение: {relation}\n" \
                     f"Топ-3 фотографии:"
        vk_bot.messages.send(
            user_id=user_id,
            message=match_text,
            attachment=','.join(top_photos_attachments),
            random_id=0
        )
        return True
    except vk_api.exceptions.ApiError:
        return False


def enough_info(user_info):
    required_fields = ['sex', 'city', 'bdate', 'relation']
    return all(field in user_info for field in required_fields)

def search_for_matches(vk_user, user_info, offset=0):
    age_from, age_to = calculate_age_range(user_info.get('bdate'))
    sex = 1 if user_info.get('sex') == 2 else 2 if user_info.get('sex') == 1 else None
    city_id = user_info.get('city', {}).get('id')
    status = user_info.get('relation')

    search_params = {
        'city': city_id,
        'sex': sex,
        'status': status,
        'count': 1000,
        'offset': offset,
        'fields': 'id,first_name,last_name,photo_200,sex,bdate,city,relation',
    }

    if age_from and age_to:
        search_params['age_from'] = age_from
        search_params['age_to'] = age_to

    search_results = vk_user.users.search(**search_params)


    filtered_results = [match for match in search_results['items'] if not was_user_shown(match['id'])]

    return filtered_results




def process_search_results(vk_bot, user_id, search_results):
    for match in search_results:
        top_photos_attachments = get_top_3_photos(vk_bot, match['id'])
        success = send_match_info(vk_bot, user_id, match, top_photos_attachments)
        if not success:
            vk_bot.messages.send(
                user_id=user_id,
                message="Не удалось отправить информацию о профиле.",
                random_id=0
            )
        time.sleep(1)

def send_next_button(vk, user_id):
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("Далее", color=VkKeyboardColor.SECONDARY)
    keyboard.add_button('Закончить', color=VkKeyboardColor.NEGATIVE)

    vk.messages.send(
        user_id=user_id,
        message="Нажмите далее для перехода к следующему профилю.",
        random_id=get_random_id(),
        keyboard=keyboard.get_keyboard()
    )
def main():
    vk_session_bot = vk_api.VkApi(token=TOKEN)
    longpoll = VkBotLongPoll(vk_session_bot, GROUP_ID)
    vk_bot = vk_session_bot.get_api()

    try:
        vk_session_user = vk_api.VkApi(login=USER_LOGIN, password=USER_PASSWORD, app_id=APP_ID, scope='photos', captcha_handler=captcha_handler)

        vk_session_user.auth()
    except vk_api.AuthError as error_msg:
        print(error_msg)
        return

    vk_user = vk_session_user.get_api()

    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW and event.from_user:
            user_id = event.obj.message['from_id']
            text = event.obj.message['text'].lower()

            if text == "начать поиск":
                user_info = get_user_info(vk_bot, user_id)
                if not enough_info(user_info):
                    vk_bot.messages.send(
                        user_id=user_id,
                        message="Мне нужно больше информации о вас. Пожалуйста, заполните свой профиль.",
                        keyboard=create_next_keyboard(),
                        random_id=0
                    )
                else:
                    matches = search_for_matches(vk_user, user_info, user_id)
                    if not matches:
                        matches = []
                        for offset in range(0, 100, 10):
                            matches += search_for_matches(vk_user, user_info, offset=offset)
                    current_match_index = 0
                    show_next_profile = True

                    while show_next_profile:
                        if matches and current_match_index < len(matches):
                            add_shown_user(matches[current_match_index]['id'])
                            top_photos_attachments = get_top_3_photos(vk_user, matches[current_match_index]['id'])
                            success = send_match_info(vk_bot, user_id, matches[current_match_index],
                                                      top_photos_attachments)
                            if success:
                                send_next_button(vk_bot, user_id)
                            else:
                                vk_bot.messages.send(
                                    user_id=user_id,
                                    message="Не удалось отправить информацию о профиле.",
                                    keyboard=create_keyboard(),
                                    random_id=0
                                )
                        else:
                            vk_bot.messages.send(
                                user_id=user_id,
                                message="Это был последний профиль в списке.",
                                keyboard=create_keyboard(),
                                random_id=0
                            )
                            show_next_profile = False

                        for inner_event in longpoll.listen():
                            if inner_event.type == VkBotEventType.MESSAGE_NEW and inner_event.from_user:
                                inner_user_id = inner_event.obj.message['from_id']
                                inner_text = inner_event.obj.message['text'].lower()

                                if inner_text == "далее":
                                    current_match_index += 1
                                    break
                                elif inner_text == "начать поиск" or inner_text == "закончить":
                                    show_next_profile = False
                                    vk_bot.messages.send(
                                        user_id=user_id,
                                        message="Привет, я вкбот",
                                        keyboard=create_keyboard(),
                                        random_id=0
                                    )
                                    break

                                else:

                                    if inner_text == "информация обо мне":
                                        user_info = get_user_info(vk_bot, user_id)
                                        user_text = format_user_info(user_info)
                                        vk_bot.messages.send(
                                            user_id=user_id,
                                            message=user_text,
                                            keyboard=create_keyboard(),
                                            random_id=0
                                        )
                                        break

                                    elif inner_text.lower() == "привет":
                                        vk_bot.messages.send(
                                            user_id=user_id,
                                            message="Привет, я вкбот",
                                            keyboard=create_keyboard(),
                                            random_id=0
                                        )
                                        break

                                    else:
                                        vk_bot.messages.send(
                                            user_id=user_id,
                                            message="Не понимаю вашей команды. Вот список того, что я умею.",
                                            keyboard=create_keyboard(),
                                            random_id=0
                                        )
                                        break

                                    break

            elif text == "информация обо мне":
                user_info = get_user_info(vk_bot, user_id)
                user_text = format_user_info(user_info)
                vk_bot.messages.send(
                    user_id=user_id,
                    message=user_text,
                    keyboard=create_keyboard(),
                    random_id=0
                )

            elif text.lower() == "привет":
                vk_bot.messages.send(
                    user_id=user_id,
                    message="Привет, я вкбот",
                    keyboard=create_keyboard(),
                    random_id=0
                )
            else:
                vk_bot.messages.send(
                    user_id=user_id,
                    message="Не понимаю вашей команды. Вот список того, что я умею.",
                    keyboard=create_keyboard(),
                    random_id=0
                )


if __name__ == "__main__":
    create_database()
    main()
