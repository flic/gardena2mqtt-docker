FROM python:3

WORKDIR /app

COPY gardena_ws.py /app
COPY startup.sh /app

RUN chmod a+x /app/startup.sh

RUN pip install requests
RUN pip install websocket-client
RUN pip install paho-mqtt

ENTRYPOINT [ "/app/startup.sh" ]
