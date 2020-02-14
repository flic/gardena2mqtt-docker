import websocket
from threading import Thread
import time
import sys
import getopt
import requests
import paho.mqtt.client as mqtt
import json


# other constants
AUTHENTICATION_HOST = 'https://api.authentication.husqvarnagroup.dev'
SMART_HOST = 'https://api.smart.gardena.dev'

mqttclient = mqtt.Client('gardena_ws')

MQTTPREFIX = ''

def iterate(topic,msg):
    message = {}
    for key, value in msg.items():
        if isinstance(value, dict):
            iterate(topic+'/'+key,value)
        elif isinstance(value, list):
            i = 0
            for x in value:
                i += 1
                iterate(topic+'/'+i,value)
        else:
            message[key] = value
    if len(message) > 0:
        mqttclient.publish(topic,json.dumps(message),0,True)

class Client:
    def on_message(self, message):
        global MQTTPREFIX
        msg = json.loads(message)
        iterate(MQTTPREFIX+'/'+msg['type'],msg)
        sys.stdout.flush()

    def on_error(self, error):
        print("error", error)

    def on_close(self):
        self.live = False
        print("### closed ###")
        sys.exit(0)

    def on_open(self):
        print("### connected ###")

        self.live = True

        def run(*args):
            while self.live:
                time.sleep(1)

        Thread(target=run).start()

# mqtt
#define callback
def on_message(client, userdata, message):
    print("received message =",str(message.payload.decode("utf-8")))

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected with result code "+str(rc))
    else:
        print("Connection failed with with result code "+str(rc)+". Exiting...")
        exit()

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    #client.subscribe("$SYS/#")
def on_disconnect(client, userdata, rc):
   print("Client Got Disconnected, exiting...")
   exit()

def main(argv):
    global MQTTPREFIX

    try:
        opts, args = getopt.getopt(argv, '', ["gardena_username=","gardena_password=","gardena_apikey=","mqtt_host=","mqtt_port=","mqtt_user=","mqtt_password=","mqtt_prefix="])
    except getopt.GetoptError:
        print("Missing parameters")
        exit(2)

    for opt, arg in opts:
      if opt == "--gardena_username":
          USERNAME = arg
      elif opt == "--gardena_password":
          PASSWORD = arg
      elif opt == "--gardena_apikey":
          API_KEY = arg
      elif opt == "--mqtt_host":
          MQTTHOST = arg
      elif opt == "--mqtt_port":
          MQTTPORT = int(arg)
      elif opt == "--mqtt_user":
          MQTTUSER = arg
      elif opt == "--mqtt_password":
          MQTTPASSWORD = arg
      elif opt == "--mqtt_prefix":
          MQTTPREFIX = arg

    mqttclient.on_connect = on_connect
    mqttclient.on_disconnect = on_disconnect
    mqttclient.on_message=on_message
    print("Connecting to broker...")
    mqttclient.username_pw_set(MQTTUSER,password=MQTTPASSWORD)
    mqttclient.connect(MQTTHOST,MQTTPORT)
    mqttclient.loop_start()

    payload = {'grant_type': 'password', 'username': USERNAME, 'password': PASSWORD,
               'client_id': API_KEY}

    print("Logging into authentication system...")
    r = requests.post(f'{AUTHENTICATION_HOST}/v1/oauth2/token', data=payload)
    assert r.status_code == 200, r
    auth_token = r.json()["access_token"]

    headers = {
        "Content-Type": "application/vnd.api+json",
        "x-api-key": API_KEY,
        "Authorization-Provider": "husqvarna",
        "Authorization": "Bearer " + auth_token
    }

    r = requests.get(f'{SMART_HOST}/v1/locations', headers=headers)
    assert r.status_code == 200, r
    assert len(r.json()["data"]) > 0, 'location missing - user has not setup system'
    location_id = r.json()["data"][0]["id"]

    payload = {
        "data": {
            "type": "WEBSOCKET",
            "attributes": {
                "locationId": location_id
            },
            "id": "does-not-matter"
        }
    }
    print("Logged in (%s), getting WebSocket ID..." % auth_token)
    r = requests.post(f'{SMART_HOST}/v1/websocket', json=payload, headers=headers)

    assert r.status_code == 201, r
    print("WebSocket ID obtained, connecting...")
    response = r.json()
    websocket_url = response["data"]["attributes"]["url"]

    # websocket.enableTrace(True)
    client = Client()
    ws = websocket.WebSocketApp(
        websocket_url,
        on_message=client.on_message,
        on_error=client.on_error,
        on_close=client.on_close)
    ws.on_open = client.on_open
    ws.run_forever(ping_interval=150, ping_timeout=1)

if __name__ == "__main__":
    main(sys.argv[1:])

