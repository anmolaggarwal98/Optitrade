import socket
import select

#--------------------------------------
REMOTE_IP = "178.62.36.224"
UDP_ANY_IP = ""

USERNAME = "Team15"
PASSWORD = "KG4HgHEE"
# -------------------------------------
# EML code (EML is execution market link)
# -------------------------------------
EML_UDP_PORT_LOCAL = 8078
EML_UDP_PORT_REMOTE = 8001

eml_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
eml_sock.bind((UDP_ANY_IP, EML_UDP_PORT_LOCAL))
# -------------------------------------
# IML code (IML is information market link)
# -------------------------------------

IML_UDP_PORT_LOCAL = 7078
IML_UDP_PORT_REMOTE = 7001
IML_INIT_MESSAGE = "TYPE=SUBSCRIPTION_REQUEST"
iml_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
iml_sock.bind((UDP_ANY_IP, IML_UDP_PORT_LOCAL))
# -------------------------------------
# Auto trader
# -------------------------------------
'''
def start_autotrader():
    subscribe()
    event_listener()'''

def event_listener():
    """
    Wait for messages from the exchange and
    call handle_message on each of them.
    """
    while True:
        ready_socks,_,_ = select.select([iml_sock, eml_sock], [], [])
        for socket in ready_socks:
            data, addr = socket.recvfrom(1024)
            message = data.decode('utf-8')
            handle_message(message)

def subscribe():
    iml_sock.sendto(IML_INIT_MESSAGE.encode(), (REMOTE_IP, IML_UDP_PORT_REMOTE))

def send_order(target_feedcode, action, target_price, volume):
    """
    Send an order to the exchange.
    :param target_feedcode: The feedcode, either "SP-FUTURE" or "ESX-FUTURE"
    :param action: "BUY" or "SELL"
    :param target_price: Price you want to trade at
    :param volume: Volume you want to trade at. Please start with 10 and go from there. Don't go crazy!
    :return:
    Example:
    If you want to buy  100 SP-FUTURES at a price of 3000:
    - send_order("SP-FUTURE", "BUY", 3000, 100)
    """
    order_message = f"TYPE=ORDER|USERNAME={USERNAME}|PASSWORD={PASSWORD}|FEEDCODE={target_feedcode}|ACTION={action}|PRICE={target_price}|VOLUME={volume}"
    #print(f"[SENDING ORDER] {order_message}")
    eml_sock.sendto(order_message.encode(), (REMOTE_IP, EML_UDP_PORT_REMOTE))

#---------------------Actual Code starts here----------------------------------------------------
def sign(str,point):
    if str == 'BID':
        return -point
    else:
        return point

trade_dict = dict()
trade_dict['ESX_vol'] = []
trade_dict['SP_vol'] = []

ESX_bid_price = None
ESX_ask_price = None

SP_bid_price = None
SP_ask_price = None

def handle_message(message):

    global trade_dict

    comps = message.split("|")

    length = 10
    feedcode = None

    global ESX_bid_price
    global ESX_ask_price
    global SP_bid_price
    global SP_ask_price

    if len(comps) == 0:
        print(f"Invalid message received: {message}")
        return

    type = comps[0]

    if type == "TYPE=PRICE":

        feedcode = comps[1].split("=")[1]
        #print(feedcode)

        if feedcode == 'ESX-FUTURE':

            ESX_bid_price = float(comps[2].split("=")[1])
            bid_volume = int(comps[3].split("=")[1])
            ESX_ask_price = float(comps[4].split("=")[1])
            ask_volume = int(comps[5].split("=")[1])

        elif feedcode == 'SP-FUTURE':

            SP_bid_price = float(comps[2].split("=")[1])
            bid_volume = int(comps[3].split("=")[1])
            SP_ask_price = float(comps[4].split("=")[1])
            ask_volume = int(comps[5].split("=")[1])

    if type == "TYPE=TRADE":

        feedcode = comps[1].split("=")[1]
        #print(feedcode)
        side = comps[2].split("=")[1]
        #print(side)
        traded_price = float(comps[3].split("=")[1])
        traded_volume = int(comps[4].split("=")[1])

        if len(trade_dict['ESX_vol']) == length:
            trade_dict['ESX_vol'].pop(0)
            trade_dict['ESX_vol'].append(sign(side,traded_volume))

        elif len(trade_dict['SP_vol']) == length:
            trade_dict['SP_vol'].pop(0)
            trade_dict['SP_vol'].append(sign(side,traded_volume))

        else:
            trade_dict['SP_vol'].append(sign(side,traded_volume))
            trade_dict['ESX_vol'].append(sign(side,traded_volume))

        s_ESX = sum(trade_dict['ESX_vol'])
        s_tilde_ESX = sum(list(map(lambda x: abs(x),trade_dict['ESX_vol'])))

        s_SP = sum(trade_dict['SP_vol'])
        s_tilde_SP = sum(list(map(lambda x: abs(x),trade_dict['SP_vol'])))

        end_points = 0.4
        volume = 200

        if feedcode == 'ESX-FUTURE':
            #bid_price = float(comps[2].split("=")[1])
            #ask_price = float(comps[4].split("=")[1])

            ratio_ESX = s_ESX/s_tilde_ESX

            if ratio_ESX >= end_points:
                send_order('ESX_FUTURE', 'BUY', ESX_ask_price, volume)
                print(f'{volume} ESX-FUTURE BOUGHT at {ESX_ask_price}')

            elif ratio_ESX <= -end_points:
                send_order('ESX_FUTURE','SELL',ESX_bid_price, volume)
                print('\t'*6+f'{volume} ESX-FUTURE SOLD at {ESX_bid_price}')

        elif feedcode == 'SP-FUTURE':
            #bid_price = float(comps[2].split("=")[1])
            #ask_price = float(comps[4].split("=")[1])

            ratio_SP = s_SP/s_tilde_SP

            if ratio_SP >= end_points:
                send_order('SP_FUTURE', 'BUY', SP_ask_price, volume)
                print(f'{volume} SP-FUTURE BOUGHT at {SP_ask_price}')

            elif ratio_SP <= -end_points:
                send_order('SP_FUTURE','SELL',SP_bid_price, volume)
                print('\t'*6+f'{volume} SP-FUTURE SOLD at {SP_bid_price}')

        #print(f"[TRADE] product: {feedcode} side: {side} price: {traded_price} volume: {traded_volume}")

    if type == "TYPE=ORDER_ACK":

        if comps[1].split("=")[0] == "ERROR":
            error_message = comps[1].split("=")[1]
            #print(f"Order was rejected because of error {error_message}.")
            return

        feedcode = comps[1].split("=")[1]
        traded_price = float(comps[2].split("=")[1])

        # This is only 0 if price is not there, and volume became 0 instead.
        # Possible cause: someone else got the trade instead of you.
        if traded_price == 0:
            #print(f"Unable to get trade on: {feedcode}")
            return

        traded_volume = int(comps[3].split("=")[1])

        #print(f"[ORDER_ACK] feedcode: {feedcode}, price: {traded_price}, volume: {traded_volume}")

if __name__=='__main__':
    event_listener()
