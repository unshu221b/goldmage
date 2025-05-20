FROM python:3.11-slim

RUN python -m venv /opt/venv/
ENV PATH=/opt/venv/bin:$PATH

WORKDIR /app

# Create temporary env file BEFORE pip install
RUN echo "CLOUDINARY_CLOUD_NAME=dummy\n\
CLOUDINARY_PUBLIC_API_KEY=dummy\n\
CLOUDINARY_SECRET_API_KEY=dummy\n\
SECRET_KEY=dummy\n\
DEBUG=True\n\
DATABASE_URL=sqlite:///db.sqlite3\n\
STRIPE_SECRET_KEY=dummy\n\
STRIPE_PUBLIC_KEY=dummy\n\
STRIPE_WEBHOOK_SECRET=dummy\n\
STRIPE_MONTHLY_PRICE_ID=dummy\n\
STRIPE_YEARLY_PRICE_ID=dummy\n\
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=dummy\n\
CLERK_SECRET_KEY=dummy\n\
CLERK_WEBHOOK_SIGNING_SECRET=dummy\n\
BASE_URL=http://localhost:8000\n\
ENV_ALLOWED_HOSTS=localhost\n\
EMAIL_HOST=dummy\n\
EMAIL_PORT=587\n\
EMAIL_HOST_USER=dummy\n\
EMAIL_HOST_PASSWORD=dummy\n\
EMAIL_USE_TLS=True\n\
ADMIN_EMAIL=dummy@example.com\n\
AWS_ACCESS_KEY_ID=dummy\n\
AWS_SECRET_ACCESS_KEY=dummy\n\
REDIS_HOST=redis\n\
REDIS_PORT=6379\n\
REDIS_PASSWORD=\n\
OPENAI_API_KEY=dummy\n\
ENVIRONMENT=development" > .env

COPY ./requirements.txt /tmp/requirements.txt

COPY ./src /app/

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# Collect static files
RUN /opt/venv/bin/python manage.py collectstatic --noinput --clear

RUN rm .env

# Make sure entrypoint.sh is executable
RUN chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]