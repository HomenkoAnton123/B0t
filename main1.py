from telethon import TelegramClient
from telethon.tl.functions.account import UpdateProfileRequest
from datetime import datetime
import asyncio

api_id = 33883754
api_hash = "ef6dc46913bdbb2cde91990bbd6e3479"

client = TelegramClient("session", api_id, api_hash)

last_time = ""

async def main():
    global last_time
    await client.start()

    while True:
        now = datetime.now().strftime("%H:%M")

        # Меняем только если время изменилось
        if now != last_time:
            await client(UpdateProfileRequest(
                first_name=f"meloton {now}"
            ))

            print("Обновлено:", now)
            last_time = now

        # Проверка каждую секунду
        await asyncio.sleep(1)

with client:
    client.loop.run_until_complete(main())