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

mqttclient = mqtt.Client('gardena2mqtt')

MQTTPREFIX = ''
USERNAME = ''
PASSWORD = ''
API_KEY = ''

def getAccessHeader(username, password, apikey):
    global AUTHENTICATION_HOST
    payload = {'grant_type': 'password', 'username': username, 'password': password,'client_id': apikey}

    print("Logging into authentication system...")
    r = requests.post(AUTHENTICATION_HOST+'/v1/oauth2/token', data=payload)
    assert r.status_code == 200, r
    return {
        "Content-Type": "application/vnd.api+json",
        "x-api-key": apikey,
        "Authorization-Provider": "husqvarna",
        "Authorization": "Bearer " + r.json()["access_token"],
        "accept": "application/vnd.api+json"
    }

def valveControl(deviceId,msg):
    global SMART_HOST
    global USERNAME
    global PASSWORD
    global API_KEY

    headers = getAccessHeader(USERNAME,PASSWORD,API_KEY)
    data = {
        'data':  {
            'id': 'request-1',
            'type': 'VALVE_CONTROL',
            'attributes': {
                'command': msg['command'],
                'seconds': msg['seconds']
            }
        }
    }
    print("Sending command:")
    print(data)
    r = requests.put(SMART_HOST+'/v1/command/'+deviceId,data=json.dumps(data),headers=headers)

    if (r.status_code == 200):
        print('Command sent')
    else:
        print(r.content)
    assert r.status_code == 200, r

def iterate(topic,msg):
    message = {}
    try:
        for key, value in msg.items():
            if key == 'type':
                topic += '/'+value
                del msg[key]

        for key, value in msg.items():
            if key == 'id':
                topic += '/'+value
                del msg[key]
    except:
        pass

    if 'data' in msg.keys():
        if isinstance(msg['data'], list):
            i = 0
            for x in msg['data']:
                mqttclient.publish(topic.lower()+'/'+str(i),json.dumps(x),0,True)
                i += 1
        else:
            mqttclient.publish(topic.lower()+'/0',json.dumps(msg['data']),0,True)
        return

    else:
        for key, value in msg.items():
            if isinstance(value, dict):
                iterate(topic+'/'+key,value)
            elif isinstance(value, list):
                i = 0
                for x in value:
                    iterate(topic+'/'+str(i),value)
                    i += 1
            else:
                message[key] = value
    if len(message) > 0:
        mqttclient.publish(topic.lower(),json.dumps(message),0,True)

class Client:
    def on_message(self, message):
        global MQTTPREFIX
        msg = json.loads(message)
        iterate(MQTTPREFIX,msg)
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
    msg = message.payload
    print("Received message ("+message.topic+") "+str(msg))
    topic = message.topic.split('/')
    deviceId = topic[len(topic)-1]
    command = topic[len(topic)-2]
    msg = json.loads(msg)

    if command == 'valve_control':
        valveControl(deviceId,msg)

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    global MQTTPREFIX
    if rc == 0:
        print("Connected with result code "+str(rc))
    else:
        print("Connection failed with with result code "+str(rc)+". Exiting...")
        exit()

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.

    # Subscripe to command topic valve_control
    client.subscribe(MQTTPREFIX.lower()+'/valve_control/+')
def on_disconnect(client, userdata, rc):
   print("Client Got Disconnected, exiting...")
   exit()

def main(argv):
    global MQTTPREFIX 
    global USERNAME
    global PASSWORD
    global API_KEY   

    try:
        opts = getopt.getopt(argv, '', ["gardena_username=","gardena_password=","gardena_apikey=","mqtt_host=","mqtt_port=","mqtt_user=","mqtt_password=","mqtt_prefix="])
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

    print("MQTT user: "+MQTTUSER)

    mqttclient.on_connect = on_connect
    mqttclient.on_disconnect = on_disconnect
    mqttclient.on_message=on_message
    print("Connecting to broker...")
    mqttclient.username_pw_set(MQTTUSER,password=MQTTPASSWORD)
    mqttclient.connect(MQTTHOST,MQTTPORT)
    mqttclient.loop_start()

    headers = getAccessHeader(USERNAME,PASSWORD, API_KEY)

    r = requests.get(SMART_HOST+'/v1/locations', headers=headers)
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
    print("Logged in, getting WebSocket ID...")
    r = requests.post(SMART_HOST+'/v1/websocket', json=payload, headers=headers)

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

