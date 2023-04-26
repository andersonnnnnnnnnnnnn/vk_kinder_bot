import vk_api
import time
from vk_api.utils import get_random_id
from database_utils import *
from interface_utils import *

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

def get_top_3_photos(vk, user_id):
    try:
        photos = vk.photos.get(owner_id=user_id, album_id='profile', extended=1)
    except vk_api.exceptions.ApiError as e:
        if e.code == 30:  # Profile is private
            return []
        else:
            raise e

    top_photos = sorted(photos['items'], key=lambda x: x['likes']['count'], reverse=True)[:3]

    attachments = []
    for photo in top_photos:
        attachments.append(f"photo{photo['owner_id']}_{photo['id']}")

    return attachments

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