# GCIR Grant Management System (GCIR-GMS)

A Django-based digital grant management system for GCIR division office staff.

**Status:** 🚀 In Development  
**Target:** Easy-to-use grant tracking for handful of office staff users

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Development Setup](#development-setup)
3. [Project Structure](#project-structure)
4. [Development Progress](#development-progress)
5. [Useful Commands](#useful-commands)

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

```
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
- Django Official Docs: https://docs.djangoproject.com/
- Project SPECIFICATION.md for architecture details
- Development Roadmap for step-by-step guidance
