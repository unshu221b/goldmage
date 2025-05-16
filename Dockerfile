FROM python:3.11-slim

RUN python -m venv /opt/venv/
ENV PATH=/opt/venv/bin:$PATH

WORKDIR /app

COPY ./requirements.txt /tmp/requirements.txt

COPY ./src /app/

RUN pip install pip --upgrade
RUN pip install -r /tmp/requirements.txt

# Collect static files
RUN /opt/venv/bin/python manage.py collectstatic --noinput --clear

CMD ["/app/entrypoint.sh"]