import telebot
from telebot import types
import sqlite3
import time

# TODO
# Карточки товара с новыми продуктами подхватываемые из spreadsheets и отправляемые в сообщении о новых продуктах
# Доделать функцию back2menu
# Ежедневные нотификации о нвых продуктов в боте
# После нажатии кнопки back называет имя бота вместо имени пользователя
# Добавить возможность наполнения товара админом и покказа этого товара по кнопке New goods ✅
# Добавить просмотр зарегистрированных пользователей админом бот
# Перенести базы данных рядом с файлом main

# Your own token from BotFather
TOKEN = ""
bot = telebot.TeleBot(TOKEN)

# Connecting 2 db using connection pooling
conn = sqlite3.connect('user_data.db', check_same_thread=False)
cursor = conn.cursor()

# Create the table if it doesn't exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        chat_id INTEGER,
        user_id INTEGER,
        email TEXT,
        phone TEXT,
        first_name TEXT,
        last_name TEXT
    )
''')
conn.commit()

# Product cards database
assortment_of_goods_conn = sqlite3.connect('assortment_of_goods.db', check_same_thread=False)
assortment_of_goods_cursor = assortment_of_goods_conn.cursor()

# Create the table of goods if it doesn't exists
assortment_of_goods_cursor.execute('''
    CREATE TABLE IF NOT EXISTS assortment_of_goods (
        id INTEGER PRIMARY KEY,
        name TEXT,
        description TEXT,
        price TEXT,
        image_url TEXT                                                                                 
    )
''')
assortment_of_goods_conn.commit()

# Admin functions
admin_ids = [] # Your tg id, not username, id!
@bot.message_handler(commands=['add_item'])
def add_item(message):
    user_id = message.from_user.id

    # Are u admininstrator?
    if user_id not in admin_ids:
        bot.send_message(message.chat.id, "You don't have permission to add new goods.")
        return
    # Request to enter details about new product
    bot.send_message(message.chat.id, "Enter the item name:")
    bot.register_next_step_handler(message, process_item_name)

def process_item_name(message):
    # Saving the item name and asking more data
    item_name = message.text
    chat_id = message.chat.id

    # Request about product description
    bot.send_message(chat_id, "Enter the item description:")
    bot.register_next_step_handler(message, lambda m: process_item_description(m, item_name))

def process_item_description(message, item_name):
    # Saving description of item, and asking next data
    item_description = message.text
    chat_id = message.chat.id

    # Request for item price
    bot.send_message(chat_id, "Enter the item price:")
    bot.register_next_step_handler(message, lambda m: process_item_price(m, item_name, item_description))

def process_item_price(message, item_name, item_description):
    try:
        # Saving price of item and add this item to database
        item_price = str(message.text)
        chat_id = message.chat.id

        bot.send_message(chat_id, "This item has been added to the database.")
        assortment_of_goods_cursor.execute('INSERT INTO assortment_of_goods (name, description, price) VALUES (?, ?, ?)',
                                       (item_name, item_description, item_price))
    except ValueError:
        bot.send_message(chat_id, "Invalid price. Please enter a valid number.")

# Time of Launch the bot
now = time.ctime()
print("The bot has been launched:", now)

# Tracking user state
user_state = {}
# Command handler /start
@bot.message_handler(commands=["start"])
def start(message):
    # Cleaning  the previous state
    user_state[message.chat.id] = None

    # Defining user data
    chat_id = message.chat.id
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name

    # Writing user data to the database
    cursor.execute('INSERT INTO users (chat_id, user_id, first_name, last_name) VALUES (?, ?, ?, ?)',
                   (chat_id, user_id, first_name, last_name))
    conn.commit()

    # Welcome message and menu buttons
    markup = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton("🛎️ New customer", callback_data='new_user')
    button2 = types.InlineKeyboardButton("🛍️ New goods", callback_data='new_goods') # Message about a new goods
    button3 = types.InlineKeyboardButton("🛒 Our shop", url='google.com') # Link to eshop
    button4 = types.InlineKeyboardButton("🆘 Help", callback_data='help') # Message about a new goods
    button5 = types.InlineKeyboardButton("❓ About", callback_data='about') # Message about an author
    button6 = types.InlineKeyboardButton("🔙 Back", callback_data='back') # back
    markup.add(button1)
    markup.add(button2)
    markup.add(button3)
    markup.add(button4)
    markup.add(button5)
    markup.add(button6)

    bot.send_message(message.chat.id, f"Hello, {first_name}! Click the button to fill your data.", reply_markup=markup)

# Get the list of itmes from database

def get_items():
    assortment_of_goods_cursor.execute('SELECT name, description, price FROM assortment_of_goods')
    items = assortment_of_goods_cursor.fetchall()
    return items


# Button handler
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id

    if call.data == 'new_user':
        # Request to fill the user data
        bot.send_message(call.message.chat.id, "Please enter your email:")
        bot.register_next_step_handler(call.message, process_email)
        user_state[chat_id] = 'process_email'
    elif call.data == 'new_goods':
        # Extract items from the data base
        items = get_items()
        # Send goods as message
        if items:
            item_message = "Our items: \n"
            for item in items:
                item_message += f"{item[0]} - {item[1]} - {item[2]}\n"
            bot.send_message(call.message.chat.id, item_message)
        else:
            bot.send_message(call.message.chat.id, "No items available.")    
    elif call.data == 'help':
        bot.send_message(call.message.chat.id, f"There are multiple menu options available. To register a new user, select the '🛎️New customer' button. For viewing new products, click on '🛍️New Products'. To visit our store, choose '🛒Our Shop'. And, to find information about the bot, select '❓About'.")    
    elif call.data == 'about':
        bot.send_message(call.message.chat.id, f"Author: Aydar Gainullin aka 4yd4r")        
    elif call.data == 'back':
        # Back to previous state
        if user_state[chat_id] == 'process_email':
            bot.send_message(chat_id, "You cancelled entering your email.")
            user_state[chat_id] = None
        elif user_state[chat_id] == 'process_phone':
            bot.send_message(chat_id, "You canceled entering your phone number.")
            user_state[chat_id] = 'process_email'
        elif user_state[chat_id] == 'process_first_name':
            bot.send_message(chat_id, "You canceled entering your first name.")    
            user_state[chat_id] = 'process_phone'
        elif user_state[chat_id] == 'process_last_name':
            bot.send_message(chat_id, "You canceled entering your last name.")       
            user_state[chat_id] = 'process_first_name'
        else:
            # If we don't have a prveious state then comeback to /start
            start(call.message) 
            user_state[chat_id] = None    

def process_email(message):
    # Saving user email and asking more data to database
    email = message.text
    chat_id = message.chat.id
    user_id = message.from_user.id

    cursor.execute('INSERT INTO users (chat_id, user_id, email) VALUES (?, ?, ?)',
                   (chat_id, user_id, email))
    conn.commit()

    bot.send_message(message.chat.id, "Please enter your phone number:")
    bot.register_next_step_handler(message, process_phone)

def process_phone(message):
    # Saving user phone data, and asking more data again :)
    phone = message.text
    chat_id = message.chat.id
    user_id = message.from_user.id

    cursor.execute('UPDATE users SET phone = ? WHERE chat_id = ? AND user_id = ?',
                   (phone, chat_id, user_id))
    conn.commit()

    bot.send_message(message.chat.id, "Please enter your first name:")
    bot.register_next_step_handler(message, process_first_name)

def process_first_name(message):
    # Saving the user first name then second name
    first_name = message.text
    chat_id = message.chat.id
    user_id = message.from_user.id

    cursor.execute('UPDATE users SET first_name = ? WHERE chat_id = ? AND user_id = ?',
                   (first_name, chat_id, user_id))
    conn.commit()

    bot.send_message(message.chat.id, "Please enter your last name:")
    bot.register_next_step_handler(message, process_last_name)

def process_last_name(message):
    # Saving the user second name and finishing the process
    last_name = message.text
    chat_id = message.chat.id
    user_id = message.from_user.id

    cursor.execute('UPDATE users SET last_name = ? WHERE chat_id = ? AND user_id = ?',
                   (last_name, chat_id, user_id))
    conn.commit()

    bot.send_message(message.chat.id, "Thank you! Your details have been recorded.")

# Don't let it crash
bot.polling(none_stop=True)

# Close connection to database
conn.close()
