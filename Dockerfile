FROM python:3.4
RUN pip install aiohttp aiozmq msgpack-python pymongo

ADD ./metabolic-ninja/server.py .
ADD ./metabolic-ninja/mongo_client.py .

EXPOSE 8080

EXPOSE 5555

CMD ["python", "./server.py"]