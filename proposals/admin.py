"""
Django admin customization for the proposals app.

Registers models with the admin interface and customizes the UI/behavior
per SPECIFICATION.md, including history tracking and GCIR code generation.
"""

from django.contrib import admin
from django.db.models import signals
from django.dispatch import receiver
from simple_history.admin import SimpleHistoryAdmin

from .models import (
    Department,
    ProjectType,
    FundingAgency,
    Investigator,
    Proposal,
    ProposalInvestigator,
    ProposalDocument,
)
from .services import generate_gcir_code


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')
    search_fields = ('code', 'name')


@admin.register(ProjectType)
class ProjectTypeAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')
    search_fields = ('code', 'name')


@admin.register(FundingAgency)
class FundingAgencyAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Investigator)
class InvestigatorAdmin(admin.ModelAdmin):
    list_display = ('psrn', 'name', 'email', 'department')
    list_filter = ('department',)
    search_fields = ('psrn', 'name', 'email')


class ProposalInvestigatorInline(admin.TabularInline):
    """Inline editor for investigators on a proposal."""
    model = ProposalInvestigator
    extra = 1
    fields = ('investigator', 'role')


class ProposalDocumentInline(admin.TabularInline):
    """Inline editor for documents attached to a proposal."""
    model = ProposalDocument
    extra = 1
    fields = ('file', 'document_type', 'uploaded_at')
    readonly_fields = ('uploaded_at',)


@admin.register(Proposal)
class ProposalAdmin(SimpleHistoryAdmin):
    """
    Admin interface for Proposal model with history tracking.
    
    Features:
    - Auto-generates GCIR code on creation
    - GCIR code is read-only after creation
    - Shows history tab with all changes via SimpleHistoryAdmin
    - Inline editors for investigators and documents
    - Enforces exactly one PI per proposal
    """

    list_display = ('gcir_code', 'title', 'status', 'department', 'project_type', 'application_date')
    list_filter = ('status', 'department', 'project_type', 'created_at')
    search_fields = ('gcir_code', 'title')
    readonly_fields = ('gcir_code', 'created_at', 'updated_at')
    
    fieldsets = (
        ('GCIR Code & Basic Info', {
            'fields': ('gcir_code', 'title', 'department', 'project_type')
        }),
        ('Dates & Status', {
            'fields': ('status', 'application_date', 'start_date', 'end_date')
        }),
        ('Funding', {
            'fields': ('funding_agency', 'final_sanctioned_cost')
        }),
        ('Sanction', {
            'fields': ('sanction_letter_number',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [ProposalInvestigatorInline, ProposalDocumentInline]

    def save_model(self, request, obj, form, change):
        """Override save to call clean() for validation."""
        obj.full_clean()  # This calls clean() and validates
        super().save_model(request, obj, form, change)


@admin.register(ProposalInvestigator)
class ProposalInvestigatorAdmin(admin.ModelAdmin):
    list_display = ('proposal', 'investigator', 'role')
    list_filter = ('role',)
    search_fields = ('proposal__gcir_code', 'investigator__name')


@admin.register(ProposalDocument)
class ProposalDocumentAdmin(admin.ModelAdmin):
    list_display = ('proposal', 'document_type', 'uploaded_at')
    list_filter = ('document_type', 'uploaded_at')
    search_fields = ('proposal__gcir_code', 'document_type')
    readonly_fields = ('uploaded_at',)


# Signal handler to auto-generate GCIR code on proposal creation
@receiver(signals.pre_save, sender=Proposal)
def auto_generate_gcir_code(sender, instance, **kwargs):
    """
    Signal handler: auto-generates GCIR code if the proposal is new and gcir_code is empty.
    
    This hook runs before saving a Proposal instance. If the proposal is new (pk is None)
    and gcir_code is blank, we generate one using the GCIR code service.
    """
    # Check if this is a new proposal (no primary key yet)
    if instance.pk is None and not instance.gcir_code:
        # Generate GCIR code using the service
        instance.gcir_code = generate_gcir_code(
            project_type_id=instance.project_type_id,
            department_id=instance.department_id,
        )
