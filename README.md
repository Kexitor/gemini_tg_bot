# Human pose estimation and classification using Mediapipe

Simple Telegram bot with Gemini API. There is dialog refresher enabled.

## Used lib versions:

Python version 3.10.11

Required libs can be installed:

```
pip install -r requirements.txt
```

## BEFORE LAUNCH:

Fill file `creds.py` with your Gemini API token and Telegram bot token.


## How to use:

Example of usage:

```commandline
python tg_chat_bot.py
```

## Extra:

Bot records logs in directory `./logs/` and user messages in `./messages/`.

If any problem with Gemini API libs, do next command:

```commandline
pip install -q -U google-generativeai 
```
