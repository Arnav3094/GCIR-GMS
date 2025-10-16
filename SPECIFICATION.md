# GCIR-GMS: Development & Deployment Specification

**Version:** 1.0 | **Date:** October 16, 2025

---

## 1. Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Backend** | Django 4.2 LTS | Built-in admin, ORM, security |
| **Frontend** | Django Templates + Bootstrap 5 | Server-side rendering, no build process |
| **Database** | SQLite | Zero setup, single file, suitable for <50 users |
| **Deployment** | Gunicorn + Nginx (or platform-specific) | Lightweight, reliable |
| **Hosting** | *TBD - Multiple Options Available* | See Deployment Options (Section 8) |
| **Audit Trail** | django-simple-history | AR1-AR4 requirements with minimal code |

---

## System Architecture

```text
┌───────────────────────────────────────────────────────┐
│                  GCIR STAFF USERS                     │
│                                                       │
└──────────────────────────┬────────────────────────────┘
                           │
                    HTTP Requests
                           │
┌──────────────────────────▼───────────────────────────────────┐
│                    WEB BROWSER                               │
│  - Django Admin (/admin) - Main interface for GCIR staff     │
│  - Custom Pages (/proposals) - List, create, edit proposals  │
│  - Reports (/reports) - Weekly changelog                     │
└──────────────────────────┬───────────────────────────────────┘
                           │
         ┌─────────────────▼─────────────────┐
         │     DJANGO BACKEND (Python)       │
         │                                   │
         │  - URL Router (urls.py)           │
         │  - Views (views.py)               │
         │  - Business Logic (services.py)   │
         │  - Forms (forms.py)               │
         │                                   │
         └─────────────────┬─────────────────┘
                           │
         ┌─────────────────▼─────────────────┐
         │    DATABASE (SQLite)              │
         │                                   │
         │  - Proposals & Data               │
         │  - Audit History                  │
         │    (via django-simple-history)    │
         │                                   │
         └───────────────────────────────────┘

Deployment: Gunicorn (app server) + Nginx (reverse proxy) on various platforms
            (Options: DigitalOcean, Heroku, Raspberry Pi, self-hosted VPS, etc.)
```

---

## 2. Project Structure & File Purposes

```text
GCIR-GMS/
├── manage.py                           # Django CLI tool
├── Pipfile                             # Pipenv dependencies
├── Pipfile.lock                        # Locked dependency versions
├── .env (gitignored)                   # Environment variables (SECRET_KEY, DEBUG, etc.)
├── db.sqlite3 (gitignored)             # Database file
├── gms_project/                        # Django project folder
│   ├── settings.py                     # Configuration (DB, apps, security)
│   ├── urls.py                         # Main URL routing
│   └── wsgi.py                         # Production WSGI app
├── proposals/                          # Main Django app
│   ├── models.py                       # Database schemas
│   ├── views.py                        # Request handlers & business logic
│   ├── forms.py                        # HTML form definitions
│   ├── urls.py                         # App-level URL routing
│   ├── admin.py                        # Django admin customization
│   ├── services.py                     # Helper functions (GCIR code generation)
│   ├── migrations/                     # Auto-generated database migration files
│   └── templates/proposals/            # HTML templates
│       ├── list.html                   # Proposal listing page
│       ├── detail.html                 # Single proposal view/edit page
│       ├── form.html                   # Create/edit form
│       └── reports.html                # Weekly changelog report
└── static/
    └── css/style.css                   # Styling
```

### File Responsibilities

| File | Purpose | Key Tasks |
|------|---------|-----------|
| `models.py` | Define database tables | Store Proposal, Investigator, Department data |
| `views.py` | Handle HTTP requests | Display lists, create/edit proposals, generate reports |
| `forms.py` | Define HTML forms | Validate user input before saving to DB |
| `admin.py` | Customize Django admin | Enable GCIR staff to manage data via /admin |
| `services.py` | Business logic helpers | Generate unique GCIR codes |
| `urls.py` | Route URLs to views | Map `/proposals/` to correct view functions |
| Templates | Render HTML pages | Display proposals to users |
| `settings.py` | App configuration | Database settings, installed apps, security |

---

## 3. Dependencies (Pipenv)

Dependencies are managed using **Pipenv** via `Pipfile`:

```txt
Django==4.2.7
django-simple-history==3.4.0
python-decouple==3.8
gunicorn==21.2.0
pillow==10.1.0
```

To install:

```bash
pipenv install
pipenv shell
```

The `Pipfile.lock` ensures reproducible dependency versions across environments.

---

## 4. Data Model Overview

### Entity Relationship Diagram

```text
┌─────────────────┐         ┌──────────────────┐
│  Investigator   │         │  Department      │
│  (PSRN - PK)    │◄────────┤  (DeptID - PK)   │
│  - name         │         │  - code (CS)     │
│  - email        │         │  - name          │
└────────┬────────┘         └──────────────────┘
         │
         │ 1:M (PI)
         │
    ┌────▼────────────────────────────────────┐
    │     Proposal (GCIR_Code - PK)           │
    │  - title, status, dates, costs          │
    │  - sanction_letter_number               │
    │  - final_sanctioned_cost                │
    │  - history (tracked by django-history)  │
    └────┬────────────────────────────────────┘
         │ 1:M
         │
    ┌────▼─────────────────────┐
    │ ProposalInvestigator     │
    │  - role (PI / Co-PI)     │
    └──────────────────────────┘

Also includes:
- ProjectType (IND, GOV, etc.)
- FundingAgency
- ProposalDocument (file uploads)
```

### Model Summary

| Model | Primary Key | Key Fields | Purpose |
|-------|-------------|-----------|---------|
| **Proposal** | GCIR_Code (auto-generated) | title, status, dates, costs | Core proposal record |
| **Investigator** | PSRN | name, email, department | Faculty/PI data |
| **ProposalInvestigator** | (proposal, investigator) | role (PI/Co-PI) | Links PIs to proposals |
| **Department** | DeptID | code (CS), name | Lookup table |
| **ProjectType** | TypeID | code (IND), name | Lookup table |
| **FundingAgency** | AgencyID | name | Lookup table |
| **ProposalDocument** | DocID | file, document_type | File storage |

### Status Workflow

```text
DRAFT → PERMISSION → SUBMITTED → REVIEW → APPROVED → DISBURSED
                                   ↓
                              REJECTED (terminal)
```

### GCIR Code Format

```text
G - 2025 - CS - IND - 0001
│    │     │   │     │
│    │     │   │     └─ Serial number (0001, 0002...) (4 digit, zero-padded)
│    │     │   └─────── Project Type (from lookup)
│    │     └─────────── Department Code (from lookup)
│    └───────────────── Academic/Financial Year
└────────────────────── Campus (G = Goa)

---
```

## 5. GCIR Code Generation Logic

### How GCIR Code is Generated

When GCIR staff creates a proposal:

1. **Select Department & Project Type** (via form)
2. **System automatically generates unique code** (FR2)
3. **Code format:** `G-{year}-{dept_code}-{type_code}-{serial}`

### Example Sequence

```text
First CS (Computer Science) + IND (Industry) proposal in 2025:
G-2025-CS-IND-001

Second CS + IND proposal in 2025:
G-2025-CS-IND-002

First ME (Mechanical) + GOV (Government) proposal in 2025:
G-2025-ME-GOV-001
```text

### Implementation

```python
# proposals/services.py

def generate_gcir_code(project_type_id, department_id, year=None):
    """Auto-generate unique GCIR code when proposal is created"""
    if year is None:
        year = datetime.now().year
    
    # Fetch lookups
    project_type = ProjectType.objects.get(id=project_type_id)
    department = Department.objects.get(id=department_id)
    
    # Find next serial number
    pattern = f"G-{year}-{department.code}-{project_type.code}-"
    existing_codes = Proposal.objects.filter(gcir_code__startswith=pattern)
    
    if existing_codes.exists():
        last_serial = max([int(code.split('-')[-1]) for code in existing_codes])
        next_serial = last_serial + 1
    else:
        next_serial = 1
    
    return f"{pattern}{next_serial:03d}"
```

### Where It's Called

- `proposal_create()` view: Automatically generates code before saving
- Code is **read-only** after creation (cannot be changed)

---

## 6. Request Flow & Views

### How User Requests Flow Through Django

```txt
User clicks link/submits form
        ↓
URL Router (urls.py)
        ↓
View Function (views.py)
        ↓
Query Database (models.py)
        ↓
Render Template (HTML)
        ↓
Return to User
```

### Core Views Needed

| View Function | URL | Purpose | Returns |
|---------------|-----|---------|---------|
| `proposal_list` | `/proposals/` | Display all proposals with search | HTML list page |
| `proposal_create` | `/proposals/new/` | Form to create proposal, auto-generates GCIR code | Redirect to detail |
| `proposal_detail` | `/proposals/<gcir_code>/` | View/edit single proposal, update status | HTML detail page |
| `changelog_report` | `/reports/changelog/` | Weekly changes (FR5 audit trail) | HTML report |

### Code Example (Simplified)

```python
# proposals/views.py - Key patterns

@login_required
def proposal_list(request):
    # Filter by search query if provided
    proposals = Proposal.objects.all()
    if search := request.GET.get('q'):
        proposals = proposals.filter(title__icontains=search)
    return render(request, 'proposals/list.html', {'proposals': proposals})

@login_required
def proposal_create(request):
    if request.method == 'POST':
        form = ProposalForm(request.POST)
        if form.is_valid():
            proposal = form.save(commit=False)
            # Auto-generate code before saving
            proposal.gcir_code = generate_gcir_code(...)
            proposal.save()
            return redirect('proposal_detail', pk=proposal.gcir_code)
    return render(request, 'proposals/form.html', {'form': ProposalForm()})

@login_required
def proposal_detail(request, pk):
    proposal = get_object_or_404(Proposal, gcir_code=pk)
    # Handle both GET (display) and POST (update)
    if request.method == 'POST':
        form = ProposalForm(request.POST, instance=proposal)
        if form.is_valid():
            form.save()  # Records history automatically
            return redirect('proposal_detail', pk=proposal.gcir_code)
    else:
        form = ProposalForm(instance=proposal)
    return render(request, 'proposals/detail.html', {'proposal': proposal, 'form': form})
```

---

## 7. Admin Interface

### Why Django Admin?

The Django admin at `/admin/` provides:

- ✅ Search, filter, and sort proposals
- ✅ Create/edit/delete records without coding
- ✅ Automatic audit trail display (via django-simple-history)
- ✅ User permission controls
- ✅ 80% of GCIR staff needs covered with 0 custom UI code

### Admin Configuration

```python
# proposals/admin.py - Key customizations

@admin.register(Proposal)
class ProposalAdmin(SimpleHistoryAdmin):
    list_display = ('gcir_code', 'title', 'pi', 'status', 'application_date')
    list_filter = ('status', 'project_type', 'department')  # Sidebar filters
    search_fields = ('gcir_code', 'title', 'pi__name')       # Search bar
    readonly_fields = ('gcir_code', 'created_at', 'updated_at')  # Can't edit
    # SimpleHistoryAdmin automatically shows change history tab
```

### Admin Features Provided

| Feature | What It Does |
|---------|------------|
| **List View** | Shows all proposals in a table with filters and search |
| **Change/Edit** | Click any proposal to edit details, status changes are tracked |
| **History Tab** | Shows all changes made to proposal with timestamp & user |
| **Permissions** | Only GCIR staff can access `/admin/` |
| **Bulk Actions** | Select multiple proposals and perform actions |

---

---

## User Workflows

### Typical GCIR Staff Workflow

```txt
1. GCIR Staff logs into /admin
   ↓
2. Click "Add Proposal" → ProposalForm appears
   ↓
3. Fill form (Title, Type, Agency, PI, Dates, etc.)
   ↓
4. Submit → System auto-generates GCIR Code (e.g., G-2025-CS-IND-001)
   ↓
5. Proposal saved & visible in list
   ↓
6. As proposal progresses, update Status field (DRAFT → PERMISSION → ... → APPROVED)
   ↓
7. When status = APPROVED, fill in Sanction Letter Number & Final Cost
   ↓
8. All changes automatically recorded in audit trail
   ↓
9. Generate weekly report to see all changes from past 7 days
```

### Requirement Mapping to Workflows

| User Action | Feature | Requirement | Where It Happens |
|------------|---------|------------|-----------------|
| Create proposal | Proposal form | FR1 | `/admin/proposals/proposal/add/` |
| System generates code | GCIR code service | FR2 | `services.generate_gcir_code()` |
| View proposal | Detail page | FR3 | `/admin/proposals/proposal/{code}/` |
| Change status | Status dropdown | FR4 | Form field in admin |
| Search proposals | Search bar | FR5 | Admin search box |
| Upload sanction letter | Document model | FR6 | ProposalDocument inline in admin |
| View dashboard | Aggregation view | FR7 | `/dashboard/` (custom page) |
| Record sanction details | Form fields | FR8 | Admin form fields |
| See audit trail | History tab | AR1-AR4 | Admin change history tab |

---

## 8. Deployment Options (TBD - To Be Decided)

### Available Platforms

The application is designed to run on multiple platforms. The choice will depend on:

- **Infrastructure availability** (existing servers, cloud accounts, etc.)
- **Maintenance preference** (managed vs. self-hosted)
- **Cost constraints**
- **Performance requirements** (for 5-20 office staff, all options are viable)

| Platform | Cost | Setup Effort | Maintenance | Notes |
|----------|------|--------------|------------|-------|
| **Heroku** | Free tier (limited) / $7+/month | Low | Very low (platform handles updates) | Good for: Quick deployment, no server management |
| **DigitalOcean VPS** | $5-6/month | Medium | Medium (manual updates, backups) | Good for: Full control, low cost, reliable |
| **Raspberry Pi (self-hosted)** | Hardware cost only | Medium | Medium (manual maintenance) | Good for: On-campus deployment, no recurring costs |
| **AWS Lightsail** | $3.50+/month | Medium | Medium | Good for: Existing AWS infrastructure |
| **Existing University Server** | Variable | Low-Medium | Depends on IT support | Good for: Leveraging existing infrastructure |

### Deployment Requirements (Platform-Independent)

Regardless of chosen platform, the system needs:

1. **Python 3.11+** runtime
2. **WSGI Server** (Gunicorn)
3. **Web Server** (Nginx) - or platform-specific reverse proxy
4. **SSL/HTTPS** certificate (Let's Encrypt free, or platform-provided)
5. **Daily database backups** to cloud storage or USB

### Next Steps for Deployment Decision

- [ ] Assess available infrastructure (cloud accounts, existing servers, etc.)
- [ ] Determine maintenance preference (managed vs. self-hosted)
- [ ] Check cost constraints
- [ ] Choose platform and update Section 8 with specific steps
- [ ] Document platform-specific configuration

---

## Deployment Example: DigitalOcean ($5-6/month VPS)

```bash
#!/bin/bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv nginx supervisor git

cd /home/ubuntu
git clone https://github.com/Arnav3094/GCIR-GMS.git
cd GCIR-GMS

# Install Pipenv
pip3 install pipenv

# Install dependencies
pipenv install --deploy --ignore-pipfile

# Run migrations
pipenv run python manage.py collectstatic --noinput
pipenv run python manage.py migrate

# Supervisor config
sudo tee /etc/supervisor/conf.d/gms.conf > /dev/null <<EOF
[program:gms]
directory=/home/ubuntu/GCIR-GMS
command=/home/ubuntu/.local/bin/pipenv run gunicorn gms_project.wsgi:application --bind 127.0.0.1:8000 --workers 3
autostart=true
autorestart=true
stderr_logfile=/var/log/gms.err.log
stdout_logfile=/var/log/gms.out.log
EOF

sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start gms

# Nginx config
sudo tee /etc/nginx/sites-available/gms > /dev/null <<EOF
server {
    listen 80;
    server_name your-domain.com;
    
    location /static/ {
        alias /home/ubuntu/GCIR-GMS/staticfiles/;
    }
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/gms /etc/nginx/sites-enabled/
sudo systemctl restart nginx

# SSL (Let's Encrypt)
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## 9. Initial Setup Commands

```bash
# Install Pipenv globally (if not already installed)
pip install pipenv

# Install dependencies
pipenv install

# Activate Pipenv shell
pipenv shell

# Create project & app
django-admin startproject gms_project .
python manage.py startapp proposals

# Create migrations & database
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run locally
python manage.py runserver
# Access: http://localhost:8000/admin
```

---

## 10. Requirements Coverage

| Requirement | Implementation |
|-------------|-----------------|
| FR1 - Create Proposal | ProposalForm + proposal_create view |
| FR2 - Generate GCIR Code | generate_gcir_code() service |
| FR3 - View/Edit Proposal | proposal_detail view + admin |
| FR4 - Status Transitions | Status field in model |
| FR5 - Search/Filter | proposal_list view with filters |
| FR6 - Upload Documents | ProposalDocument model |
| FR7 - Dashboard | Dashboard view (aggregations) |
| FR8 - Sanction Letter | Form fields in Proposal model |
| AR1-AR4 - Audit Trail | django-simple-history + changelog_report |
| DR1-DR4 - Data Model | All models defined |

---

## 11. Production Checklist

- [ ] Set `DEBUG=False` in settings
- [ ] Set strong `SECRET_KEY`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Enable HTTPS/SSL
- [ ] Daily database backups
- [ ] Configure error logging
- [ ] Email configuration for notifications

---

## Quick Reference: Development Workflow

### Step 1: Project Setup (Once)

```bash
pipenv install
pipenv shell

django-admin startproject gms_project .
python manage.py startapp proposals
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
# Access http://localhost:8000/admin
```

### Step 2: Make Changes

Edit `models.py` → Create form in `forms.py` → Customize admin in `admin.py`

### Step 3: Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### Step 4: Test Locally

```bash
python manage.py runserver
# Visit http://localhost:8000/admin and test features
```

### Step 5: Deploy

- Push to GitHub
- SSH into server
- Run deployment script (Section 8)

---

## Key Technologies & Why They're Chosen

| Decision | Choice | Why |
|----------|--------|-----|
| Framework | Django | Battle-tested, built-in admin, ORM, security |
| Database | SQLite | Zero setup, perfect for <50 users |
| Frontend | Django Templates | Server-side rendering = simple, no build process |
| Styling | Bootstrap 5 | Professional look, CDN-based, minimal setup |
| **Hosting** | **Multiple options available** | Flexibility to choose based on infrastructure, cost, preferences |
| Audit Trail | django-simple-history | 1 line of code per model = automatic tracking |

**Note on Hosting:** The application is platform-agnostic and can run on:

- Cloud platforms (Heroku, DigitalOcean, AWS, Azure)
- On-campus infrastructure (university servers, Raspberry Pi, etc.)
- The choice will be finalized during deployment planning phase

---

## File Reference Guide

| File | Edit When | Don't Edit When |
|------|-----------|-----------------|
| `models.py` | Adding/changing database fields | Making custom views |
| `views.py` | Adding/changing business logic or pages | Never auto-edits (manual only) |
| `forms.py` | Adding/changing form fields or validation | Auto-generated by admin |
| `admin.py` | Customizing admin interface | Not needed for basic setup |
| `urls.py` | Adding new routes/pages | Using admin interface |
| `settings.py` | Changing configuration, adding apps | During normal use |
| Templates | Styling or layout changes | For admin-only workflows |

---

## What NOT to Do (Common Pitfalls)

❌ **Don't** add complex caching (Redis, Memcached) - SQLite is fast enough  
❌ **Don't** use microservices - One simple Django app is best  
❌ **Don't** add Celery for tasks - 1-5 users don't need async  
❌ **Don't** overcomplicate custom UI - Use admin interface  
❌ **Don't** forget to backup database daily  
❌ **Don't** expose SECRET_KEY in code - Use `.env` file  

---

## Success Criteria

✅ GCIR staff can create proposals in <5 clicks  
✅ GCIR Code auto-generates correctly  
✅ Status changes are tracked in audit trail  
✅ Weekly changelog report is accessible  
✅ System runs on chosen hosting platform (low-cost options available)  
✅ No expensive database server needed (SQLite included)  
✅ Backup/restore takes <5 minutes  
✅ Platform-agnostic code (can migrate between deployment options)
