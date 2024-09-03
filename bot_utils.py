import pathlib
import textwrap
import asyncio
import google.generativeai as genai
from IPython.display import display
from IPython.display import Markdown
import asyncio
import logging
import os
from datetime import datetime
import re
import config
import creds
import time


def create_directory(directory_path):
  """
  Creates directory

  :param directory_path: str path to directory
  """
  if not os.path.exists(directory_path) or os.path.isfile(directory_path):
      os.makedirs(directory_path)


def get_time_difference_from_now_in_minutes(last_message_time_str):
  """
  Difference in minutes for last message time

  :param last_message_time_str: str(datetime.utcnow()
  :return: integer - minutes difference
  """
  dt = datetime.strptime(last_message_time_str, '%Y-%m-%d %H:%M:%S.%f')
  dt2 = datetime.utcnow()
  time_diff = dt2 - dt
  minutes_diff = int(time_diff.total_seconds() / 60)

  return minutes_diff


def get_messages_count_in_dialog(messages):
  """
  Messages count in dialog

  :param messages: list of messages
  :return: integer - number of messages
  """
  return len(messages)


# def to_markdown(text):
#   text = text.replace('•', '  *')
#   return Markdown(textwrap.indent(text, '> ', predicate=lambda _: True))


def init_gemini_chat(ai_model):
  """
  Initializes gemini chat

  :param ai_model: string - AI model
  :return: initialized chat
  """
  genai.configure(api_key=creds.gemini_api_token)
  model = genai.GenerativeModel(ai_model)
  chat = model.start_chat(history=[])

  return chat

async def chat_request(chat_entity, text):
  """
  Request to Gemini API

  :param chat_entity: initialized chat
  :param text: string - chat message
  :return: string - response text
  """
  response = await chat_entity.send_message_async(text)
  # to_markdown(response.text)

  return response.text


def get_file_path():
  """
  Forms new file path using current date and time

  :return: string - path to new generated messages file
  """
  return os.path.join(config.messages_json_path, f'messages_{time.strftime("%Y-%m-%d_%H-%M-%S")}.json')


