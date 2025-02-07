import re
import json
import logging
import requests
from aiogram import Bot, Dispatcher
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import CommandStart
from environs import Env
from aiogram.types import Message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

env = Env()
env.read_env()
BOT_TOKEN = env('BOT_TOKEN')
API_TOKEN = env('API_TOKEN')
url = 'https://api.imeicheck.net/v1/checks'

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
WHITE_LIST = []

ALWAYS_SUCCESS = 12  # Всегда успешные результаты
TEN_PERCENT_FAILURE = 13  # 10% неуспешного результата
SINGLE_FAILURE = 14  # только один неуспешный результат
MIXED_RESULTS = 15  # 50% успеха 25% неудач 25% провала


class FSMState(StatesGroup):
    search_imei = State()


def valid_imei(imei):
    if re.fullmatch(r'^\d{15}$', imei):
        return imei
    return None


@dp.message(CommandStart())
async def start(message: Message, state):
    user_id = message.from_user.id
    print(user_id)
    if user_id not in WHITE_LIST:
        await message.answer('Вам нет доступа')
        logger.warning(f"Вход пытался осуществить пользователь {user_id}")
        return
    await message.answer('Доступ получен.\nВведите IMEI для проверки:')
    logger.info(f"Пользователь c {user_id} получил доступ.")
    await state.set_state(FSMState.search_imei)


@dp.message(FSMState.search_imei)
async def search_imei(message: Message):
    user_imei = message.text
    if not valid_imei(user_imei):
        await message.answer("Неверный формат IMEI. Пожалуйста, введите 15-значный IMEI.")
        logger.warning(f"Неверный формат IMEI {user_imei}")
        return
    payload = json.dumps({
        "deviceId": user_imei,
        "serviceId": ALWAYS_SUCCESS
    })
    headers = {
        'Authorization': 'Bearer ' + API_TOKEN,
        'Accept-Language': 'en',
        'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    json_response = json.loads(response.text)
    logger.info(response.status_code)
    if response.status_code == 201:
        description = (
            f"Модель: {json_response.get('properties', {}).get('deviceName', 'Неизвестно')}\n"
            f"Серийный номер: {json_response.get('properties', {}).get('serial', 'Неизвестно')}\n"
            f"Статус гарантии: {json_response.get('properties', {}).get('warrantyStatus', 'Неизвестно')}"
        )
        await message.answer(description)
    else:
        await message.answer('Нет ответа от сервера')

    logger.info(f"Запрос IMEI {user_imei} успешен.")
    await message.answer('Повторите запрос')
    await message.answer("Введите следующий IMEI для проверки:")


if __name__ == '__main__':
    logger.info("Бот запущен.")
    dp.run_polling(bot)
