FROM python:3.4
RUN pip install aiohttp aiozmq msgpack-python

ADD ./metabolic-ninja/server.py .

EXPOSE 8080

EXPOSE 5555

CMD ["python", "./server.py"]