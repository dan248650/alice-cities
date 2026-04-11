from flask import Flask, request, jsonify
import logging
import random

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

cities = {
    'москва': {
        'images': ['1656841/4ba1ee6cf5cee2f5c303', '213044/7df73ae4cc715175059e'],
        'country': 'россия'
    },
    'нью-йорк': {
        'images': ['1652229/728d5c86707054d4745f', '1030494/aca7ed7acefde2606bdc'],
        'country': 'сша'
    },
    'париж': {
        'images': ["1652229/f77136c2364eb90a3ea8", '1540737/15a652779c8a198a069f'],
        'country': 'франция'
    }
}

sessionStorage = {}


@app.route('/')
def empty():
    return "empty"


@app.route('/post', methods=['POST'])
def main():
    logging.info('Request: %r', request.json)
    response = {
        'session': request.json['session'],
        'version': request.json['version'],
        'response': {
            'end_session': False
        }
    }
    handle_dialog(response, request.json)
    logging.info('Response: %r', response)
    return jsonify(response)


def handle_dialog(res, req):
    user_id = req['session']['user_id']

    if user_id not in sessionStorage:
        sessionStorage[user_id] = {
            'first_name': None,
            'game_started': False,
            'guessed_cities': [],
            'awaiting_country': False,
            'last_city': None
        }

    if req['session']['new']:
        res['response']['text'] = 'Привет! Назови своё имя!'
        sessionStorage[user_id] = {
            'first_name': None,
            'game_started': False,
            'guessed_cities': [],
            'awaiting_country': False,
            'last_city': None
        }
        return

    tokens = get_tokens(req)

    if is_map_button_pressed(req):
        last_city = sessionStorage[user_id].get('last_city', '')
        if last_city:
            map_url = f"https://yandex.ru/maps/?mode=search&text={last_city}"
            res['response']['text'] = 'В какой стране находится этот город?'
            res['response']['buttons'] = [
                {'title': 'Помощь', 'hide': False},
                {
                    'title': 'Посмотреть на карте',
                    'url': map_url,
                    'hide': True,
                    'payload': {}
                }
            ]
        else:
            res['response']['text'] = 'Назови страну, пожалуйста.'
        return

    if 'помощь' in tokens or 'help' in tokens:
        help_text = (
            'Правила игры: я показываю фото города, а ты угадываешь его название. '
            'После неправильной попытки я дам дополнительное фото. '
            'Когда угадаешь город, я спрошу страну этого города. '
            'Для ответа просто назови город или страну. '
            'Чтобы продолжить игру, просто ответь на мой вопрос или назови город.'
        )
        res['response']['text'] = help_text
        res['response']['buttons'] = [{'title': 'Помощь', 'hide': False}]
        return

    first_name = sessionStorage[user_id]['first_name']
    name_address = f"{first_name.title()}, " if first_name else ""

    if sessionStorage[user_id]['awaiting_country']:
        handle_country_question(res, req)
        return

    if sessionStorage[user_id]['first_name'] is None:
        first_name = get_first_name(req)
        if first_name is None:
            res['response']['text'] = 'Не расслышала имя. Повтори, пожалуйста!'
        else:
            sessionStorage[user_id]['first_name'] = first_name
            sessionStorage[user_id]['guessed_cities'] = []
            res['response'][
                'text'] = (f'Приятно познакомиться, {first_name.title()}. '
                           f'Я Алиса. {first_name.title()}, отгадаешь город по фото?')
            res['response']['buttons'] = [
                {'title': 'Да', 'hide': True},
                {'title': 'Нет', 'hide': True},
                {'title': 'Помощь', 'hide': False}
            ]
    else:
        if not sessionStorage[user_id]['game_started']:
            if 'да' in tokens:
                if len(sessionStorage[user_id]['guessed_cities']) == 3:
                    res['response']['text'] = f'{name_address}Ты отгадал все города!'
                    res['response']['end_session'] = True
                else:
                    sessionStorage[user_id]['game_started'] = True
                    sessionStorage[user_id]['attempt'] = 1
                    play_game(res, req)
            elif 'нет' in tokens:
                res['response']['text'] = f'{name_address}Ну и ладно!'
                res['response']['end_session'] = True
            else:
                res['response']['text'] = f'{name_address}Не поняла ответа! Так да или нет?'
                res['response']['buttons'] = [
                    {'title': 'Да', 'hide': True},
                    {'title': 'Нет', 'hide': True},
                    {'title': 'Помощь', 'hide': False}
                ]
        else:
            play_game(res, req)


def is_map_button_pressed(req):
    try:
        command = req['request'].get('command', '').lower()
        original = req['request'].get('original_utterance', '').lower()

        if 'payload' in req['request']:
            payload = req['request']['payload']
            if payload and isinstance(payload, dict):
                return True

        if not command or command in ['посмотреть на карте', 'карта', 'на карте']:
            return True

        return False
    except (KeyError, TypeError):
        return False


def handle_country_question(res, req):
    user_id = req['session']['user_id']
    first_name = sessionStorage[user_id]['first_name']
    name_address = f"{first_name.title()}, " if first_name else ""
    last_city = sessionStorage[user_id]['last_city']
    correct_country = cities[last_city]['country']

    guessed_country = get_country(req)

    if guessed_country == correct_country:
        res['response']['text'] = f'{name_address}Абсолютно верно! Это {correct_country.title()}.'
        sessionStorage[user_id]['awaiting_country'] = False
        sessionStorage[user_id]['game_started'] = False
        sessionStorage[user_id]['guessed_cities'].append(last_city)

        if len(sessionStorage[user_id]['guessed_cities']) == 3:
            res['response']['text'] += f' {name_address}Поздравляю! Ты отгадал все города!'
            res['response']['end_session'] = True
        else:
            res['response']['text'] += f' {name_address}Сыграем ещё?'
            res['response']['buttons'] = [
                {'title': 'Да', 'hide': True},
                {'title': 'Нет', 'hide': True},
                {'title': 'Помощь', 'hide': False}
            ]
    else:
        if guessed_country is None and req['request'].get('command', ''):
            map_url = f"https://yandex.ru/maps/?mode=search&text={last_city}"
            res['response'][
                'text'] = f'{name_address}Я не поняла страну. Назови страну, где находится {last_city.title()}.'
            res['response']['buttons'] = [
                {'title': 'Помощь', 'hide': False},
                {
                    'title': 'Посмотреть на карте',
                    'url': map_url,
                    'hide': True,
                    'payload': {}
                }
            ]
            return

        res['response'][
            'text'] = f'{name_address}Неправильно. Правильная страна: {correct_country.title()}. Сыграем ещё?'
        sessionStorage[user_id]['awaiting_country'] = False
        sessionStorage[user_id]['game_started'] = False
        sessionStorage[user_id]['guessed_cities'].append(last_city)

        if len(sessionStorage[user_id]['guessed_cities']) == 3:
            res['response']['text'] += f' {name_address}Ты отгадал все города!'
            res['response']['end_session'] = True
        else:
            res['response']['buttons'] = [
                {'title': 'Да', 'hide': True},
                {'title': 'Нет', 'hide': True},
                {'title': 'Помощь', 'hide': False}
            ]


def play_game(res, req):
    user_id = req['session']['user_id']
    attempt = sessionStorage[user_id]['attempt']
    first_name = sessionStorage[user_id]['first_name']
    name_address = f"{first_name.title()}, " if first_name else ""

    if attempt == 1:
        city = random.choice(list(cities.keys()))
        while city in sessionStorage[user_id]['guessed_cities']:
            city = random.choice(list(cities.keys()))
        sessionStorage[user_id]['city'] = city
        res['response']['card'] = {}
        res['response']['card']['type'] = 'BigImage'
        res['response']['card']['title'] = f'{name_address}Что это за город?'
        res['response']['card']['image_id'] = cities[city]['images'][attempt - 1]
        res['response']['text'] = f'{name_address}Тогда сыграем!'
    else:
        city = sessionStorage[user_id]['city']
        guessed_city = get_city(req)

        if guessed_city == city:
            sessionStorage[user_id]['last_city'] = city
            sessionStorage[user_id]['awaiting_country'] = True
            sessionStorage[user_id]['game_started'] = False

            map_url = f"https://yandex.ru/maps/?mode=search&text={city}"

            res['response'][
                'text'] = f'{name_address}Правильно! Это {city.title()}. А теперь скажи, в какой стране находится этот город?'
            res['response']['buttons'] = [
                {'title': 'Помощь', 'hide': False},
                {
                    'title': 'Посмотреть на карте',
                    'url': map_url,
                    'hide': True,
                    'payload': {}
                }
            ]
            return
        else:
            if attempt == 3:
                map_url = f"https://yandex.ru/maps/?mode=search&text={city}"
                res['response'][
                    'text'] = f'{name_address}Вы пытались. Это {city.title()}. А теперь скажи, в какой стране находится этот город?'
                sessionStorage[user_id]['game_started'] = False
                sessionStorage[user_id]['last_city'] = city
                sessionStorage[user_id]['awaiting_country'] = True
                res['response']['buttons'] = [
                    {'title': 'Помощь', 'hide': False},
                    {
                        'title': 'Посмотреть на карте',
                        'url': map_url,
                        'hide': True,
                        'payload': {}
                    }
                ]
                return
            else:
                res['response']['card'] = {}
                res['response']['card']['type'] = 'BigImage'
                res['response']['card']['title'] = f'{name_address}Неправильно. Вот тебе дополнительное фото'
                res['response']['card']['image_id'] = cities[city]['images'][attempt - 1]
                res['response']['text'] = f'{name_address}А вот и не угадал!'

    sessionStorage[user_id]['attempt'] += 1
    res['response']['buttons'] = [{'title': 'Помощь', 'hide': False}]


def get_tokens(req):
    try:
        return req['request']['nlu']['tokens']
    except (KeyError, TypeError):
        return []


def get_city(req):
    try:
        for entity in req['request']['nlu']['entities']:
            if entity['type'] == 'YANDEX.GEO':
                city = entity['value'].get('city', None)
                if city:
                    return city.lower()
    except (KeyError, TypeError):
        pass

    tokens = get_tokens(req)
    for token in tokens:
        token_lower = token.lower()
        if token_lower in cities:
            return token_lower

    return None


def get_country(req):
    try:
        for entity in req['request']['nlu']['entities']:
            if entity['type'] == 'YANDEX.GEO':
                country = entity['value'].get('country', None)
                if country:
                    return country.lower()
    except (KeyError, TypeError):
        pass

    tokens = get_tokens(req)
    country_names = ['россия', 'рф', 'российская федерация', 'сша', 'америка',
                     'соединенные штаты', 'соединённые штаты', 'франция']

    for token in tokens:
        token_lower = token.lower()
        if token_lower in country_names:
            if token_lower in ['россия', 'рф', 'российская федерация']:
                return 'россия'
            elif token_lower in ['сша', 'америка', 'соединенные штаты', 'соединённые штаты']:
                return 'сша'
            elif token_lower == 'франция':
                return 'франция'

    return None


def get_first_name(req):
    try:
        for entity in req['request']['nlu']['entities']:
            if entity['type'] == 'YANDEX.FIO':
                first_name = entity['value'].get('first_name', None)
                if first_name:
                    return first_name
    except (KeyError, TypeError):
        pass

    tokens = get_tokens(req)
    if tokens:
        excluded = ['привет', 'здравствуй', 'меня', 'зовут', 'я']
        first_token = tokens[0].lower()
        if first_token not in excluded:
            return tokens[0]
        elif len(tokens) > 1:
            return tokens[1]

    return None


if __name__ == '__main__':
    app.run()
