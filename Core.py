import telebot
import datetime
import os
import time
import logging
import multiprocessing

# Set up logging
logging.basicConfig(level=logging.INFO)

# Replace with your Telegram bot token
bot = telebot.TeleBot('8018452264:AAEGFJekVzKvP-vnowxCry8zYBWfQCJfSFY')

# Admin user IDs
admin_id = ["6442837812"]

# File to store allowed users and their expiration times
USER_ACCESS_FILE = "user_access.txt"

# Dictionary to store user access information (user_id: expiration_date)
user_access = {}

# Track active attacks
active_attacks = []

# Dictionary to track the last attack time for each user
user_last_attack_time = {}

# Dictionary to store attack limits (user_id: max_attack_duration)
attack_limits = {}

# List to keep track of CPU stress processes
cpu_stress_processes = []

# Ensure the access file exists
if not os.path.exists(USER_ACCESS_FILE):
    open(USER_ACCESS_FILE, "w").close()

# Load user access information from file
def load_user_access():
    try:
        with open(USER_ACCESS_FILE, "r") as file:
            access = {}
            for line in file:
                user_id, expiration = line.strip().split(",")
                access[user_id] = datetime.datetime.fromisoformat(expiration)
            return access
    except FileNotFoundError:
        return {}
    except ValueError as e:
        logging.error(f"Error loading user access file: {e}")
        return {}

# Save user access information to file
def save_user_access():
    temp_file = f"{USER_ACCESS_FILE}.tmp"
    try:
        with open(temp_file, "w") as file:
            for user_id, expiration in user_access.items():
                file.write(f"{user_id},{expiration.isoformat()}\n")
        os.replace(temp_file, USER_ACCESS_FILE)
    except Exception as e:
        logging.error(f"Error saving user access file: {e}")

# Load access information on startup
user_access = load_user_access()

# Function to simulate CPU stress
def stress_cpu():
    while True:
        pass  # Busy-wait to keep the CPU at 100%

# Stop all CPU stress processes
def stop_cpu_stress():
    global cpu_stress_processes
    for process in cpu_stress_processes:
        process.terminate()
    cpu_stress_processes = []

# Command: /start
@bot.message_handler(commands=['start'])
def start_command(message):
    logging.info("Start command received")
    welcome_message = """
    🌟 Welcome to the **Lightning DDoS Bot**! 🌟

    ⚡️ With this bot, you can:
    - Check your subscription status.
    - Simulate powerful attacks responsibly.
    - Manage access and commands efficiently.

    🚀 Use `/help` to see the available commands and get started!

    🛡️ For assistance, contact [@its_darinda](https://t.me/its_darinda).

    **Note:** Unauthorized access is prohibited. Contact an admin if you need access.
    """
    bot.reply_to(message, welcome_message, parse_mode='Markdown')

# Command: /bgmi
@bot.message_handler(commands=['bgmi'])
def handle_bgmi(message):
    logging.info("BGMI command received")
    global active_attacks, cpu_stress_processes
    user_id = str(message.from_user.id)

    # Check if the user is authorized
    if user_id not in user_access or user_access[user_id] < datetime.datetime.now():
        bot.reply_to(message, "❌ You are not authorized to use this bot or your access has expired. Please contact an admin.")
        return

    # Remove completed attacks
    active_attacks = [attack for attack in active_attacks if attack['end_time'] > datetime.datetime.now()]

    # Check for cooldown
    if user_id in user_last_attack_time:
        last_attack_time = user_last_attack_time[user_id]
        time_since_last_attack = (datetime.datetime.now() - last_attack_time).total_seconds()
        if time_since_last_attack < 120:  # 120 seconds cooldown
            remaining_time = 120 - int(time_since_last_attack)
            bot.reply_to(message, f"⚠️ You must wait {remaining_time} more seconds before launching another attack.")
            return

    # Parse command
    command = message.text.split()
    if len(command) != 4 or not command[3].isdigit():
        bot.reply_to(message, "Invalid format! Use: `/bgmi <target> <port> <duration>`", parse_mode='Markdown')
        return

    target, port, duration = command[1], command[2], int(command[3])

    # Validate port
    if not port.isdigit() or not (1 <= int(port) <= 65535):
        bot.reply_to(message, "Invalid port! Please provide a port number between 1 and 65535.")
        return

    # Check attack duration limit
    if user_id in attack_limits and duration > attack_limits[user_id]:
        bot.reply_to(message, f"⚠️ You can only launch attacks up to {attack_limits[user_id]} seconds.")
        return

    # Escape dynamic values
    target = target.replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("]", "\\]").replace("`", "\\`")
    port = port.replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("]", "\\]").replace("`", "\\`")

    # Add attack to active attacks
    attack_end_time = datetime.datetime.now() + datetime.timedelta(seconds=duration)
    active_attacks.append({
        'user_id': user_id,
        'target': target,
        'port': port,
        'end_time': attack_end_time
    })

    user_last_attack_time[user_id] = datetime.datetime.now()

    # Start CPU stress processes
    stop_cpu_stress()  # Ensure no previous stress processes are running
    for _ in range(multiprocessing.cpu_count()):  # Start one process per CPU core
        process = multiprocessing.Process(target=stress_cpu)
        process.start()
        cpu_stress_processes.append(process)

    # Schedule the stop of stress processes
    def stop_stress_after_duration():
        time.sleep(duration)
        stop_cpu_stress()

    stress_stop_process = multiprocessing.Process(target=stop_stress_after_duration)
    stress_stop_process.start()

    attack_message = f"""
    ⚡️🔥 𝐀𝐓𝐓𝐀𝐂𝐊 𝐃𝐄𝐏𝐋𝐎𝐘𝐄𝐃 🔥⚡️

    👑 **Commander**: `{user_id}`
    🎯 **Target Locked**: `{target}`
    📡 **Port Engaged**: `{port}`
    ⏳ **Duration**: `{duration} seconds`
    ⚔️ **Weapon**: `BGMI Protocol`

    🔥 **The wrath is unleashed. May the network shatter!** 🔥
    """
    try:
        bot.send_message(message.chat.id, attack_message, parse_mode='Markdown')
    except telebot.apihelper.ApiTelegramException as e:
        logging.error(f"Telegram API error: {e}")
        bot.reply_to(message, "🚨 Failed to deploy the attack. Please check your parameters.")

# Polling with retry logic
while True:
    try:
        bot.polling(none_stop=True, interval=0, allowed_updates=["message"])
    except Exception as e:
        logging.error(f"Polling error: {e}")
        time.sleep(5)
        