# импортируем библиотеки
from flask import Flask, request, jsonify
import logging

# библиотека, которая нам понадобится для работы с JSON
import json

# создаем приложение
# мы передаем __name__, в нем содержится информация, в каком модуле мы находимся.
# В данном случае там содержится '__main__', так как мы обращаемся к переменной из запущенного модуля.
# если бы такое обращение, например, произошло внутри модуля logging, то мы бы получили 'logging'
app = Flask(__name__)

# Устанавливаем уровень логирования
logging.basicConfig(level=logging.INFO)

# Создадим словарь, чтобы для каждой сессии общения с навыком хранились подсказки, которые видел пользователь.
# Это поможет нам немного разнообразить подсказки ответов (buttons в JSON ответа).
# Когда новый пользователь напишет нашему навыку, то мы сохраним в этот словарь запись формата
# sessionStorage[user_id] = { 'suggests': ["Не хочу.", "Не буду.", "Отстань!" ] }
# Такая запись говорит, что мы показали пользователю эти три подсказки. Когда он откажется купить слона,
# то мы уберем одну подсказку. Как будто что-то меняется :)
sessionStorage = {}


@app.route('/')
def empty():
    return 'empty'


@app.route('/post', methods=['POST'])
# Функция получает тело запроса и возвращает ответ.
# Внутри функции доступен request.json - это JSON, который отправила нам Алиса в запросе POST
def main():
    logging.info('Request: %r', request.json)

    # Начинаем формировать ответ, согласно документации
    # мы собираем словарь, который потом при помощи библиотеки json преобразуем в JSON и отдадим Алисе
    response = {
        'session': request.json['session'],
        'version': request.json['version'],
        'response': {
            'end_session': False
        }
    }

    # Отправляем request.json и response в функцию handle_dialog. Она сформирует оставшиеся поля JSON, которые отвечают
    # непосредственно за ведение диалога
    handle_dialog(request.json, response)

    logging.info('Response: %r', request.json)

    # Преобразовываем в JSON и возвращаем
    return jsonify(response)


def handle_dialog(req, res):
    user_id = req['session']['user_id']

    if req['session']['new']:
        # Это новый пользователь.
        # Инициализируем сессию и поприветствуем его.
        # Запишем подсказки, которые мы ему покажем в первый раз

        sessionStorage[user_id] = {
            'suggests': [
                "Не хочу.",
                "Не буду.",
                "Отстань!",
            ],
            'current_animal': 'слона'
        }
        # Заполняем текст ответа
        res['response']['text'] = 'Привет! Купи слона!'
        # Получим подсказки
        res['response']['buttons'] = get_suggests(user_id)
        return

    current_animal = sessionStorage[user_id]["current_animal"]

    user_text = req['request']['original_utterance'].lower()

    agree_keywords = ['ладно', 'куплю', 'покупаю', 'хорошо']

    is_agree = any(keyword in user_text for keyword in agree_keywords)
    if is_agree:
        if current_animal == 'слона':
            sessionStorage[user_id]['current_animal'] = 'кролика'
            res['response']['text'] = ('Отлично! Слон ваш. '
                                       'А теперь купи кролика!')
            res['response']['buttons'] = get_suggests(user_id)
        else:
            sessionStorage[user_id]['current_animal'] = 'слона'
            res['response']['text'] = ('Замечательно! Кролик ваш. '
                                       'А теперь снова купи слона!')
            res['response']['buttons'] = get_suggests(user_id)
        return

    # Если нет, то убеждаем его купить слона!
    res['response']['text'] = 'Все говорят "%s", а ты купи %s!' % (
        req['request']['original_utterance'],
        current_animal
    )
    res['response']['buttons'] = get_suggests(user_id)


# Функция возвращает две подсказки для ответа.
def get_suggests(user_id):
    session = sessionStorage[user_id]

    # Выбираем две первые подсказки из массива.
    suggests = [
        {'title': suggest, 'hide': True}
        for suggest in session['suggests'][:2]
    ]

    # Убираем первую подсказку, чтобы подсказки менялись каждый раз.
    session['suggests'] = session['suggests'][1:]
    sessionStorage[user_id] = session

    # Если осталась только одна подсказка, предлагаем подсказку
    # со ссылкой на Яндекс.Маркет.
    if len(suggests) < 2:
        suggests.append({
            "title": "Ладно",
            "url": "https://market.yandex.ru/search?text=слон",
            "hide": True
        })

    return suggests


if __name__ == '__main__':
    app.run()
