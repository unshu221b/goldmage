FROM python:3.11-slim

COPY . /app/
# Set work directory
WORKDIR /app

RUN python3 -m venv /opt/venv
RUN /opt/venv/bin/pip install pip --upgrade && \
    /opt/venv/bin/pip install -r requirements.txt && \
    chmod +x entrypoint.sh

# Collect static files (if you use Django staticfiles)
RUN /opt/venv/bin/python manage.py collectstatic --noinput --clear

# Entrypoint
CMD ["/app/entrypoint.sh"]