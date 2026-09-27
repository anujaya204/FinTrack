# FinTrack

FinTrack is a Django web application for recording, reviewing, and analyzing personal income and expenses. It provides authenticated user accounts, transaction management, dashboard summaries, and searchable transaction history, with SQLite for simple local development and PostgreSQL support through `DATABASE_URL`.

## Features

- User sign-up, login, and logout
- Dashboard showing total income, total expenses, and balance
- Income-versus-expenses chart and expense-by-category chart
- Add, edit, and delete transactions
- Transaction fields for amount, type, category, date, and description
- Transaction type filtering for all, income, or expenses
- Search by category, transaction type, or description
- Paginated transaction history
- Django admin access for the `Transaction` model
- Per-user transaction isolation
- CSRF protection for state-changing requests
- Static asset handling with WhiteNoise

## Tech Stack

- Python (3.13 in GitHub Actions CI)
- Django 6.1.1
- SQLite for the default local database
- PostgreSQL through `DATABASE_URL`
- `psycopg[binary]` and `dj-database-url` for PostgreSQL connectivity
- Django templates and custom CSS
- Chart.js 4.4.4 for dashboard charts
- WhiteNoise for compressed static files
- Gunicorn for a production WSGI server
- Docker and Docker Compose
- GitHub Actions for continuous integration

## Architecture

FinTrack follows Django's standard project and application structure:

1. Requests enter through `config/urls.py`, which routes authentication, dashboard, transaction, and admin URLs.
2. Views in `finance/views.py` enforce login requirements, query user-owned transactions, calculate dashboard totals, and render templates.
3. `TransactionForm` validates transaction input before records are saved.
4. The `Transaction` model stores income and expense records linked to Django's built-in `User` model.
5. Django templates render the user interface, while `finance/static/finance/style.css` provides the application styling.
6. The dashboard supplies JSON data to Chart.js for its two analytics charts.
7. Django uses SQLite when `DATABASE_URL` is absent and PostgreSQL when it is present.
8. In Docker Compose, the web container runs Django and the database container runs PostgreSQL.

## Screenshots

Screenshots can be added later in this section. Suggested captures:

| View | Placeholder |
| --- | --- |
| Dashboard | `![FinTrack dashboard](docs/screenshots/dashboard.png)` |
| All transactions | `![All transactions](docs/screenshots/all-transactions.png)` |
| Add transaction | `![Add transaction form](docs/screenshots/add-transaction.png)` |
| Login | `![Login page](docs/screenshots/login.png)` |

The image paths above are placeholders and are not currently included in the repository.

## Local Setup

### Prerequisites

- Python 3.13
- Git
- Optional: Docker Desktop for the containerized setup

### Install and run with SQLite

```powershell
git clone <repository-url>
cd FinTrack
py -3.13 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and replace the `SECRET_KEY` placeholder with a local development secret. Leave `DATABASE_URL` unset to use the existing SQLite fallback. `DEBUG=True` may be used for local debugging; it defaults to `False`.

Run migrations and start Django:

```powershell
python manage.py migrate
python manage.py runserver
```

Open <http://127.0.0.1:8000/> in a browser. Create an account at `/signup/`, or create an admin account with:

```powershell
python manage.py createsuperuser
```

## Docker Setup

Docker Compose runs the Django web service and PostgreSQL together.

1. Copy the safe environment template:

   ```powershell
   Copy-Item .env.example .env.docker.local
   ```

2. Replace the placeholder `SECRET_KEY`, `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` values in `.env.docker.local`. Do not commit this file.
3. Build and start both services:

   ```powershell
   docker compose --env-file .env.docker.local up --build
   ```

The web service is available at <http://127.0.0.1:8000/>. The container runs migrations before starting Django's development server. Stop the services with:

```powershell
docker compose --env-file .env.docker.local down
```

The PostgreSQL data is stored in the Compose-managed `postgres_data` volume.

## PostgreSQL Support

When `DATABASE_URL` is set, `config/settings.py` configures Django to use PostgreSQL through `dj-database-url`. When it is not set, FinTrack uses `db.sqlite3`.

Docker Compose constructs the PostgreSQL connection URL from the database values in `.env.docker.local` and passes it to the web container. For a non-Docker PostgreSQL setup, configure `DATABASE_URL` directly without committing its value.

## Testing

The repository contains 17 automated Django tests. They cover authentication requirements, transaction CRUD operations, validation, user isolation, filtering, searching, pagination, dashboard analytics, CSRF enforcement, localization-sensitive rendering, and safe handling of user-provided values.

Run the checks locally with:

```powershell
python manage.py check
python manage.py test
```

## GitHub Actions CI

The workflow in `.github/workflows/ci.yml` runs on pushes and pull requests targeting `main`. It:

- Runs on Ubuntu
- Uses Python 3.13
- Installs `requirements.txt`
- Runs `python manage.py check`
- Runs `python manage.py test`

The CI workflow uses a CI-only secret value supplied through the workflow environment and does not require local private environment files.

## Environment Variables

Use `.env.example` as the safe template. Keep `.env` and `.env.docker.local` private; both are excluded from version control.

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Django secret key; keep it private and use a unique value outside local development. |
| `DEBUG` | Enables Django debug mode only when explicitly set to a truthy value; defaults to `False`. |
| `ALLOWED_HOSTS` | Comma-separated hostnames accepted by Django. |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated HTTPS origins trusted for CSRF-protected requests. |
| `DATABASE_URL` | Optional PostgreSQL connection URL. When absent, SQLite is used. |
| `POSTGRES_DB` | PostgreSQL database name used by Docker Compose. |
| `POSTGRES_USER` | PostgreSQL username used by Docker Compose. |
| `POSTGRES_PASSWORD` | PostgreSQL password used by Docker Compose. |

The Compose file builds `DATABASE_URL` from the three `POSTGRES_*` variables, so `DATABASE_URL` should not be added to `.env.docker.local` for the provided Docker setup.

## Security Practices

- Secrets are read from environment variables rather than stored in application code.
- `.env` and `.env.docker.local` are ignored by Git.
- Production `DEBUG` is disabled by default.
- Allowed hosts and trusted CSRF origins are configurable per environment.
- Django authentication and password validation are enabled.
- Transaction queries are scoped to the authenticated user.
- Edit and delete operations only resolve transactions owned by the current user.
- State-changing forms include CSRF protection.
- Production static files are served through WhiteNoise.

## Project Structure

```text
FinTrack/
|-- config/
|   |-- settings.py       # Django settings and database/static configuration
|   |-- urls.py           # Root URL routing
|   |-- asgi.py           # ASGI entry point
|   `-- wsgi.py           # WSGI entry point
|-- finance/
|   |-- migrations/       # Database migrations
|   |-- static/           # Finance application CSS
|   |-- templates/        # Dashboard, transaction, and authentication templates
|   |-- forms.py          # Transaction validation form
|   |-- models.py         # Transaction model
|   |-- views.py          # Authentication and transaction views
|   `-- tests.py          # Automated tests
|-- .env.example          # Safe environment variable template
|-- compose.yaml           # Django and PostgreSQL services
|-- Dockerfile             # Django container image
|-- manage.py              # Django management entry point
`-- requirements.txt       # Python dependencies
```

## Future Improvements

Potential future improvements include:

- Add deployment-specific health checks and operational monitoring.
- Add more detailed reporting and configurable date-range analytics.
- Add export options for transaction data.
- Add broader automated coverage for production deployment configuration.
- Add a dedicated production settings configuration if deployment needs diverge further from local settings.

## Author

**Tharindi Anuththara**  
Software Engineering Undergraduate  
NSBM Green University, Sri Lanka
