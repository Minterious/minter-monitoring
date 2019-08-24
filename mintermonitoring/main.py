import sys
import json
import logging.config
import time
import pickle

from telegram.ext import Updater, CommandHandler
from mintersdk.minterapi import MinterAPI


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(u'Usage: {} config'.format(sys.argv[0]))
        sys.exit(1)

    # load config
    with open(sys.argv[1], 'r') as f:
        config = json.load(f)

    # configure logging
    logging.config.dictConfig(config['logger'])

    updater = Updater(token=config['telegram_bot_token'], use_context=True)
    dispatcher = updater.dispatcher

    auth_key = config['monitoring_auth_key']
    chats_file = config['telegram_chats_file']

    try:
        with open(chats_file, 'rb') as handle:
            chats = pickle.load(handle)
    except FileNotFoundError:
        chats = []  # [(bot, chat_id), ...]

    def start(update, context):
        msg = update.message
        bot = context.bot
        chat_id = msg.chat_id

        if (bot, chat_id) in chats:
            bot.send_message(chat_id=chat_id, text="Already authorized")
            return

        msg_tokens = msg.text.split()
        if len(msg_tokens) < 2 or msg_tokens[1] != auth_key:
            bot.send_message(chat_id=chat_id, text="Auth failed")
            return

        chats.append((bot, chat_id))
        with open(chats_file, 'wb') as handle:
            pickle.dump(chats, handle, protocol=pickle.HIGHEST_PROTOCOL)

        bot.send_message(chat_id=chat_id, text="Successful auth")

    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)

    updater.start_polling()

    minterapi = MinterAPI(config['minter_api_url'])
    pub_keys = config['minter_nodes_pub_keys']

    while True:
        for pub_key in pub_keys:
            response = minterapi.get_candidate(pub_key)

            error = response.get('error')
            if not error:
                status = response['result']['status']

                # If status = 1, node is offline
                if status == 1:
                    msg = '{} node is offline'.format(pub_key)
                    logging.debug(msg)
                    for bot, chat_id in chats:
                        bot.send_message(chat_id=chat_id, text=msg)
            else:
                logging.error(error)

            response = minterapi.get_missed_blocks(pub_key)

            error = response.get('error')
            if not error:
                missed_blocks = int(response['result']['missed_blocks_count'])

                if missed_blocks > 0:
                    msg = '{} node has missed {} blocks'.format(pub_key, missed_blocks)
                    logging.debug(msg)
                    for bot, chat_id in chats:
                        bot.send_message(chat_id=chat_id, text=msg)
            else:
                logging.error(error)

        time.sleep(1)
