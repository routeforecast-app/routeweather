# RouteForcast Ubuntu VPS Deployment

This guide assumes:

- Ubuntu on an IONOS VPS
- one domain or subdomain pointed at the VPS
- the repo will live in `/var/www/routeforcast/current`
- the Python virtual environment will live in `/var/www/routeforcast/venv`

## 1. Point DNS to the VPS

In IONOS DNS, create or update:

- `A` record for `routeforcast.co.uk` -> your VPS IPv4 address
- optional `A` record for `www.routeforcast.co.uk` -> same IPv4 address
- optional `AAAA` records if your VPS has IPv6 enabled

Wait until DNS resolves to the VPS before doing HTTPS setup.

## 2. Install system packages

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx certbot python3-certbot-nginx nodejs npm git
```

If you want a newer Node.js version than Ubuntu ships by default, install Node 20 LTS from NodeSource before running `npm install`.

## 3. Create the app directories

```bash
sudo mkdir -p /var/www/routeforcast/current
sudo mkdir -p /var/www/routeforcast/shared
sudo chown -R $USER:$USER /var/www/routeforcast
```

## 4. Upload the project

Either:

- `git clone` the repo into `/var/www/routeforcast/current`, or
- upload the project from your local machine with `scp` or SFTP

Example with git:

```bash
cd /var/www/routeforcast
git clone <your-repo-url> current
```

## 5. Set up the backend virtual environment

```bash
cd /var/www/routeforcast/current/backend
python3 -m venv /var/www/routeforcast/venv
/var/www/routeforcast/venv/bin/pip install --upgrade pip
/var/www/routeforcast/venv/bin/pip install -r requirements.txt
```

## 6. Create the production backend env file

Create `/var/www/routeforcast/shared/backend.env`:

```bash
cp /var/www/routeforcast/current/deploy/backend.env.routeforcast.example /var/www/routeforcast/shared/backend.env
nano /var/www/routeforcast/shared/backend.env
```

Recommended starting content:

```env
SECRET_KEY=replace-with-a-long-random-secret
DATABASE_URL=sqlite:///./routeweather.db
ACCESS_TOKEN_EXPIRE_MINUTES=720
CORS_ORIGINS=["https://routeforcast.co.uk","https://www.routeforcast.co.uk"]
FRONTEND_APP_URL=https://routeforcast.co.uk
EMAIL_OUTBOX_DIR=./app/static_uploads/email_outbox
EMAIL_DELIVERY_MODE=sendgrid
SENDGRID_API_KEY=your-sendgrid-api-key
SENDGRID_FROM_EMAIL=no-reply@routeforcast.co.uk
SENDGRID_FROM_NAME=RouteForcast
SENDGRID_REPLY_TO_EMAIL=support@routeforcast.co.uk
SENDGRID_DATA_RESIDENCY=eu
OPEN_METEO_BASE_URL=https://api.open-meteo.com/v1/forecast
WEATHER_CACHE_TTL_MINUTES=30
GUNICORN_BIND=127.0.0.1:8000
GUNICORN_WORKERS=2
GUNICORN_TIMEOUT=120
```

Use your real SendGrid API key only in `/var/www/routeforcast/shared/backend.env` on the VPS.
Do not commit it into the repo.

Generate a strong secret key with:

```bash
python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(64))
PY
```

## 7. Build the frontend

```bash
cd /var/www/routeforcast/current/frontend
npm install
npm run build
```

The frontend already uses relative `/api` calls in production, which is ideal for one-domain VPS hosting.

## 8. Install the systemd service

Copy the template:

```bash
sudo cp /var/www/routeforcast/current/deploy/systemd/routeforcast-backend.service /etc/systemd/system/
```

If you want to run it as your own Linux user instead of `www-data`, edit:

```bash
sudo nano /etc/systemd/system/routeforcast-backend.service
```

Then enable it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable routeforcast-backend
sudo systemctl start routeforcast-backend
sudo systemctl status routeforcast-backend
```

Useful logs:

```bash
sudo journalctl -u routeforcast-backend -f
```

## 9. Install the nginx site

Copy the nginx template:

```bash
sudo cp /var/www/routeforcast/current/deploy/nginx/routeforcast.conf /etc/nginx/sites-available/routeforcast
```

Edit the domain names:

```bash
sudo nano /etc/nginx/sites-available/routeforcast
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/routeforcast /etc/nginx/sites-enabled/routeforcast
sudo nginx -t
sudo systemctl reload nginx
```

## 10. Open the firewall

If `ufw` is enabled:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

## 11. Enable HTTPS with Let's Encrypt

Once DNS is pointing at the VPS and nginx is serving the site:

```bash
sudo certbot --nginx -d routeforcast.co.uk -d www.routeforcast.co.uk
```

Choose the redirect-to-HTTPS option when prompted.

## 12. Validate the deployment

Check:

- `https://routeforcast.co.uk` loads the frontend
- `https://routeforcast.co.uk/api/docs` loads the backend API docs
- `https://routeforcast.co.uk/api/health` returns `{"status":"ok"}`
- route uploads work
- saved routes reload correctly
- PWA install prompt appears in supported browsers

## 13. Updating the app later

```bash
cd /var/www/routeforcast/current
git pull

cd /var/www/routeforcast/current/backend
/var/www/routeforcast/venv/bin/pip install -r requirements.txt

cd /var/www/routeforcast/current/frontend
npm install
npm run build

sudo systemctl restart routeforcast-backend
sudo systemctl reload nginx
```

## Notes

- SQLite is okay for a first public deployment with light traffic, but Postgres is the next thing I'd move to once usage grows.
- Uploaded GPX files are currently stored on the VPS filesystem, so make regular backups.
- SendGrid is now supported directly by the backend. Leave `EMAIL_DELIVERY_MODE=auto` for local development fallback, or set `EMAIL_DELIVERY_MODE=sendgrid` in production once your sender identity is verified.
