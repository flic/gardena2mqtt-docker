FROM python:3

ADD gardena_ws.py /

RUN pip install requests

RUN pip install websocket-client

RUN pip install paho-mqtt

ENTRYPOINT [ "python", "./gardena_ws.py" ]
