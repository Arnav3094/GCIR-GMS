"""
Business logic services for the proposals app.

This module contains helper functions for operations like generating
unique GCIR codes per the SPECIFICATION.md.
"""

from datetime import datetime
from typing import Optional
from django.db import transaction
from .models import Proposal, Department, ProjectType


def generate_gcir_code(project_type_id: int, department_id: int, year: Optional[int] = None) -> str:
    """
    Auto-generate a unique GCIR code for a new proposal.

    Format: G-{year}-{dept_code}-{type_code}-{serial}
    Example: G-2025-CS-IND-0001

    Args:
        project_type_id: ID of the ProjectType model instance
        department_id: ID of the Department model instance
        year: Academic/financial year (defaults to current year)

    Returns:
        A unique GCIR code string (e.g., 'G-2025-CS-IND-0001')

    Raises:
        ProjectType.DoesNotExist: if project_type_id doesn't exist
        Department.DoesNotExist: if department_id doesn't exist

    Notes:
        - Uses database transaction + select_for_update to ensure atomicity
        - Prevents race conditions during concurrent proposal creation
        - Serial number is zero-padded to 4 digits
    """
    if year is None:
        year = datetime.now().year

    # Fetch lookups (raises DoesNotExist if not found)
    project_type = ProjectType.objects.get(id=project_type_id)
    department = Department.objects.get(id=department_id)

    # Build pattern prefix
    pattern_prefix = f"G-{year}-{department.code}-{project_type.code}-"

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
            # Extract serial from codes like "G-2025-CS-IND-0001"
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
