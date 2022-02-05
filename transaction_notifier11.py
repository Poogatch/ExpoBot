import logging
import threading
import time
from collections import deque
from json import JSONDecodeError

import requests
import schedule

logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s] %(name)s - %(levelname)s - %(message)s')
LOG = logging.getLogger(__name__)


BOT_API_KEY = '5178892115:AAGVaTYLhslBQW29FL5CfZ_Kyf9wIxOF0FU'
CHANNEL_ID = '-1001620608960'

total_supply = 816722973503
liquidity_pool_id = '0x8e1b5164d4059fdec87ec5d0b9c64e4ff727b1ed'
dex_screener_base_url = 'https://io8.dexscreener.io/u/trading-history/recent/ethereum/'
dbank_api_url = 'https://openapi.debank.com/v1/user/total_balance?id='
etherscan_api_url = 'https://api.etherscan.io/api'
contract_address = '0xcfaf8edcea94ebaa080dc4983c3f9be5701d6613'
etherscan_api_key = '0xc7260d904989febb1a2d12e46dd6679adb99a6f7'
covalent_base_api = 'https://api.covalenthq.com/v1/1'
covalent_transactions_api = f'{covalent_base_api}/transaction_v2/'
covalent_holders_api = f'{covalent_base_api}/tokens/0xc7260D904989fEbB1a2d12e46dd6679aDB99A6F7/token_holders/'
covalent_locked_holder_addr = '0xe2fe530c047f2d85298b07d9333c05737f1435fb'
covalent_api_key = 'ckey_86c5aebd8b36441c8b7514dbe54'
null_address = '0x0000000000000000000000000000000000000000'
treasury_wallet_address = '0x9e2f500a31f5b6ec0bdfc87957587307d247a595'
treasury_wallet_address_degen = '0x880a3769d82d63ee014195b758854d5750bb30ca'
dbank_token_search_url = 'https://openapi.debank.com/v1/user/token_search?chain_id=eth&id=' \
                         + treasury_wallet_address + '&q=' + contract_address + '&has_balance'
dbank_token_search_url_degen = 'https://openapi.debank.com/v1/user/token_search?chain_id=eth&id=' \
                         + treasury_wallet_address_degen + '&q=' + contract_address + '&has_balance'
queue = deque(maxlen=10)

state = {
    'lastTimestamp': int(time.time() * 1000),
    'lockedSupply': 0,
    'lockedSupplyValidity': 1650398706
}


def send_message(text):
    """
    Send a message to the telegram channel using preconfigured bot
    """
    LOG.info(f'Sending message: {text}')
    url = "https://api.telegram.org/bot" + BOT_API_KEY
    params = {'chat_id': CHANNEL_ID, 'text': text, "parse_mode": "html", 'disable_web_page_preview': 'True'}
    response = requests.post(url + '/sendMessage', data=params)
    LOG.info(f'Bot message response: {response.text}')


def get_transaction_history():
    """
    1. Get transaction history from dex screener using token address
    2. Filter only 'buy' trades, happening after the last processed block timestamp
    3. Return a list of actionable trades
    """
    url = dex_screener_base_url + liquidity_pool_id
    response = requests.get(url)
    trading_data = response.json()

    # Filter transaction history
    trading_history = [trade for trade in trading_data['tradingHistory']
                       if trade['blockTimestamp'] > state['lastTimestamp'] and trade['type'] == 'buy']
    return trading_history





def get_tokens(txn_hash):
    """
    Retrieve burn tokens using the transaction hash from Covalent api
    """
    time.sleep(30)
    url = covalent_transactions_api + txn_hash + '/'
    response = requests.get(url + '?key=' + covalent_api_key)
    data = response.json()
    if 'data' not in data:
        LOG.warning("Burn tokens not found")
        return None

    items = data['data']['items']
    if len(items) > 0:
        log_events = items[0]['log_events']
        if len(log_events) > 0:
            received = log_events[2]['decoded']['params'][2]['value']
            reflected = log_events[3]['decoded']['params'][2]['value']
            for event in log_events:
                event_type = event['decoded']
                if event_type['name'].lower() == 'Transfer'.lower():
                    if len(event_type['params']) > 0:
                        for param in event_type['params']:
                            if param['name'] == 'to' and param['value'] == null_address:
                                return event_type['params'][2]['value'], received, reflected


def get_treasury_amount():
    response = requests.get(dbank_token_search_url)
    data = response.json()
    return data[0]['amount']

def get_treasury_amount_degen():
    response = requests.get(dbank_token_search_url_degen)
    data = response.json()
    return data[0]['amount']




def get_header(trade_amount):
    header = 'EXPO BUY \n🟢🚀🟢🚀🟢🚀🟢\n🟢🟢🟢🟢🟢🟢🟢'
    if float(trade_amount) < 1.00:
        return header
    elif 1.00 <= float(trade_amount) < 2.00:
        header = 'EXPO BUY \n🟢🚀🟢🚀🟢🚀🟢🚀🟢🚀🟢\n🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢'
    elif 2.00 <= float(trade_amount) < 5.00:
        header = 'EXPO BUY \n🟢🚀🟢🚀🟢🚀🟢🚀🟢🚀🟢🚀🟢🚀🟢🚀🟢🚀🟢\n🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢'
    elif float(trade_amount) >= 5.00:
        header = 'EXPO BUY \n🟢🚀🟢🚀🟢🚀🟢🚀🟢🚀🟢🚀🟢🚀🟢🚀🟢🚀🟢\n🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢'
    LOG.info(f'Header: {header}')
    return header



def prepare_message(eth_spent, printable_token_received, printable_treasury_tokens, printable_token_reflected, expo_buy_price,
                    printable_cmc, printable_total_balance, treasure_change_percent,
                    etherscan_link, dexscreener_link):
    message = ''
    message = message + '<b>' + get_header(eth_spent) + '</b>'
    message = message + '\n<b>Spent</b> 💸: ' + eth_spent + ' ETH'
    if printable_token_received != 'UNAVAILABLE':
        message = message + '\n<b>Received</b> 💰: ' + printable_token_received + ' EXPO'

    if printable_treasury_tokens != 'UNAVAILABLE':
        message = message + '\n<b>Treasury</b> 🏦: ' + printable_treasury_tokens + ' EXPO'

    if printable_token_reflected != 'UNAVAILABLE':
        message = message + '\n<b>Reflected</b> 🔙: $' + printable_token_reflected + ' USD'

    message = message + '\n<b>EXPO price</b>: $' + expo_buy_price

    if printable_cmc != 'UNAVAILABLE':
        message = message + '\n<b>Market Cap</b>: $' + printable_cmc + 'M'

    if printable_total_balance != 'UNAVAILABLE':
        message = message + '\n<b>Treasury</b> 🏦: $' + printable_total_balance + ' (' + str(round(treasure_change_percent, 2)) + '% EXPO)'

    message = message + '\n<a href="' + etherscan_link + '">TXN</a> | <a href="' + dexscreener_link + '">CHART</a>'
    return message


def calculate_transaction_data(trade):
    global treasure_change_percent
    eth_spent = trade['amount1']
    LOG.info("Eth spent: " + str(eth_spent))
    expo_buy_price = trade['priceUsd']


    try:
        total_balance = requests.get(dbank_api_url + treasury_wallet_address)
        total_balance_degen = requests.get(dbank_api_url + treasury_wallet_address_degen)
        treasury_balance = total_balance.json()['total_usd_value']
        treasury_balance_degen = total_balance_degen.json()['total_usd_value']
        ##########
        expo_amount = float(get_treasury_amount()) * float(expo_buy_price)
        treasury_balance = float(treasury_balance) + float(expo_amount) + float(treasury_balance_degen)
        treasure_change = float(expo_amount) / float(treasury_balance)
        treasure_change_percent = treasure_change * 100
        printable_total_balance = "{:,.0f}".format(
            treasury_balance) if treasury_balance else 'UNAVAILABLE'
    except TypeError as error:
        LOG.error("Data unavailable form API")
        printable_total_balance = 'UNAVAILABLE'
    except Exception as exception:
        LOG.error(
            "Exception occurred wile retrieving total balance from dbank", exception)
        printable_total_balance = 'UNAVAILABLE'
    except JSONDecodeError as error:
        LOG.error("Unable to parse json")
        printable_total_balance = 'UNAVAILABLE'

    try:
        _cmc = float(total_supply) * float(expo_buy_price)
        printable_cmc = str(round(float(_cmc) / ((10 ** 18) * (10 ** 6)), 2)) if _cmc else 'UNAVAILABLE'
    except TypeError as error:
        LOG.error("Covalent api service unavailable")
        printable_cmc = 'UNAVAILABLE'
    except JSONDecodeError as error:
        LOG.error("Unable to parse json")
        printable_cmc = 'UNAVAILABLE'
    try:
        # burned_tokens, received_tokens, reflected_tokens = get_tokens(trade['txnHash'])
        received_tokens = float(str(trade['amount0']).replace(',', ''))
        reflected_tokens = 0.05 * received_tokens
        treasury_tokens = 0.08 * reflected_tokens
        printable_treasury_tokens = "{:,.0f}".format(
            float(treasury_tokens)) if treasury_tokens else 'UNAVAILABLE'
        printable_token_received = "{:,.0f}".format(
            float(received_tokens)) if received_tokens else 'UNAVAILABLE'
        printable_token_reflected = "{:,.0f}".format(
            (float(reflected_tokens)) * float(expo_buy_price)) if reflected_tokens else 'UNAVAILABLE'
    except TypeError as error:
        LOG.error("Unable to find transaction data")
        printable_burnt_tokens = 'UNAVAILABLE'
        printable_token_received = 'UNAVAILABLE'
        printable_token_reflected = 'UNAVAILABLE'
    except JSONDecodeError as error:
        LOG.error("Unable to parse json")
        printable_burnt_tokens = 'UNAVAILABLE'
        printable_token_received = 'UNAVAILABLE'
        printable_token_reflected = 'UNAVAILABLE'
    except IndexError as error:
        LOG.error("Unable to parse json due to indexing issue")
        printable_burnt_tokens = 'UNAVAILABLE'
        printable_token_received = 'UNAVAILABLE'
        printable_token_reflected = 'UNAVAILABLE'

    try:
        etherscan_link = 'https://etherscan.io/tx/' + trade['txnHash']
        dexscreener_link = 'https://dexscreener.com/ethereum/' + liquidity_pool_id

        message = f"""{prepare_message(eth_spent,printable_token_received, printable_treasury_tokens, printable_token_reflected,
                                       expo_buy_price, printable_cmc, printable_total_balance, treasure_change_percent, etherscan_link, dexscreener_link)}"""
        send_message(message)

    except NameError as error:
        LOG.error("Could not process some data", error)


def track_transaction():
    global trades
    LOG.info('Fetching transaction history on v10')
    try:
        trades = get_transaction_history()
    except JSONDecodeError as error:
        LOG.error("Unable to fetch transaction. Some dexscreener issue.")
    except TypeError as error:
        LOG.error("Unable to fetch transaction. Some dexscreener issue.")

    if not trades:
        LOG.debug('No new transaction found')

    # executor = ThreadPoolExecutor(max_workers=10)
    for trade in list(reversed(trades)):
        LOG.info("Transaction hash of trade %s", trade['txnHash'])
        unique_log_index = trade['logIndex']
        if unique_log_index not in queue:
            t = threading.Thread(target=calculate_transaction_data, args=(trade,))
            t.start()
            # executor.submit(calculate_transaction_data, trade)
            # executor.shutdown(wait=False)
            # Update timestamp and logIndex queue only when a transaction has been successfully processed
            LOG.info('Trade block timestamp: ' + str(trade['blockTimestamp']))
            LOG.info('State last timestamp: ' + str(state['lastTimestamp']))
            if trade['blockTimestamp'] > state['lastTimestamp']:
                state['lastTimestamp'] = trade['blockTimestamp']
            queue.append(trade['logIndex'])


if __name__ == '__main__':
    schedule.every(5).seconds.do(track_transaction)
    LOG.info("Started transaction notification scheduler...")
    while True:
        schedule.run_pending()
