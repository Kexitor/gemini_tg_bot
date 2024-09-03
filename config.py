messages_json_path = "messages/"

messages_json_file_path = ""

max_messages_file_size = 15

bot_refresh_timeout = 15

max_messages_count = 30

greeting_message = "Hi, you are talking to Gemini. Ask your first question. Write /help to get possible commands."

possible_commands = '''
/help - get possible commands
/start - get greeting message
/change_ai_model - changes AI model
'''

wait_message = "Got your question, wait for my response."

logs_path = "logs/"

confusion_message = "Send me text message (not file) or server couldn't send back answer."

messages_limit_warning = f"You are close to messages limit {max_messages_count}"

possible_ai_models_list = ["gemini-1.5-flash", "gemini-1.5-pro"]