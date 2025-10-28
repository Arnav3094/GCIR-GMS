"""
Business logic services for the proposals app.

This module contains helper functions for operations like generating
unique GCIR codes per the SPECIFICATION.md and external investigator codes.
"""

from datetime import datetime, date
from typing import Optional
from django.db import transaction
from .models import Proposal, Department, ProjectType, ExternalInvestigator


def generate_gcir_code(project_type_id: int, department_id: int, year: Optional[int] = None, funding_agency_id: Optional[int] = None, application_date: Optional[date] = None) -> str:
    """
    Auto-generate a unique GCIR code for a new proposal.

    Format: G-{year}-{dept_code}-{type_code}[-{agency_code}]-{serial}
    Example: G-2025-CS-IND-NSF-0001 (with agency) or G-2025-CS-IND-0001 (without agency)

    Args:
        project_type_id: ID of the ProjectType model instance (required)
        department_id: ID of the Department model instance (required)
        year: Explicit calendar year (required if application_date not provided)
              If not provided, derived from application_date or current year
        funding_agency_id: ID of FundingAgency (optional, its code is included if provided)
        application_date: Optional application date to extract year from

    Returns:
        A unique GCIR code string (e.g., 'G-2025-CS-IND-NSF-0001' or 'G-2025-CS-IND-0001')

    Raises:
        ProjectType.DoesNotExist: if project_type_id doesn't exist
        Department.DoesNotExist: if department_id doesn't exist
        FundingAgency.DoesNotExist: if funding_agency_id is provided but doesn't exist
        ValueError: if year cannot be determined

    Notes:
        - Uses database transaction + select_for_update to ensure atomicity
        - Prevents race conditions during concurrent proposal creation
        - Serial number is zero-padded to 4 digits
        - Year determination: explicit year > application_date year > current year
        - Funding agency code is optional; format includes it only if provided
    """
    # Determine the year to use
    if year is None:
        if application_date:
            # Extract year from application_date
            year = application_date.year if hasattr(application_date, 'year') else int(str(application_date).split('-')[0])
        else:
            # Use current calendar year
            year = datetime.now().year

    # Fetch lookups (raises DoesNotExist if not found)
    project_type = ProjectType.objects.get(id=project_type_id)
    department = Department.objects.get(id=department_id)
    
    # Funding agency is optional
    agency_code = ""
    if funding_agency_id:
        from .models import FundingAgency
        funding_agency = FundingAgency.objects.get(id=funding_agency_id)
        agency_code = f"-{funding_agency.code}"

    # Build pattern prefix
    pattern_prefix = f"G-{year}-{department.code}-{project_type.code}{agency_code}-"

    # Use transaction + lock to prevent race conditions
    with transaction.atomic():
        # Lock all existing proposals with this pattern to ensure atomicity
        existing_proposals = (
            Proposal.objects
            .filter(gcir_code__startswith=pattern_prefix)
            .select_for_update()
        )

        # Find the highest serial number for this pattern
        if existing_proposals.exists():
            # Extract serial from codes like "G-2025-CS-IND-NSF-0001"
            serials = []
            for proposal in existing_proposals:
                try:
                    serial = int(proposal.gcir_code.split('-')[-1])
                    serials.append(serial)
                except (ValueError, IndexError):
                    # Skip malformed codes
                    pass

            next_serial = max(serials) + 1 if serials else 1
        else:
            next_serial = 1

        # Format serial with zero-padding (4 digits)
        return f"{pattern_prefix}{next_serial:04d}"


def generate_external_investigator_code() -> str:
    """
    Auto-generate a unique external investigator code.

    Format: E{serial}
    Example: E0001, E0002, E0003, etc.

    Returns:
        A unique external investigator code string (e.g., 'E0001')

    Notes:
        - Uses database transaction + select_for_update to ensure atomicity
        - Prevents race conditions during concurrent external investigator creation
        - Serial number is zero-padded to 4 digits
        - Global sequence (not scoped by any other field)
    """
    # Use transaction + lock to prevent race conditions
    with transaction.atomic():
        # Lock all existing external investigators to ensure atomicity
        existing_investigators = (
            ExternalInvestigator.objects
            .all()
            .select_for_update()
        )

        # Find the highest serial number
        if existing_investigators.exists():
            # Extract serial from codes like "E0001"
            serials = []
            for investigator in existing_investigators:
                try:
                    # Skip if code is not set (will be auto-generated)
                    if not investigator.code:
                        continue
                    # Remove 'E' prefix and convert to int
                    serial = int(investigator.code[1:])
                    serials.append(serial)
                except (ValueError, IndexError, TypeError):
                    # Skip malformed codes
                    pass

            next_serial = max(serials) + 1 if serials else 1
        else:
            next_serial = 1

        # Format serial with zero-padding (4 digits)
        return f"E{next_serial:04d}"

