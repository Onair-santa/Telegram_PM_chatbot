import os
import logging
import json
import asyncio

from pyrogram import Client, filters
from presets import Presets

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logging.getLogger("pyrogram").setLevel(logging.WARNING)

if bool(os.environ.get("ENV", False)):
    from sample_config import Config
else:
    from config import Config

# Создание экземпляра бота
bot = Client(
    "pmchat",
    bot_token=Config.TG_BOT_TOKEN,
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
)


async def is_banned(user_id):
    try:
        with open("ban.txt", "r") as f:
            for line in f:
                if line.strip():
                    if int(line.strip()) == user_id:
                        return True
    except FileNotFoundError:
        pass  # Файл ban.txt не существует, значит все пользователи разрешены

    return False


async def add_user_to_json(user_id):
    """
    Добавляет уникального пользователя в файл users.json
    """
    try:
        with open("users.json", "r") as f:
            user_list = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        user_list = []

    if user_id not in user_list:
        user_list.append(user_id)
        with open("users.json", "w") as f:
            json.dump(user_list, f)

@bot.on_message(filters.private & filters.command(['start']))
async def help_me(bot, message):
    if await is_banned(message.from_user.id):
        return
    elif message.from_user.id == Config.ADMIN:
        return

    # Добавляем пользователя в базу данных
    await add_user_to_json(message.from_user.id)

    info = await bot.get_users(user_ids=message.from_user.id)
    await bot.send_message(
        chat_id=message.chat.id,
        text=Presets.WELCOME_TEXT.format(message.from_user.mention, info.first_name),
        disable_web_page_preview=True
    )

    await bot.send_message(
        chat_id=Config.ADMIN,
        text=Presets.USER_DETAILS.format(
            info.first_name,
            info.last_name,
            info.id, info.username
        )
    )

# Новый обработчик для подсчета пользователей
@bot.on_message(filters.private & filters.command(['infouser']) & filters.user(Config.ADMIN))
async def user_count_command(bot, message):
    try:
        with open("users.json", "r") as f:
            user_list = json.load(f)
        await message.reply_text(f"Users: **{len(user_list)}**")
    except FileNotFoundError:
        await message.reply_text("Файл с пользователями не найден. Возможно, еще никто не писал боту.")
    except json.JSONDecodeError:
        await message.reply_text("Ошибка чтения файла users.json. Возможно, он поврежден.")


async def ban_user(user_id):
    try:
        with open("ban.txt", "a") as f:
            f.write(str(user_id) + "\n")
        return True
    except Exception as e:
        print(f"Error banning user {user_id}: {e}")
        return False

async def unban_user(user_id):
    try:
        with open("ban.txt", "r") as f:
            lines = f.readlines()
        with open("ban.txt", "w") as f:
            for line in lines:
                if line.strip() != str(user_id):
                    f.write(line)
        return True
    except Exception as e:
        print(f"Error unbanning user {user_id}: {e}")
        return False


@bot.on_message(filters.user(Config.ADMIN) & filters.reply & filters.command(['ban', 'unban', 'info']))
async def handle_admin_commands(bot, message):
    user_id = None
    replied_message = message.reply_to_message

    if replied_message.text:
        try:
            user_id = int(replied_message.text.split()[2])
        except (IndexError, ValueError):
            pass
    
    if not user_id and replied_message.caption:
        try:
            user_id = int(replied_message.caption.split()[2])
        except (IndexError, ValueError):
            pass

    if not user_id and replied_message.forward_from:
        user_id = replied_message.forward_from.id

    if not user_id:
        await message.reply_text("Не удалось найти ID пользователя. Пожалуйста, отвечайте на пересланное сообщение от пользователя.")
        return

    if user_id == Config.ADMIN:
        await message.reply_text("Невозможно выполнить эту команду в отношении самого себя.")
        return
        
    if message.text.startswith('/info'):
        try:
            info = await bot.get_users(user_id)
            await message.reply_text(
                Presets.USER_DETAILS.format(
                    info.first_name,
                    info.last_name,
                    info.id,
                    info.username
                )
            )
        except Exception as e:
            await message.reply_text(f"Не удалось получить информацию о пользователе: {e}")

    elif message.text.startswith('/ban'):
        if await is_banned(user_id):
            await message.reply_text(f"Пользователь с ID {user_id} уже забанен.")
            return
        
        if await ban_user(user_id):
            await message.reply_text(f"Пользователь с ID {user_id} забанен.")
        else:
            await message.reply_text(f"Ошибка при блокировке пользователя с ID {user_id}")

    elif message.text.startswith('/unban'):
        if not await is_banned(user_id):
            await message.reply_text(f"User with ID {user_id} has been banned.")
            return

        if await unban_user(user_id):
            await message.reply_text(f"User with ID {user_id} has been unbanned.")
        else:
            await message.reply_text(f"Ошибка при разблокировке пользователя с ID {user_id}")


@bot.on_message(filters.private & filters.text & ~filters.user(Config.ADMIN))
async def pm_text(bot, message):
    if await is_banned(message.from_user.id):
        return
    
    # Добавляем пользователя в базу данных
    await add_user_to_json(message.from_user.id)

    info = await bot.get_users(user_ids=message.from_user.id)
    reference_id = int(message.chat.id)
    await bot.send_message(
        chat_id=Config.ADMIN,
        text=Presets.PM_TXT_ATT.format(reference_id, info.first_name, info.username, message.text)
    )

@bot.on_message(filters.private & filters.media & ~filters.user(Config.ADMIN))
async def pm_media(bot, message):
    if await is_banned(message.from_user.id):
        return
    
    # Добавляем пользователя в базу данных
    await add_user_to_json(message.from_user.id)

    info = await bot.get_users(user_ids=message.from_user.id)
    reference_id = int(message.chat.id)
    await bot.copy_message(
        chat_id=Config.ADMIN,
        from_chat_id=message.chat.id,
        message_id=message.id,
        caption=Presets.PM_MED_ATT.format(reference_id, info.first_name, info.username)
    )

@bot.on_message(filters.user(Config.ADMIN) & filters.text & filters.reply)
async def reply_text(bot, message):
    reference_id = True
    if message.reply_to_message is not None:
        file = message.reply_to_message
        try:
            reference_id = file.text.split()[2]
        except Exception:
            pass
        try:
            reference_id = file.caption.split()[2]
        except Exception:
            pass
        await bot.send_message(
            text=message.text,
            chat_id=int(reference_id)
        )

@bot.on_message(filters.user(Config.ADMIN) & filters.media & filters.reply)
async def replay_media(bot, message):
    reference_id = True
    if message.reply_to_message is not None:
        file = message.reply_to_message
        try:
            reference_id = file.text.split()[2]
        except Exception:
            pass
        try:
            reference_id = file.caption.split()[2]
        except Exception:
            pass
        await bot.copy_message(
            chat_id=int(reference_id),
            from_chat_id=message.chat.id,
            message_id=message.id
        )

@bot.on_message(filters.user(Config.ADMIN) & filters.sticker & filters.reply)
async def replay_media(bot, message):
    reference_id = True
    if message.reply_to_message is not None:
        file = message.reply_to_message
        try:
            reference_id = file.text.split()[2]
        except Exception:
            pass
        try:
            reference_id = file.caption.split()[2]
        except Exception:
            pass
        await bot.copy_message(
            chat_id=int(reference_id),
            from_chat_id=message.chat.id,
            message_id=message.id
        )


bot.run()