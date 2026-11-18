# PostgreSQL Setup (Windows)

Helix Agent uses **PostgreSQL** as its main database. SQLite is still available as a quick fallback
(used automatically when `DATABASE_URL` is not set).

Choose **one** way to install PostgreSQL.

---

## Option A — PostgreSQL installer (no Docker)

1. Download **PostgreSQL 16** for Windows from the official site: https://www.postgresql.org/download/windows/
2. Run the installer. Keep the defaults (port **5432**). Set a password for the `postgres` user and remember it.
   Tick **pgAdmin 4** (a visual tool) when asked.
3. Open **pgAdmin 4** (or **SQL Shell (psql)** from the Start menu) and log in as `postgres`.
4. Run this SQL once:
   ```sql
   CREATE USER helix WITH PASSWORD 'helix';
   CREATE DATABASE helix_kgit OWNER helix;
   CREATE DATABASE helix_test OWNER helix;
   ```
   (`helix/helix` is for local development only.)

## Option B — Docker Desktop

If Docker Desktop is installed, from the project folder:
```powershell
docker compose up -d
```
This starts PostgreSQL 16 on port 5432 with user `helix`, password `helix` and the databases
`helix_kgit` and `helix_test` (see `docker-compose.yml`).

---

## Run the API on PostgreSQL

In the VS Code terminal (PowerShell), inside the `helix-agent` folder with `(venv)` active:

```powershell
pip install -r requirements.txt          # installs psycopg (PostgreSQL driver)
$env:DATABASE_URL="postgresql://helix:helix@localhost:5432/helix_kgit"
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/health — it shows `"domain": "kgit"`.
On first start the app runs the migrations in `app/migrations/postgres/` and loads the 50 demo tickets and 30 FAQs.

> `$env:` settings last only for that terminal window. Open a new terminal → set it again.

## Run the tests on PostgreSQL
```powershell
$env:TEST_DATABASE_URL="postgresql://helix:helix@localhost:5432/helix_test"
python -m pytest -q
```
Each test uses a temporary schema that is deleted afterwards. Remove the variable to go back to SQLite:
```powershell
Remove-Item Env:TEST_DATABASE_URL
```

## Check the tables (optional)
In pgAdmin: **helix_kgit → Schemas → public → Tables** — you should see `tickets`, `faqs`, `ai_suggestions`,
`users`, `teams`, `categories`, `app_settings`, `schema_migrations`.

Or in psql:
```sql
\c helix_kgit
SELECT id, category, priority, team FROM tickets ORDER BY id LIMIT 5;
SELECT * FROM schema_migrations;
```

## Start again with fresh data
```sql
DROP DATABASE helix_kgit;
CREATE DATABASE helix_kgit OWNER helix;
```
Then restart the API — it re-creates the tables and loads the demo data.

## Troubleshooting
| Problem | Fix |
|---|---|
| `psycopg is not installed` | `pip install "psycopg[binary]"` with `(venv)` active |
| `connection refused` | PostgreSQL is not running — start the "postgresql-x64-16" service (Windows Services) or `docker compose up -d` |
| `password authentication failed` | Check the user/password in `DATABASE_URL` |
| `database "helix_kgit" does not exist` | Run the `CREATE DATABASE` commands above |
| `This database holds '...' data but HELIX_DOMAIN is 'kgit'` | The database was used for different data — use a fresh database |
