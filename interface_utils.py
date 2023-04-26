from datetime import datetime
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

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

def create_keyboard():
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button('Поиск людей группы', color=VkKeyboardColor.POSITIVE)
    keyboard.add_line()
    keyboard.add_button('Информация обо мне', color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button('Начать поиск', color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()

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

def calculate_age_range(bdate):
    age = calculate_age(bdate)
    if age == 'Не указан':
        return None, None
    age_from = age - 5 if age > 5 else 1
    age_to = age + 5
    return age_from, age_to

def get_user_info(vk, user_id):
    user_fields = 'city,bdate,sex,relation'
    user_info = vk.users.get(user_id=user_id, fields=user_fields)
    return user_info[0]