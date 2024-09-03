import asyncio
import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Router
from aiogram.types import Message
from aiogram import types
from aiogram.filters import Command
import config
import creds
import json
import os
from aiogram import F
from bot_utils import (create_directory, init_gemini_chat, chat_request, get_time_difference_from_now_in_minutes,
                       get_messages_count_in_dialog, get_file_path)
import aiofiles

router = Router()
user_sessions = {}
file_writer_queue = asyncio.Queue()


def assistant_id_initialized(msg):
    user_id = msg.from_user.id
    try:
        if user_sessions[user_id]["ai_model"] and user_sessions[user_id]["ai_model"] != "":
            return True
    except:
        user_sessions[user_id] = {"last_message": str(datetime.utcnow()),
                                  "chat_entity": init_gemini_chat(config.possible_ai_models_list[0]),
                                  "messages": [],
                                  "ai_model": config.possible_ai_models_list[0]}
        return False


async def write_data_in_json(user_id: str, user_messages: dict, lock: asyncio.Lock):
    """
    Async JSON file writer
    """
    if not config.messages_json_file_path:
        config.messages_json_file_path = get_file_path()
    create_directory(config.messages_json_path)

    try:
        if os.path.isfile(config.messages_json_file_path):
            if os.path.getsize(config.messages_json_file_path) / (1024 ** 2) > config.max_messages_file_size:
                config.messages_json_file_path = get_file_path()
                logging.info(
                    f'Messages file size is more than {str(config.max_messages_file_size)}MB, making new file with name {config.messages_json_file_path}')
    except:
        pass

    async with lock:
        data = {}
        try:
            async with aiofiles.open(config.messages_json_file_path, 'r') as f:
                data = await f.read()
                data = json.loads(data)
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            data = {}

        if user_id in data:
            data[user_id].append(user_messages)
        else:
            data[user_id] = [user_messages]

        async with aiofiles.open(config.messages_json_file_path, 'w') as f:
            await f.write(json.dumps(data, indent=4))


async def queue_message_writer():
    """
    Async queue JSON file writer
    """
    logging.info("queue_message_writer is working")
    json_file_path = get_file_path()
    create_directory(config.messages_json_path)

    while True:
        try:
            if os.path.isfile(json_file_path):
                if os.path.getsize(json_file_path) / (1024 ** 2) > config.max_messages_file_size:
                    json_file_path = get_file_path()
                    logging.info(
                        f'Messages file size is more than {str(config.max_messages_file_size)}MB, making new file with name {json_file_path}')
        except:
            pass

        try:
            user_id, user_messages = await file_writer_queue.get()
            try:
                with open(json_file_path, 'r') as file:
                    data = json.load(file)
            except (FileNotFoundError, json.decoder.JSONDecodeError):
                data = {}

            if user_id in data:
                data[user_id].append(user_messages)
            else:
                data[user_id] = [user_messages]

            with open(json_file_path, 'w') as file:
                json.dump(data, file, indent=4)

            file_writer_queue.task_done()
        except Exception as e:
            logging.error(f"Failed to write user data in JSON with error: {str(e)}")
            await asyncio.sleep(60)

        await asyncio.sleep(60)


async def user_dialogs_refresher():
    """
    Deletes user history when reaching limits
    """
    logging.info("user_dialogs_refresher is working")
    while True:
        if len(user_sessions) > 0:
            keys = list(user_sessions.keys())
            for key in keys:
                if get_time_difference_from_now_in_minutes(user_sessions[key]["last_message"]) >= config.bot_refresh_timeout:
                    # await write_data(str(key), user_sessions[key], asyncio.Lock())
                    await file_writer_queue.put((str(key), user_sessions[key]))
                    del user_sessions[key]
                    logging.info(f"Deleted user with id {key} by time")
                elif get_messages_count_in_dialog(user_sessions[key]["messages"]) > config.max_messages_count:
                    # await write_data(str(key), user_sessions[key], asyncio.Lock())
                    await file_writer_queue.put((str(key), user_sessions[key]))
                    del user_sessions[key]
                    logging.info(f"Deleted user with id {key} by messages count")
                else:
                    pass
        else:
            pass

        await asyncio.sleep(30)


async def get_gemini_response(user_id):
    """
    Provides interaction with Gemini API
    """
    try:
        chat_text = user_sessions[user_id]["messages"]
        chat_entity = user_sessions[user_id]["chat_entity"]
        response = await chat_request(chat_entity, chat_text[-1]["content"])
        user_sessions[user_id]["messages"].append({"role": "assistant", "content": response})
        return response
    except Exception as e:
        logging.error(f"Failed to connect to Gemini with error: {str(e)}")
        return f"Error with Gemini API: {str(e)}"



@router.message(Command("start"))
async def start_handler(msg: Message):
    """
    Initializes user
    """
    user_id = msg.from_user.id
    try:
        if user_sessions[user_id]["last_message"]:
            await file_writer_queue.put((str(user_id), user_sessions[user_id]))
    except:
        pass

    user_sessions[user_id] = {"last_message": str(datetime.utcnow()),
                              "chat_entity": init_gemini_chat(config.possible_ai_models_list[0]),
                              "messages": [],
                              "ai_model": config.possible_ai_models_list[0]}

    await msg.answer(config.greeting_message)



@router.message(Command("help"))
async def help_handler(msg: Message):
    """
    Shows all accessible commands
    """
    await msg.answer(f"Possible commands:\n{config.possible_commands}")


@router.message(Command("change_ai_model"))
async def change_ai_model_handler(msg: Message):
    """
    Changes AI model
    """
    user_id = msg.from_user.id
    assistant_id_initialized(msg)

    buttons_list = []
    # config.bots_dict = await get_all_assistants()
    for model_name in config.possible_ai_models_list:
        button = types.InlineKeyboardButton(text=f"{model_name}", callback_data=f"change_model_{model_name}")
        buttons_list.append([button])
    buttons_list.append([types.InlineKeyboardButton(text=f"Cancel", callback_data=f"change_model_exit")])
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons_list)

    await msg.answer("Choose AI model:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("change_model_"))
async def process_change_ai_model(callback_query: types.CallbackQuery):
    model_name = callback_query.data.split("_")[-1]
    user_id = callback_query.from_user.id
    if model_name == "exit":
        await callback_query.message.edit_text(f"You canceled choosing AI model", reply_markup=None)
        return
    try:
        user_sessions[user_id]['ai_model'] = model_name
        user_sessions[user_id]["chat_entity"] = init_gemini_chat(model_name)
        logging.info(f"User {str(user_id)} selected AI model {model_name} for {user_sessions[user_id]['ai_model']}")
        await callback_query.message.edit_text(f"You chose {model_name} AI model", reply_markup=None)
    except Exception as e:
        await callback_query.message.edit_text(f"Error while trying to change AI model for assistant: {str(e)}", reply_markup=None)
        logging.error(f"Error while trying to change AI model for assistant {str(user_id)}: {str(e)}")


@router.message()
async def message_handler(msg: Message):
    """
    Message handler
    """
    user_id = msg.from_user.id

    try:
        if not msg.text or str(msg.content_type) != 'ContentType.TEXT':
            raise Exception

        try:
            user_sessions[user_id]["messages"].append({"role": "user", "content": msg.text})
            user_sessions[user_id]["last_message"] = str(datetime.utcnow())
        except:
            user_sessions[user_id] = {"last_message": str(datetime.utcnow()),
                                      "chat_entity": init_gemini_chat(config.possible_ai_models_list[0]),
                                      "messages": [],
                                      "ai_model": config.possible_ai_models_list[0]}
            user_sessions[user_id]["messages"].append({"role": "user", "content": msg.text})

        try:
            user_messages_count = get_messages_count_in_dialog(user_sessions[user_id]["messages"])
            if user_messages_count >= config.max_messages_count - 5:
                await msg.answer(
                    f"You spent {user_messages_count}/{config.max_messages_count} messages. " + config.messages_limit_warning,
                    parse_mode="Markdown")
        except Exception as e:
            logging.warning(f"Failed to calculate user {str(user_id)} tokens or messages count: {str(e)}")

        await msg.answer(config.wait_message, parse_mode="Markdown")
        await msg.bot.send_chat_action(user_id, 'typing')
        gemini_response = await get_gemini_response(user_id)

        await msg.answer(gemini_response, parse_mode="Markdown")

        try:
            logging.info(user_sessions)
        except:
            logging.warning("Failed to log user messages")

    except Exception as e:
        # TODO File processing
        logging.info(f"Error while trying to send msg back {str(user_id)}: {str(e)}")
        await msg.answer(config.confusion_message, parse_mode="Markdown")


async def main():
    asyncio.create_task(user_dialogs_refresher())
    asyncio.create_task(queue_message_writer())
    bot = Bot(token=creds.assistant_bot_token)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    create_directory(config.logs_path)

    handler = TimedRotatingFileHandler(config.logs_path + "logs.txt", when="midnight", backupCount=2)
    handler.suffix = "%b-%d-%Y.txt"
    logging.basicConfig(
        level=logging.INFO,
        encoding="utf-8",
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[handler, logging.StreamHandler(sys.stdout)])

    asyncio.run(main())
