import sys
import json
import logging.config
import time
import pickle

from telegram.ext import Updater, CommandHandler
from mintersdk.minterapi import MinterAPI


if __name__ == '__main__':
    try:
        if len(sys.argv) < 2:
            raise Exception(u'Usage: {} config'.format(sys.argv[0]))

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

        nodes = {
            pub_key: {'status': 2, 'missed_blocks': 0}
            for pub_key in pub_keys
        }
        while True:
            try:
                for pub_key in pub_keys:
                    node = nodes[pub_key]

                    response = minterapi.get_candidate(pub_key)

                    error = response.get('error')
                    if not error:
                        status = response['result']['status']

                        # If status = 1 and node was previously online, alert that it's offline now
                        if status == 1 and node['status'] == 2:
                            msg = '{} node is offline'.format(pub_key)
                            if pub_key in config['node_pubkey']:
                                msg = '{} node is offline'.format(config['node_pubkey'][pub_key])
                            logging.info(msg)
                            for bot, chat_id in chats:
                                bot.send_message(chat_id=chat_id, text=msg)
                            node['status'] = 1
                    else:
                        logging.error('get_candidate: {}'.format(error))

                    response = minterapi.get_missed_blocks(pub_key)

                    error = response.get('error')
                    if not error:
                        missed_blocks = int(response['result']['missed_blocks_count'])

                        # If missed blocks count has increased, alert
                        if missed_blocks > node['missed_blocks']:
                            msg = '{} node has missed {} blocks'.format(pub_key, missed_blocks)
                            if pub_key in config['node_pubkey']:
				msg = '{} node has missed {} blocks'.format(config['node_pubkey'][pub_key], missed_blocks)
                            logging.info(msg)
                            for bot, chat_id in chats:
                                bot.send_message(chat_id=chat_id, text=msg)
                        node['missed_blocks'] = missed_blocks
                    else:
                        logging.error('get_missed_blocks: {}'.format(error))
            except Exception as e:
                logging.error('{}: {}'.format(e.__class__.__name__, e.__str__()))

            time.sleep(1)
    except Exception as e:
        logging.error('{}: {}'.format(e.__class__.__name__, e.__str__()))
        sys.exit(1)
