#!/usr/bin/env bash
python ./gardena2mqtt.py --gardena_username=${GARDENA_USERNAME} --gardena_password=${GARDENA_PASSWORD} --gardena_apikey=${GARDENA_APIKEY} --mqtt_host=${MQTT_HOSTNAME} --mqtt_port=${MQTT_PORT} --mqtt_user=${MQTT_USERNAME} --mqtt_password=${MQTT_PASSWORD} --mqtt_prefix=${MQTT_PREFIX}
