FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Copy project files
COPY . /app/

# Create virtual environment and install dependencies
RUN python3 -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install -r requirements.txt && \
    chmod +x entrypoint.sh

# Collect static files (if you use Django staticfiles)
RUN /opt/venv/bin/python manage.py collectstatic --noinput --clear

# Entrypoint
CMD ["/app/entrypoint.sh"]