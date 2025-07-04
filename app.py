import os
import re
import requests
from flask import Flask, render_template, request
from google import genai  # клиентская библиотека Google GenAI

# Загрузка API-ключей из переменных окружения (если не заданы, используются заданные по умолчанию)
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'AIzaSyBjCMFPAv1QX5ewcb0m08Pjh4Mdn6MV9i8')
SORA_API_KEY   = os.getenv('SORA_API_KEY',   'sk-bCREbtCgwOgFPHxdFd4c7a9910A140438507D1C51401827c')
SORA_URL = "https://api.laozhang.ai/v1/chat/completions"

# Инициализация клиента Gemini (Google GenAI)
genai_client = genai.Client(api_key=GEMINI_API_KEY)

def get_best_prompt(user_input: str) -> str:
    """
    С помощью модели Gemini генерирует подробный английский промпт из пользовательского ввода.
    """
    # Формируем запрос согласно требованиям (текст запроса на русском с инструкцией, далее сам ввод)
    prompt_request = (
        "Напиши очень подробный промпт для Sora, кроме промпта не должно быть лишних слов. "
        "Задача — нарисовать картинку в лучшем виде, не придумывать ничего лишнего, "
        "главная задача — сохранить исходную идею. Ниже запрос пользователя, ответ дай на английском языке:\n"
        f"{user_input}"
    )
    # Отправляем запрос к модели Gemini для генерации текста
    response = genai_client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt_request
    )
    detailed_prompt = response.text.strip()
    return detailed_prompt

def get_image_urls_from_sora(prompt: str):
    """
    Отправляет сгенерированный промпт в Sora API и возвращает список URL-адресов изображений из ответа.
    """
    headers = {
        "Authorization": f"Bearer {SORA_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "sora-image",
        "stream": False,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user",   "content": prompt}
        ],
    }
    # Выполняем POST-запрос к API Sora
    resp = requests.post(SORA_URL, headers=headers, json=payload)
    resp.raise_for_status()  # бросить исключение, если вернулся статус ошибки
    data = resp.json()
    # Извлекаем URL изображений из содержимого ответа (если они есть)
    image_urls = []
    if "choices" in data and data["choices"]:
        content = data["choices"][0]["message"]["content"]
        # Ищем все подстроки формата (http...): URL в круглых скобках
        image_urls = re.findall(r"\((https?://[^\s)]+)\)", content)
    return image_urls

# Инициализируем Flask-приложение
app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Получаем ввод пользователя из формы
        user_input = request.form.get('prompt_text', '')
        if not user_input.strip():
            # Если поле пустое, перезагрузить страницу с сообщением (упрощенно без отдельного сообщения об ошибке)
            return render_template('index.html', prompt_text='', image_url=None)
        # 1. Генерация детального промпта через Gemini
        try:
            best_prompt = get_best_prompt(user_input)
        except Exception as e:
            # Обработка ошибок обращения к Gemini API
            error_msg = f"Ошибка при генерации промпта: {e}"
            return render_template('index.html', prompt_text=user_input, error=error_msg)
        # 2. Генерация изображения через Sora API
        image_url = None
        try:
            image_urls = get_image_urls_from_sora(best_prompt)
            if image_urls:
                # Берем первую ссылку из списка (Sora может вернуть несколько изображений)
                image_url = image_urls[0]
        except Exception as e:
            # Обработка ошибок обращения к Sora API
            error_msg = f"Ошибка при генерации изображения через Sora API: {e}"
            return render_template('index.html', prompt_text=user_input, error=error_msg)
        # Рендерим шаблон с переданными данными: исходный текст, и полученный URL (если есть)
        return render_template('index.html', prompt_text=user_input, image_url=image_url)
    # Метод GET: отображаем начальную страницу с формой ввода
    return render_template('index.html', prompt_text='', image_url=None)

# Запуск приложения на локальном сервере (например, http://127.0.0.1:5000)
if __name__ == '__main__':
    app.run(debug=True)
