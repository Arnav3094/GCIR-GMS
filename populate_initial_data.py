#!/usr/bin/env python3
"""
Populate initial data for testing the admin interface.
Run with: python3 manage.py shell < populate_initial_data.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gms_project.settings')
django.setup()

from proposals.models import Department, ProjectType, FundingAgency, Investigator, ExternalInvestigator

# Create departments
cs_dept = Department.objects.create(code='CS', name='Computer Science')
ee_dept = Department.objects.create(code='EE', name='Electrical Engineering')

# Create project types
ind_type = ProjectType.objects.create(code='IND', name='Individual Research')
col_type = ProjectType.objects.create(code='COL', name='Collaborative Research')

# Create funding agencies
nsf = FundingAgency.objects.create(code='NSF', name='National Science Foundation')
dod = FundingAgency.objects.create(code='DOD', name='Department of Defense')

# Create internal investigators
inv1 = Investigator.objects.create(psrn='G0001', name='Dr. Alice Smith', email='alice@university.edu', department=cs_dept)
inv2 = Investigator.objects.create(psrn='G0002', name='Dr. Bob Johnson', email='bob@university.edu', department=cs_dept)
inv3 = Investigator.objects.create(psrn='G0003', name='Dr. Carol White', email='carol@university.edu', department=ee_dept)

# Create external investigators
ext_inv1 = ExternalInvestigator.objects.create(
    name='Prof. David Kumar',
    email='david@external.edu',
    organization='MIT',
    country='USA',
    designation='Professor'
)

ext_inv2 = ExternalInvestigator.objects.create(
    name='Prof. Eva Rodriguez',
    email='eva@external.es',
    organization='Universidad de Madrid',
    country='Spain',
    designation='Associate Professor'
)

print("✓ Initial data created successfully!")
print(f"  - Departments: {Department.objects.count()}")
print(f"  - Project Types: {ProjectType.objects.count()}")
print(f"  - Funding Agencies: {FundingAgency.objects.count()}")
print(f"  - Internal Investigators: {Investigator.objects.count()}")
print(f"  - External Investigators: {ExternalInvestigator.objects.count()}")
