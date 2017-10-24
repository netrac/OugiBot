import logging
import sqlite3
import time

import anitopy
import feedparser
from fuzzywuzzy import fuzz
from telegram import ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import (Unauthorized, BadRequest,
                            ChatMigrated)
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler

from secret import TOKEN

logging.basicConfig(filename='../rsc/OugiBot.log',filemode='a',format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


def parse():
    feeds = open("../rsc/feeds.txt").readlines()
    l = list()
    rlist = list()
    for f in feeds:
        l.append(feedparser.parse(f))
    for rss in l:
        for item in rss.entries:
            rlist.append(anitopy.parse(item.title))

    return rlist


def build_menu(buttons, n_cols, header_buttons=None, footer_buttons=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, header_buttons)
    if footer_buttons:
        menu.append(footer_buttons)
    return menu


def broadcast(bot, title, number):
    conn = sqlite3.connect("../rsc/db.db")
    conn.execute("PRAGMA foreign_keys = 1")
    c = conn.cursor()
    c.execute("SELECT chatid FROM watchlist WHERE title = ?", [title])
    users = c.fetchall()
    num_users = 0
    for user in users:
        num_users += 1;
        try:
            bot.send_message(chat_id=user[0], text="Episode {} of {} has just been released!".format(number, title))
        except Unauthorized:
            num_users -= 1
            conn.execute("DELETE FROM watchlist WHERE chatid = ?"[user[0]])
            logger.warning("User {} has been removed".format(user[0]))
        except ChatMigrated as e:
            conn.execute("UPDATE watchlist SET chatid = ? where chatid = ?", [e.new_chat_id, user[0]])
            bot.send_message(chat_id=e.new_chat_id, text="{} {}".format(title, number))
        except Exception as e:
            logger.warning("Error while broadcasting {} to {}:\n {}".format(bot,user[0],e))

        time.sleep(0.05)
    if num_users > 0:
        logger.info("{} episode {} broadcasted to {} users".format(title, number, num_users))


def update_feed(bot, job):

    conn = sqlite3.connect("../rsc/db.db")
    conn.execute("PRAGMA foreign_keys = 1")
    episodes = parse()
    new_episodes = 0
    new_series = 0
    for episode in episodes:
        c = conn.cursor()
        c.execute("Select * from series WHERE title= ?", [episode['anime_title']])
        result = c.fetchall()
        if (len(result) == 0):
            new_series += 1
            c.execute("INSERT INTO series(title,episodes) VALUES (?,?)",
                      [episode['anime_title'], int(episode['episode_number'])])
            continue
        e_title = result[0][0]
        e_num = result[0][1]
        if (e_num < int(episode['episode_number'])):
            new_episodes += 1
            c.execute("Update series SET episodes = ? WHERE title = ?", [int(episode['episode_number']), e_title])
            broadcast(bot, e_title, int(episode['episode_number']))
    if new_series > 0:
        logger.info("Added {} new series".format(new_series))
    if new_episodes > 0:
        logger.info("Added {} new episodes".format(new_episodes))
    conn.commit()


def start(bot, update):
    text = """
    Hi! I'm a bot that lets you track your favorite seasonal anime. My job is to notify you when a new episode is released!
    <b>Commands:</b>
    /add    - Adds a new anime to your notifications
    /list   - Lists all the anime that you follow
    /remove - Removes an anime from your notifications   
    """
    bot.send_message(chat_id=update.message.chat_id, text=text, parse_mode=ParseMode.HTML)


def add_anime(bot, message, title):
    conn = sqlite3.connect("../rsc/db.db")
    conn.execute("PRAGMA foreign_keys = 1")
    try:
        conn.execute("INSERT INTO watchlist(chatid,title) VALUES (?,?)", [str(message.chat_id), title])
        logger.info("{} added {}".format(message.chat_id,title))

        bot.send_message(chat_id=message.chat_id, text="{} has been added successfully to your list.".format(title))
        conn.commit()
    except sqlite3.IntegrityError as e:
        bot.send_message(chat_id=message.chat_id, text="{} is already on your list.".format(title))


def rm_anime(bot, message, title):
    conn = sqlite3.connect("../rsc/db.db")
    conn.execute("PRAGMA foreign_keys = 1")

    if conn.execute("DELETE FROM watchlist WHERE chatid = ? AND title = ?", [str(message.chat_id), title]).rowcount > 0:
        bot.send_message(chat_id=message.chat_id, text="{} has been removed successfully from your list.".format(title))
        logger.info("{} removed {}".format(message.chat_id,title))

        conn.commit()
    else:
        bot.send_message(chat_id=message.chat_id, text="You can't remove {} from your list because you're not tracking it yet!".format(title))


def add(bot, update, args):
    conn = sqlite3.connect("../rsc/db.db")
    conn.execute("PRAGMA foreign_keys = 1")
    anime = ' '.join(args)
    if (len(anime) == 0):
        bot.send_message(chat_id=update.message.chat_id, text="Usage: /add <name of the series>")
        return
    c = conn.cursor()

    c.execute("SELECT title, Rowid FROM series")
    animelist = c.fetchall()
    l = list()
    for a in animelist:
        l.append([a, fuzz.partial_ratio(a[0].lower(), anime.lower())])
    l.sort(key=lambda score: score[1], reverse=True)

    choices = l[:4]
    if (choices[0][0][0] == anime):
        add_anime(bot, update.message, anime)
        return

    keyboard = []
    for i in choices:
        keyboard.append(InlineKeyboardButton(text=i[0][0], callback_data="add#" + str(i[0][1])))
    if (len(keyboard) == 0):
        bot.send_message(chat_id=update.message.chat_id, text="{} couldn't be found. Make sure it's a seasonal anime (i.e. not a previously broadcasted one).".format(anime))
        return
    keyboard.append((InlineKeyboardButton(text="\u2B05 Cancel search", callback_data="abort")))
    reply_markup = InlineKeyboardMarkup(build_menu(keyboard, n_cols=1))

    update.message.reply_text('Please choose:', reply_markup=reply_markup)


def add_button(bot, update):
    conn = sqlite3.connect("../rsc/db.db")
    conn.execute("PRAGMA foreign_keys = 1")
    query = update.callback_query
    Rowid = str(query.data).split('#')[1]

    c = conn.cursor()
    c.execute("SELECT title FROM series WHERE Rowid = ?", [Rowid])
    title = c.fetchall()[0][0]
    bot.deleteMessage(chat_id=query.message.chat_id, message_id=query.message.message_id)
    add_anime(bot, query.message, title)


def remove(bot, update, args):
    conn = sqlite3.connect("../rsc/db.db")
    conn.execute("PRAGMA foreign_keys = 1")
    anime = ' '.join(args)
    if (len(anime) == 0):
        bot.send_message(chat_id=update.message.chat_id, text="Usage: /remove <name of the series>")
        return
    c = conn.cursor()
    c.execute("SELECT title, Rowid FROM series")
    animelist = c.fetchall()
    l = list()
    for a in animelist:
        l.append([a, fuzz.partial_ratio(a[0].lower(), anime.lower())])
    l.sort(key=lambda score: score[1], reverse=True)
    choices = l[:4]
    if (choices[0][0][0] == anime):
        rm_anime(bot, update.message, anime)
        return

    keyboard = []
    for i in choices:
        keyboard.append(InlineKeyboardButton(text=i[0][0], callback_data="rm#" + str(i[0][1])))
    if (len(keyboard) == 0):
        bot.send_message(chat_id=update.message.chat_id, text="{} couldn't be found. Make sure it's a seasonal anime (i.e. not a previously broadcasted one).".format(anime))
        return
    keyboard.append((InlineKeyboardButton(text="\u2B05 Cancel search", callback_data="abort")))
    reply_markup = InlineKeyboardMarkup(build_menu(keyboard, n_cols=1))
    update.message.reply_text('Please, choose a series from the following:', reply_markup=reply_markup)


def remove_button(bot, update):
    conn = sqlite3.connect("../rsc/db.db")
    conn.execute("PRAGMA foreign_keys = 1")
    query = update.callback_query
    Rowid = str(query.data).split('#')[1]
    c = conn.cursor()
    c.execute("SELECT title FROM series WHERE Rowid = ?", [Rowid])
    title = c.fetchall()[0][0]
    bot.deleteMessage(chat_id=query.message.chat_id, message_id=query.message.message_id)
    rm_anime(bot, query.message, title)

    return


def list_series(bot, update):
    conn = sqlite3.connect("../rsc/db.db")
    conn.execute("PRAGMA foreign_keys = 1")
    watchlist = ""
    for row in conn.execute("SELECT title FROM watchlist WHERE chatid = ? ORDER BY title", [update.message.chat_id]):
        watchlist += row[0] + '\n'
    if len(watchlist) == 0:
        update.message.reply_text("You are not being notified on any anime")
        return
    update.message.reply_text(watchlist)
    return


def abort_button(bot, update):
    bot.deleteMessage(chat_id=update.callback_query.message.chat_id,
                      message_id=update.callback_query.message.message_id)


def error_handler(bot, update, error):
    try:
        raise error
    except  Unauthorized as e:
        logger.warning(e)
        conn = sqlite3.connect("../rsc/db.db")
        conn.execute("PRAGMA foreign_keys = 1")
        conn.execute("DELETE FROM watchlist WHERE chatid = ?", [update.message.chat_id])
        logger.warning("User {} has been removed".format(update.message.chat_id))
    except Exception as e:
        logger.warning('Update "%s" caused error "%s"' % (update, e))
        # Create the Updater and pass it your bot's token.


updater = Updater(TOKEN)
updater.dispatcher.add_handler(CommandHandler("start", start))
updater.dispatcher.add_handler(CommandHandler("add", add, pass_args=True))
updater.dispatcher.add_handler(CallbackQueryHandler(pattern="add#.*", callback=add_button))
updater.dispatcher.add_handler(CallbackQueryHandler(pattern="rm#.*", callback=remove_button))
updater.dispatcher.add_handler(CallbackQueryHandler(pattern="abort", callback=abort_button))
updater.dispatcher.add_handler(CommandHandler("remove", remove, pass_args=True))
updater.dispatcher.add_handler(CommandHandler("list", list_series))
updater.dispatcher.add_handler(CommandHandler("help", start))
updater.dispatcher.add_error_handler(error_handler)
j = updater.job_queue
j.run_repeating(update_feed, interval=600, first=0)

# Start the Bot

updater.start_polling()

# Run the bot until the user presses Ctrl-C or the process receives SIGINT,
# SIGTERM or SIGABRT
updater.idle()
