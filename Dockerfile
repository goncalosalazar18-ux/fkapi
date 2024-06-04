FROM python:3.10.6

WORKDIR /app 

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY ./fkapi .

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]