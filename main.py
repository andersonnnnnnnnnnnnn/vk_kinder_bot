from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api_utils import *
from database_utils import *
from interface_utils import *

TOKEN = "vk1.a.t2m2uvRInlGHKRERKsFonZ2Af2nhRDxIvlhp6AO9NqVx1lVx7Y3EIjzn93k4T54ctiWQJx9RtEYzAYasC9PHBl3nnIYAc-1uCeivJvVP6xemgDulUOapNtaeneE4irgpga0mDpbD3feZi-S7LL-ca0TO7r0SVQp4A2o2xQnBcZs5e267gfOzJS4ytxQmVn8fgqp58Gfb0vjBlkYdpQE5aQ"
GROUP_ID = 220038781
APP_ID = '51622190'
USER_LOGIN = '89859593227'
USER_PASSWORD = 'gaueish238_Sj#'

def captcha_handler(captcha):
    url = captcha.get_url()
    print(f"Откройте ссылку и введите код с изображения: {url}")
    captcha_key = input("Введите код с капчи: ")
    return captcha.try_again(captcha_key)

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