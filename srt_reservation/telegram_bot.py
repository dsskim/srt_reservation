import asyncio

import telegram as tel
from config.telegram_cfg import tele_conf

async def send_message(msg):
    bot = tel.Bot(token=tele_conf['token'])
    chat_id = tele_conf['id']

    await bot.sendMessage(chat_id=chat_id, text=msg)

if __name__ == "__main__":
    asyncio.run(send_message())