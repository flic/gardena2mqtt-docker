# gardena2mqtt-docker
Husqvarna Cloud Websocket2MQTT (Husqvarna, Gardena. https://developer.1689.cloud/)

Usage:

gardena2mqtt:
    image: frtnbach/gardena2mqtt:latest
    restart: unless-stopped
    environment:
      - "GARDENA_USERNAME=<username>"
      - "GARDENA_PASSWORD=<password>"
      - "GARDENA_APIKEY=<apikey>"
      - "MQTT_HOSTNAME=mosquitto"
      - "MQTT_PORT=1883"
      - "MQTT_USERNAME=<username>"
      - "MQTT_PASSWORD=<password>"
      - "MQTT_PREFIX=gardena"

