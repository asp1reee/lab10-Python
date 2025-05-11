import requests
import json
import random
import pyttsx3
import pyaudio
import vosk
import os
from PIL import Image
import io
import webbrowser

VOSK_MODEL_PATH = "vosk-model-small-ru-0.22"
API_BASE_URL = "https://rickandmortyapi.com/api/character/"
MAX_CHARACTER_ID = 826

current_character_data = None
engine = None


def initialize_tts():
    global engine
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    russian_voice_id = None
    for voice in voices:
        if ("russian" in voice.name.lower() or
                "ru-ru" in voice.id.lower() or
                "aleksandr" in voice.name.lower() or
                "irina" in voice.name.lower()):
            russian_voice_id = voice.id
            break
    if russian_voice_id:
        print(f"Using Russian voice: {russian_voice_id}")
        engine.setProperty('voice', russian_voice_id)
    else:
        print("Russian voice not found, using default.")
    engine.setProperty('rate', 150)


def speak(text):
    print(f"Ассистент: {text}")
    if engine:
        engine.say(text)
        engine.runAndWait()
    else:
        print("TTS engine not initialized.")


def listen():
    if not os.path.exists(VOSK_MODEL_PATH):
        speak(
            f"Модель распознавания речи не найдена по пути "
            f"{VOSK_MODEL_PATH}. Пожалуйста, скачайте и распакуйте ее."
        )
        return None

    model = vosk.Model(VOSK_MODEL_PATH)
    recognizer = vosk.KaldiRecognizer(model, 16000)

    pa = pyaudio.PyAudio()
    stream = pa.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=16000,
        input=True,
        frames_per_buffer=8192
    )

    speak("Слушаю вашу команду...")
    print("Listening...")

    try:
        while True:
            data = stream.read(4096, exception_on_overflow=False)
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                command_text = result.get('text', '').lower()
                if command_text:
                    print(f"Распознано: {command_text}")
                    return command_text
    except KeyboardInterrupt:
        print("Распознавание прервано.")
        return None
    except Exception as e:
        print(f"Ошибка во время распознавания: {e}")
        return None
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()


def get_character_data(character_id=None):
    global current_character_data
    try:
        if character_id:
            url = f"{API_BASE_URL}{character_id}"
        else:
            character_id = random.randint(1, MAX_CHARACTER_ID)
            url = f"{API_BASE_URL}{character_id}"

        response = requests.get(url)
        response.raise_for_status()
        current_character_data = response.json()
        return current_character_data
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            speak(f"Персонаж с ID {character_id} не найден.")
        else:
            speak(
                f"Ошибка API: {e.response.status_code}. "
                f"Не удалось получить данные о персонаже."
            )
        current_character_data = None
        return None
    except requests.exceptions.RequestException as e:
        speak(f"Ошибка сети: {e}. Не удалось подключиться к API.")
        current_character_data = None
        return None


def handle_random_character():
    speak("Ищу случайного персонажа...")
    data = get_character_data()
    if data:
        speak(f"Найден персонаж: {data['name']}.")
    else:
        speak("Не удалось получить данные о случайном персонаже.")


def handle_specific_character(character_id_str):
    try:
        character_id = int(character_id_str)
        if 1 <= character_id <= MAX_CHARACTER_ID:
            speak(f"Загружаю данные о персонаже с номером {character_id}...")
            data = get_character_data(character_id)
            if data:
                speak(f"Персонаж {data['name']} загружен.")
        else:
            speak(
                f"Неверный номер персонажа. Пожалуйста, укажите номер "
                f"от 1 до {MAX_CHARACTER_ID}."
            )
    except ValueError:
        speak("Не удалось распознать номер персонажа в команде.")


def handle_save_image():
    if not current_character_data:
        speak(
            "Сначала выберите персонажа командой 'случайный' или "
            "'персонаж номер'."
        )
        return

    image_url = current_character_data.get('image')
    name = current_character_data.get('name', 'unknown_character')
    if not image_url:
        speak("У этого персонажа нет изображения.")
        return

    try:
        response = requests.get(image_url, stream=True)
        response.raise_for_status()

        if not os.path.exists("images"):
            os.makedirs("images")

        safe_name = "".join(
            c if c.isalnum() or c in (' ', '_') else '_' for c in name
        ).rstrip()
        filename = os.path.join(
            "images", f"{safe_name.replace(' ', '_')}.png"
        )

        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        speak(f"Изображение персонажа {name} сохранено как {filename}.")
    except requests.exceptions.RequestException as e:
        speak(f"Ошибка при скачивании изображения: {e}")
    except IOError as e:
        speak(f"Ошибка при сохранении файла: {e}")


def handle_first_episode():
    if not current_character_data:
        speak(
            "Сначала выберите персонажа командой 'случайный' или "
            "'персонаж номер'."
        )
        return

    episode_urls = current_character_data.get('episode')
    if not episode_urls:
        speak(
            f"Нет информации об эпизодах для персонажа "
            f"{current_character_data['name']}."
        )
        return

    first_episode_url = episode_urls[0]
    try:
        response = requests.get(first_episode_url)
        response.raise_for_status()
        episode_data = response.json()
        episode_name = episode_data.get('name', 'Неизвестный эпизод')
        episode_code = episode_data.get('episode', '')
        speak(
            f"Персонаж {current_character_data['name']} впервые появился "
            f"в эпизоде {episode_code}: {episode_name}."
        )
    except requests.exceptions.RequestException as e:
        speak(f"Ошибка при получении информации об эпизоде: {e}")


def handle_show_image():
    if not current_character_data:
        speak(
            "Сначала выберите персонажа командой 'случайный' или "
            "'персонаж номер'."
        )
        return

    image_url = current_character_data.get('image')
    name = current_character_data.get('name', 'персонаж')
    if not image_url:
        speak(f"У персонажа {name} нет изображения.")
        return

    speak(f"Пытаюсь показать изображение персонажа {name}.")
    try:
        webbrowser.open(image_url)
        speak("Изображение должно было открыться.")
    except requests.exceptions.RequestException as e:
        speak(f"Ошибка при загрузке изображения для показа: {e}")
    except Exception as e:
        speak(
            f"Не удалось показать изображение: {e}. "
            f"Попробуйте команду 'сохранить'."
        )


def handle_image_resolution():
    if not current_character_data:
        speak(
            "Сначала выберите персонажа командой 'случайный' или "
            "'персонаж номер'."
        )
        return

    image_url = current_character_data.get('image')
    name = current_character_data.get('name', 'персонаж')
    if not image_url:
        speak(
            f"У персонажа {name} нет изображения для "
            f"определения разрешения."
        )
        return

    speak(f"Определяю разрешение изображения для {name}.")
    try:
        response = requests.get(image_url)
        response.raise_for_status()
        img_bytes = response.content
        image = Image.open(io.BytesIO(img_bytes))
        width, height = image.size
        speak(f"Разрешение изображения: {width} на {height} пикселей.")
    except requests.exceptions.RequestException as e:
        speak(
            f"Ошибка при загрузке изображения для "
            f"определения разрешения: {e}"
        )
    except Exception as e:
        speak(f"Не удалось определить разрешение: {e}")


def extract_number_from_command(command_text):
    words = command_text.split()
    for word in words:
        if word.isdigit():
            return word
    if "сто восемь" in command_text:
        return "108"
    return None


def main():
    global current_character_data
    initialize_tts()

    speak("Загружаю данные для персонажа номер 108.")
    get_character_data(108)
    if current_character_data:
        speak(
            f"Персонаж {current_character_data['name']} загружен. "
            f"Готов к командам."
        )
    else:
        speak(
            "Не удалось загрузить данные для персонажа 108. "
            "Ассистент готов к другим командам."
        )

    speak(
        "Голосовой ассистент Рик и Морти активирован. "
        "Какие будут указания?"
    )

    active = True
    while active:
        command = listen()

        if command:
            if "случайный" in command:
                handle_random_character()
            elif "сохранить" in command or "сохрани" in command:
                handle_save_image()
            elif "эпизод" in command or "первый эпизод" in command:
                handle_first_episode()
            elif "показать" in command or "покажи" in command:
                handle_show_image()
            elif ("разрешение" in command or
                  "какое разрешение" in command):
                handle_image_resolution()
            elif ("персонаж номер" in command or
                  "загрузи персонажа" in command or
                  "выбери персонажа" in command):
                number_str = extract_number_from_command(command)
                if number_str:
                    handle_specific_character(number_str)
                else:
                    speak(
                        "Не удалось распознать номер персонажа в команде. "
                        "Попробуйте 'персонаж номер СТО ВОСЕМЬ' или "
                        "'персонаж номер 108'."
                    )
            elif "стоп" in command or "выход" in command or "пока" in command:
                speak(
                    "Завершаю работу. До новых встреч во вселенной "
                    "Рика и Морти!"
                )
                active = False
            else:
                speak(
                    "Команда не распознана. Попробуйте: случайный, "
                    "сохранить, эпизод, показать, разрешение, "
                    "персонаж номер [число], или стоп."
                )
        else:
            pass


if __name__ == "__main__":
    if not os.path.exists(VOSK_MODEL_PATH):
        print(f"ERROR: Vosk model not found at '{VOSK_MODEL_PATH}'")
        print(
            "Please download a Vosk model (e.g., vosk-model-small-ru-0.22)"
        )
        print("from https://alphacephei.com/vosk/models and extract it.")
        print(
            f"The script expects it to be in a folder named "
            f"'{os.path.basename(VOSK_MODEL_PATH)}' "
            f"relative to the script, or provide the full path."
        )
    else:
        main()