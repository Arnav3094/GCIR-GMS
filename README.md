# GCIR Grant Management System (GCIR-GMS)

A Django-based digital grant management system for GCIR division office staff.

**Status:** 🚀 In Development  
**Target:** Easy-to-use grant tracking for handful of office staff users

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Development Setup](#development-setup)
3. [Project Structure](#project-structure)
4. [Useful Commands](#useful-commands)
5. [Development Notes](#development-notes)
6. [Documentation](#documentation)
7. [Next Steps](#next-steps)
8. [License](#license)

---

## Quick Start

This project uses Django 4.2 LTS with SQLite database. No complex infrastructure needed.

---

## Development Setup

### Prerequisites

- Python 3.11+ installed
- Git installed
- Terminal/Command line access

### Step 1: Clone Repository

```bash
git clone https://github.com/Arnav3094/GCIR-GMS.git
cd GCIR-GMS
```

### Step 2: Install Dependencies with Pipenv

[Pipenv](https://pipenv.pypa.io/) manages both the virtual environment and dependencies:

```bash
# Install Pipenv (if not already installed)
pip install pipenv

# Install dependencies from Pipfile (creates virtual environment automatically)
pipenv install

# Verify Django installed
pipenv run django-admin --version
```

**Note:** Pipenv automatically creates and manages a virtual environment for this project.

### Step 3: Activate Pipenv Shell

To activate the Pipenv virtual environment:

```bash
# Activate Pipenv shell
pipenv shell

# You should see the project name in your terminal line
# Example: (GCIR-GMS-abc123) $
```

To exit: `exit`


## Current Setup Status

- [x] **Step 1:** Clone repository
- [x] **Step 2:** Install dependencies with Pipenv
- [x] **Step 3:** Activate Pipenv shell
- [x] **Step 4:** Create Django project & app
- [ ] **Step 5:** Configure Django settings
- [ ] **Step 6:** Create data models
- [ ] **Step 7:** Create superuser & test admin
- [ ] **Step 8:** Build custom views & forms
- [ ] **Step 9:** Add audit trail & reports
- [ ] **Step 10:** Deploy to production

---

## Project Structure

```txt
GCIR-GMS/
├── README.md                          # This file
├── REQUIREMENTS.md                    # Original requirements documentation
├── SPECIFICATION.md                   # Technical specification
├── Pipfile                            # Pipenv dependencies
├── Pipfile.lock                       # Locked dependency versions
├── manage.py                          # Django CLI tool
├── .env (gitignored)                  # Environment variables
├── db.sqlite3 (gitignored)            # Database file
│
├── gms_project/                       # Django project folder
│   ├── settings.py                    # Configuration
│   ├── urls.py                        # Main URL routing
│   └── wsgi.py                        # Production WSGI app
|   
│
└── proposals/                         # Main Django app
    ├── models.py                      # Database schemas
    ├── views.py                       # Request handlers
    ├── forms.py                       # Form definitions
    ├── urls.py                        # App URL routing
    ├── admin.py                       # Admin customization
    ├── services.py                    # Helper functions
    ├── migrations/                    # Database migrations
    └── templates/proposals/           # HTML templates
        ├── list.html
        ├── detail.html
        ├── form.html
        └── reports.html
```

---

## Useful Commands

### Working with Pipenv

```bash
# Install dependencies
pipenv install

# Activate Pipenv shell
pipenv shell

# Exit Pipenv shell
exit

# Run commands without activating shell
pipenv run python manage.py runserver

# Show installed packages
pipenv graph
```

### Development Server

```bash
# Start development server (http://localhost:8000)
pipenv run python manage.py runserver

# Start on different port
pipenv run python manage.py runserver 8001
```

### Database Migrations

```bash
# Create migrations after changing models
pipenv run python manage.py makemigrations

# Apply migrations
pipenv run python manage.py migrate

# View migration SQL
pipenv run python manage.py sqlmigrate proposals 0001
```

### Database & initial data

The repository includes an auto-generated migration `proposals/migrations/0001_initial.py` which describes the initial schema for the `proposals` app (tables like `Proposal`, `Department`, `Investigator`, plus the historical `HistoricalProposal` table created by `django-simple-history`). This is the canonical representation of the schema — run `migrate` to apply it to your local database.

How to get a working local database quickly

- Option A — Create a fresh local DB by running migrations (recommended for development):

```bash
# Activate pipenv shell if not already
pipenv shell

# Apply all migrations (creates a fresh db.sqlite3 in the project root)
python manage.py migrate

# (Optional) Create a superuser for admin access
python manage.py createsuperuser

# Start the development server and login at http://127.0.0.1:8000/admin
python manage.py runserver
```

- Option B — Use a provided `db.sqlite3` snapshot (if you received one):

1. Place `db.sqlite3` at the project root (same level as `manage.py`).
2. If you have migrations in the repo that match the snapshot, Django should detect the applied migrations; run `python manage.py showmigrations` to confirm.
3. If migrations differ, prefer Option A or ask the teammate who provided the snapshot for the matching migration files.

Using fixtures for initial data

If the project exposes fixtures (JSON/YAML/fixtures/) you can load them after migrating:

```bash
python manage.py loaddata initial_departments.json
python manage.py loaddata initial_projecttypes.json
```

Inspecting migrations and SQL

To inspect the SQL emitted by a migration (useful for review or debugging):

```bash
python manage.py sqlmigrate proposals 0001
```

Rolling back migrations (development only)

To revert the `proposals` app to zero (drop tables) — only do this on a disposable local DB:

```bash
python manage.py migrate proposals zero
```

Notes & gotchas

- The `0001_initial.py` migration also creates the `HistoricalProposal` table used by `django-simple-history`. This table is expected and required for audit trail functionality.
- Keep migration files under version control — they document schema history and are how other developers will reproduce your database schema.
- If you switch between using a snapshot `db.sqlite3` and regenerating via migrations, ensure migrations and the snapshot are aligned to avoid inconsistencies.


### Admin & Users

```bash
# Create superuser (admin account)
pipenv run python manage.py createsuperuser

# Access Django shell
pipenv run python manage.py shell
```

### Adding/Removing Packages

```bash
# Add a new package
pipenv install package-name

# Add a dev-only package
pipenv install --dev package-name

# Remove a package
pipenv uninstall package-name

# Update all packages
pipenv update
```

---

## Development Notes

- **Dependency Management:** Pipenv (Pipfile & Pipfile.lock manage all dependencies)
- **Database:** SQLite (db.sqlite3) - no separate database server needed
- **Frontend:** Django Templates + Bootstrap 5
- **Audit Trail:** django-simple-history automatically tracks all changes
- **GCIR Code:** Auto-generated format: `G-{year}-{department}-{type}-{serial}`

---

## Documentation

- **[REQUIREMENTS.md](REQUIREMENTS.md)** - Original functional & business requirements
- **[SPECIFICATION.md](SPECIFICATION.md)** - Technical specification & architecture
- **[Development Roadmap](ROADMAP.md)** - Step-by-step development guide *(coming soon)*

---

## Next Steps

1. Make sure you've completed all **Development Setup** steps above
2. Verify Django is working: `django-admin --version`
3. Check your requirements are installed: `pip list | grep Django`
4. Ready to start coding!

For detailed development roadmap, see **SPECIFICATION.md** Section 10 (Quick Reference & Roadmap).

---

## License

See [LICENSE](LICENSE) file for details.

---

## Questions?

Refer to:

- Django Official Docs: <https://docs.djangoproject.com/>
- Project SPECIFICATION.md for architecture details
