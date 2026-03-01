FROM python:3.14-slim

WORKDIR /api

COPY ./api/requirements.txt /api/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /api/requirements.txt

COPY ./api/ /api

CMD ["fastapi", "run", "main.py", "--port", "3069"]