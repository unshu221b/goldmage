FROM python:3.11-slim

# Install Node.js and npm properly
RUN apt-get update && apt-get install -y \
    curl gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && node -v && npm -v \
    && rm -rf /var/lib/apt/lists/*

COPY . /app/
WORKDIR /app

RUN python3 -m venv /opt/venv

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
STRIPE_PRO_PRICE_ID=dummy\n\
BASE_URL=http://localhost:8000\n\
ENV_ALLOWED_HOSTS=localhost\n\
EMAIL_HOST=dummy\n\
EMAIL_PORT=587\n\
EMAIL_HOST_USER=dummy\n\
EMAIL_HOST_PASSWORD=dummy\n\
EMAIL_USE_TLS=True\n\
ADMIN_EMAIL=dummy@example.com\n\
AWS_ACCESS_KEY_ID=dummy\n\
AWS_SECRET_ACCESS_KEY=dummy" > .env

RUN /opt/venv/bin/pip install pip --upgrade && \
    /opt/venv/bin/pip install -r requirements.txt && \
    chmod +x entrypoint.sh

# Verify Node.js and npm installation
RUN which npm && which node

RUN /opt/venv/bin/python manage.py tailwind install && \
    cd theme/static_src && \
    npm install && \
    npx update-browserslist-db@latest && \
    npm run build:clean && \
    npm run build:tailwind && \
    cd ../.. && \
    /opt/venv/bin/python manage.py collectstatic --noinput --clear

# Remove temporary env file
RUN rm .env

CMD ["/app/entrypoint.sh"]