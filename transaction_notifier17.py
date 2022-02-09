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


BOT_API_KEY = '5185799432:AAF2jHYKer2inIEOI6uOWSHU1vZm1o7uocU'
CHANNEL_ID = '-1001569990778'

liquidity_pool_id = '0x8e1b5164d4059fdec87ec5d0b9c64e4ff727b1ed'
dex_screener_base_url = 'https://io8.dexscreener.io/u/trading-history/recent/ethereum/'
dbank_api_url = 'https://openapi.debank.com/v1/user/total_balance?id='
etherscan_api_url = 'https://api.etherscan.io/api'
contract_address = '0xcfaf8edcea94ebaa080dc4983c3f9be5701d6613'
etherscan_api_key = 'XN5ZN7M7Q4QFQ553XG7FGM9DJ5SPZ2FJQT'
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
chad = "https://i.imgur.com/auV7S0u.webp"
wojack = "https://i.imgur.com/IW1OEoH.webp"

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


def send_pic(eth_spent):
    """
    Send pic
    """

    if float(eth_spent) < 4.9:
        url = "https://api.telegram.org/bot" + BOT_API_KEY
        params = {'chat_id': CHANNEL_ID, 'sticker':wojack}
        response = requests.post(url + '/sendSticker', data = params)
        LOG.info(f'Bot message response: chad image')
    else:
        url = "https://api.telegram.org/bot" + BOT_API_KEY
        params = {'chat_id': CHANNEL_ID, 'sticker':chad}
        response = requests.post(url + '/sendSticker', data = params)
        LOG.info(f'Bot message response: chad image')
        

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


def get_total_supply():
    """
    Retrieve total supply of tokens
    """
    params = {
        'module': 'stats',
        'action': 'tokensupply',
        'contractaddress': contract_address,
        'apikey': etherscan_api_key
    }
    response = requests.get(etherscan_api_url, data=params)
    if response.status_code == 200:
        return response.json()['result']
    LOG.warning('Total supply not found')

def get_eth_price():
    """
    Retrieve current ETH price
    """
    params = {
        'module': 'stats',
        'action': 'ethprice',
        'apikey': etherscan_api_key
    }
    response = requests.get(etherscan_api_url, data=params)
    if response.status_code == 200:
        return response.json()['result']
    LOG.warning('ETH Price not found')


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

def get_holder_amount(buyer_address):
    try:
        dbank_holder_search_url = 'https://openapi.debank.com/v1/user/token_search?chain_id=eth&id=' \
                             + buyer_address + '&q=' + contract_address + '&has_balance'
        response = requests.get(dbank_holder_search_url)
        data = response.json()
        return data[0]['amount']
    except ConnectionError as error:
        return 0
def get_buyer_address(tx_hash):
    params = {
        'module': 'proxy',
        'action': 'eth_getTransactionByHash',
        'txhash': str(tx_hash),
        'apikey': etherscan_api_key    
    }
    response = requests.get(etherscan_api_url, data=params)
    if response.status_code == 200:
        return response.json()['result']
    else:
        return "UNAVAILABLE"

def get_header(trade_amount):
    header = 'EXPO BUY \n'
    multiplier = int((float(trade_amount)*10) + 0.5)
    if multiplier == 0:
        bubbles = "🟢"
    else:
        bubbles = "🟢" * multiplier
    header = header + bubbles
    return header
    LOG.info(f'Header: {header}')
    return header



def prepare_message(eth_spent, usd_spent, printable_token_received, printable_treasury_tokens, printable_token_reflected, printable_treasury_eth, printable_reflected_eth, expo_buy_price,
                    printable_cmc, printable_total_balance, treasure_change_percent,
                    etherscan_link, dexscreener_link, printable_position):
    message = ''
    message = message + '<b>' + get_header(eth_spent) + '</b>'
    message = message + '\n<b>Spent</b> 💸: ' + eth_spent + ' ETH ($' + usd_spent + ' USD)'
    if printable_token_received != 'UNAVAILABLE':
        message = message + '\n<b>Received</b> 💰: ' + printable_token_received + ' EXPO'
    if printable_position != 'UNAVAILABLE':
        message = message + '\n<b>Holder Position</b> ⬆: ' + printable_position
        if printable_position != "NEW!": message = message +'%!'

    if printable_treasury_tokens != 'UNAVAILABLE':
        message = message + '\n<b>Treasury</b> 🏦: $' + printable_treasury_tokens + ' USD (' + printable_treasury_eth + ' ETH)' 

    if printable_token_reflected != 'UNAVAILABLE':
        message = message + '\n<b>Reflected</b> 🔙: $' + printable_token_reflected + ' USD (' + printable_reflected_eth + ' ETH)'

    message = message + '\n<b>EXPO price</b>: $' + expo_buy_price

    if printable_cmc != 'UNAVAILABLE':
        message = message + '\n<b>Market Cap</b>: $' + printable_cmc 

    if printable_total_balance != 'UNAVAILABLE':
        message = message + '\n<b>Treasury</b> 🏦: $' + printable_total_balance + ' (' + str(round(treasure_change_percent, 2)) + '% EXPO)'

    message = message + '\n<i>Balance may not include all shitcoins</i>'
    message = message + '\n<a href="' + etherscan_link + '">TXN</a> | <a href="' + dexscreener_link + '">CHART</a>'
    return message


def calculate_transaction_data(trade):
    global treasure_change_percent
    eth_spent = trade['amount1']
    eth_spent = str(round(float(eth_spent),2))
    LOG.info("Eth spent: " + str(eth_spent))
    expo_buy_price = trade['priceUsd']
    eth_price = get_eth_price()
    eth_price = float(eth_price.get('ethusd'))
    eth_spent_float = float(eth_spent)
    usd_spent = eth_price * eth_spent_float
    usd_spent = "{:,.2f}".format(
            float(round(usd_spent, 2)))

    
    try:
        total_supply = get_total_supply()
        printable_total_supply = "{:,.0f}".format(
            float(total_supply) / (10 ** 18)) if total_supply else 'UNAVAILABLE'
    except TypeError as error:
        LOG.error("Service unavailable for total supply")
        total_supply = 'UNAVAILABLE'
        printable_total_supply = 'UNAVAILABLE'
    except JSONDecodeError as error:
        LOG.error("Service unavailable for total supply")
        total_supply = 'UNAVAILABLE'
        printable_total_supply = 'UNAVAILABLE'
    except Exception as exception:
        LOG.error(
            "Exception occurred while retrieving total supply", exception)
        total_supply = 'UNAVAILABLE'
        printable_total_supply = 'UNAVAILABLE'
        
    try:
        total_balance = requests.get(dbank_api_url + treasury_wallet_address)
        total_balance_degen = requests.get(dbank_api_url + treasury_wallet_address_degen)
        treasury_balance = total_balance.json()['total_usd_value']
        treasury_balance_degen = total_balance_degen.json()['total_usd_value']
        ##########
        expo_amount_main = float(get_treasury_amount()) * float(expo_buy_price)
        expo_amount_degen = float(get_treasury_amount_degen()) * float(expo_buy_price)
        expo_amount = float(expo_amount_main) + float(expo_amount_degen)
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
    except ConnectionError as error:
        LOG.error("Couldn't connect to debank")
        printable_total_balance = 'UNAVAILABLE'


    try:
        _cmc = float(total_supply) * float(expo_buy_price) / 1000000000000000000
        printable_cmc = "{:,.0f}".format((float(_cmc))) if _cmc else 'UNAVAILABLE'
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
        treasury_tokens = 0.08 * received_tokens
        printable_treasury_tokens = "{:,.0f}".format(
            (float(treasury_tokens))* float(expo_buy_price)) if treasury_tokens else 'UNAVAILABLE'
        printable_token_received = "{:,.0f}".format(
            float(received_tokens)) if received_tokens else 'UNAVAILABLE'
        printable_token_reflected = "{:,.0f}".format(
            (float(reflected_tokens)) * float(expo_buy_price)) if reflected_tokens else 'UNAVAILABLE'
        ### Treasury received reflected in USD Value
        ### Reflected in USD Value
        ### Token Received in EXPO Value
        printable_treasury_eth = "{:,.3f}".format(
            (float(treasury_tokens))* float(expo_buy_price) / float(eth_price)) if treasury_tokens else 'UNAVAILABLE'
        printable_reflected_eth = "{:,.3f}".format(
            (float(reflected_tokens)) * float(expo_buy_price) / float(eth_price)) if reflected_tokens else 'UNAVAILABLE'
    except TypeError as error:
        LOG.error("Unable to find transaction data")
        printable_burnt_tokens = 'UNAVAILABLE'
        printable_token_received = 'UNAVAILABLE'
        printable_token_reflected = 'UNAVAILABLE'
        printable_treasury_eth = 'UNAVAILABLE'
        printable_reflected_eth = 'UNAVAILABLE'
    except JSONDecodeError as error:
        LOG.error("Unable to parse json")
        printable_burnt_tokens = 'UNAVAILABLE'
        printable_token_received = 'UNAVAILABLE'
        printable_token_reflected = 'UNAVAILABLE'
        printable_treasury_eth = 'UNAVAILABLE'
        printable_reflected_eth = 'UNAVAILABLE'
    except IndexError as error:
        LOG.error("Unable to parse json due to indexing issue")
        printable_burnt_tokens = 'UNAVAILABLE'
        printable_token_received = 'UNAVAILABLE'
        printable_token_reflected = 'UNAVAILABLE'
        printable_treasury_eth = 'UNAVAILABLE'
        printable_reflected_eth = 'UNAVAILABLE'

    try:
        txn_hash = trade['txnHash']
        address = get_buyer_address(txn_hash)
        address = str(address.get("from"))
        holdings = float(get_holder_amount(address)) - float(received_tokens)
        if holdings < 0:
            printable_position = "NEW!"
        else:
            printable_position = str(round(((float(received_tokens)/float(holdings))*100),2))
    except TypeError as error:
        printable_position = 'UNAVAILABLE'
    except JSONDecodeError as error:
        printable_position = 'UNAVAILABLE'
    except IndexError as error:
        printable_position = 'UNAVAILABLE'

    try:
        etherscan_link = 'https://etherscan.io/tx/' + trade['txnHash']
        dexscreener_link = 'https://dexscreener.com/ethereum/' + liquidity_pool_id

        message = f"""{prepare_message(eth_spent, usd_spent, printable_token_received, printable_treasury_tokens, printable_token_reflected, printable_treasury_eth,
                                       printable_reflected_eth, expo_buy_price, printable_cmc, printable_total_balance, treasure_change_percent, etherscan_link, dexscreener_link, printable_position)}"""
        send_message(message)
        if float(eth_spent) > 2.9:
            send_pic(eth_spent)
        
        

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
    except ConnectionError as error:
        LOG.error("Unable to connect to Dexscreener.")

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
