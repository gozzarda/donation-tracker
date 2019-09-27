FROM tiangolo/uvicorn-gunicorn-starlette:python3.7

RUN mkdir /data

COPY ./app/requirements.txt /app/
RUN pip install -r /app/requirements.txt

COPY ./app /app