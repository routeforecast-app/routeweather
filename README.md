# RouteWeather

RouteWeather is a production-minded MVP for uploading GPX routes, sampling estimated positions over time, fetching forecast weather for those points, and visualizing the result on a responsive map and timeline. The repo is organized as an API-first FastAPI backend plus a fully separate React/Vite frontend so it can run locally now, deploy cleanly later, and be wrapped in a native shell app if needed.

## Stack

- Backend: FastAPI, SQLModel, SQLite, JWT auth, Passlib password hashing
- Frontend: React, Vite, React Router, Leaflet
- Weather provider: Open-Meteo hourly forecast API
- PWA: manifest + service worker

## Project Structure

```text
routeweather/
  backend/
    app/
    tests/
    requirements.txt
    .env.example
  frontend/
    src/
    public/
    package.json
    vite.config.js
  README.md
```

## Features Included

- Email/password registration and login
- Password hashing with bcrypt via Passlib
- JWT bearer authentication
- GPX upload and parsing
- Route distance calculation and interpolation-based sampling
- Weather matching for each sampled point at the estimated arrival time
- Start/end plus user-selected key points with rolling 24-hour hourly forecasts
- Saved routes per user
- Responsive desktop/mobile layout
- Installable PWA shell with basic offline caching for app assets and previously visited pages

## Backend Setup

Run these commands from [backend](C:\Users\User\Documents\Rout wether planner\routeweather\backend):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Update `.env` and set a real `SECRET_KEY` before using anything beyond local development.

Start the backend dev server:

```powershell
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend API docs will be available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

## Frontend Setup

Run these commands from [frontend](C:\Users\User\Documents\Rout wether planner\routeweather\frontend):

```powershell
npm install
Copy-Item .env.example .env
npm run dev
```

The Vite dev server runs on [http://127.0.0.1:5173](http://127.0.0.1:5173) and proxies `/api` requests to the FastAPI backend.

## Local Run Order

1. Start the backend on `127.0.0.1:8000`.
2. Start the frontend on `127.0.0.1:5173`.
3. Open the frontend in a desktop or mobile browser.
4. Register a new account and upload a `.gpx` file.

## Windows Launcher

From the main folder one level above this repo, you can use:

- [Run-RouteWeather.bat](C:\Users\User\Documents\Rout wether planner\Run-RouteWeather.bat) to start the backend and, when `npm` is installed, the frontend too
- [RouteWeather App.url](C:\Users\User\Documents\Rout wether planner\RouteWeather App.url) to open the frontend URL
- [RouteWeather API Docs.url](C:\Users\User\Documents\Rout wether planner\RouteWeather API Docs.url) to open the backend docs URL
- [Reset-RouteWeather-Password.bat](C:\Users\User\Documents\Rout wether planner\Reset-RouteWeather-Password.bat) to reset a local account password directly in the development database

If Node.js/npm is not installed, the launcher still starts the backend and opens the API docs.

## How To Create A Test User

Use the Register page in the frontend, or send a request directly:

```http
POST /auth/register
{
  "email": "demo@example.com",
  "password": "supersecure123"
}
```

## How To Use The App

1. Register or log in.
2. Open the Upload Route page.
3. Enter a route name, planned start time, average speed, and sampling interval.
4. Upload a GPX file.
5. Review the saved route detail page:
   - The route polyline appears on the Leaflet map.
   - Sampled points show estimated arrival times and matched weather.
   - The timeline panel gives a quick route-wide view.
   - Key points show a rolling 24-hour hourly forecast.
6. Click any sampled point and use "Use this point for 24-hour forecast" to add it as a key point.

## Testing

Run backend tests from [backend](C:\Users\User\Documents\Rout wether planner\routeweather\backend):

```powershell
.venv\Scripts\Activate.ps1
pytest
```

Included tests currently cover:

- auth register/login flow
- route GPX parsing
- route sampling and GeoJSON generation

## Local Password Recovery

If a local account can no longer sign in and email-based password reset is not enabled yet, use the
password reset launcher in the main folder:

```powershell
.\Reset-RouteWeather-Password.bat
```

Or run the backend helper directly from [backend](C:\Users\User\Documents\Rout wether planner\routeweather\backend):

```powershell
.venv\Scripts\python.exe reset_local_account_password.py --email jack.s.steele2007@icloud.com
```

Administrator accounts must still use a strong password:

- at least 8 characters
- at least 1 uppercase letter
- at least 1 number
- at least 1 symbol

## Important Implementation Notes

- Most route-processing logic lives in the backend so the frontend stays thin.
- Saved route geometry and forecast payloads are persisted as JSON columns to keep the swap to Postgres straightforward later.
- Open-Meteo access is centralized in [weather_service.py](C:\Users\User\Documents\Rout wether planner\routeweather\backend\app\services\weather_service.py) so a future provider swap stays isolated.
- The frontend talks to the backend through a small API layer in [src/api](C:\Users\User\Documents\Rout wether planner\routeweather\frontend\src\api).
- The default frontend API base URL is relative (`/api`) so future deployment behind one domain is simpler, and wrapping the frontend in a native shell app stays straightforward.

## Switching SQLite To Postgres Later

The main touch points are intentionally small:

- Update `DATABASE_URL` in [backend/.env.example](C:\Users\User\Documents\Rout wether planner\routeweather\backend\.env.example).
- Install a Postgres driver such as `psycopg[binary]`.
- Keep the model layer in [models.py](C:\Users\User\Documents\Rout wether planner\routeweather\backend\app\models.py) and engine setup in [database.py](C:\Users\User\Documents\Rout wether planner\routeweather\backend\app\database.py) as the primary migration surface.
- Add Alembic or another migration tool once schema changes need structured migration history.

## Deployment Notes

For a later public deployment:

- Build the frontend with `npm run build`.
- Serve the frontend bundle from a CDN, static host, or reverse proxy.
- Run the FastAPI backend behind a production ASGI server and reverse proxy.
- Prefer one public origin so the frontend can keep using relative `/api` calls.
- Move the database to Postgres for concurrent multi-user workloads.
- Store uploaded GPX files in object storage instead of the local filesystem.
- Move long-running or refresh-style weather work into background jobs as usage grows.

For an Ubuntu VPS deployment, use:

- [deploy/ubuntu-ionos-vps.md](C:/Users/User/Documents/Rout%20wether%20planner/routeweather/deploy/ubuntu-ionos-vps.md)
- [deploy/systemd/routeforcast-backend.service](C:/Users/User/Documents/Rout%20wether%20planner/routeweather/deploy/systemd/routeforcast-backend.service)
- [deploy/nginx/routeforcast.conf](C:/Users/User/Documents/Rout%20wether%20planner/routeweather/deploy/nginx/routeforcast.conf)
- [backend/gunicorn.conf.py](C:/Users/User/Documents/Rout%20wether%20planner/routeweather/backend/gunicorn.conf.py)

## TODOs For Future Upgrades

- Refresh tokens
- Password reset
- Email verification
- Postgres migration
- Background jobs for weather refresh and precomputation
- Native mobile shell wrapper
- Push notifications
- Offline cached route packs

## Notable Files

- Backend entry: [main.py](C:\Users\User\Documents\Rout wether planner\routeweather\backend\app\main.py)
- Auth API: [auth router](C:\Users\User\Documents\Rout wether planner\routeweather\backend\app\routers\auth.py)
- Route API: [routes router](C:\Users\User\Documents\Rout wether planner\routeweather\backend\app\routers\routes.py)
- GPX parsing: [gpx_service.py](C:\Users\User\Documents\Rout wether planner\routeweather\backend\app\services\gpx_service.py)
- Sampling logic: [route_sampling_service.py](C:\Users\User\Documents\Rout wether planner\routeweather\backend\app\services\route_sampling_service.py)
- Weather integration: [weather_service.py](C:\Users\User\Documents\Rout wether planner\routeweather\backend\app\services\weather_service.py)
- Frontend routes/app shell: [App.jsx](C:\Users\User\Documents\Rout wether planner\routeweather\frontend\src\App.jsx)
- Route detail page: [RouteDetailPage.jsx](C:\Users\User\Documents\Rout wether planner\routeweather\frontend\src\pages\RouteDetailPage.jsx)
