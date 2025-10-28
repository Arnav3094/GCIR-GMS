"""
Django admin customization for the proposals app.

Registers models with the admin interface and customizes the UI/behavior
per SPECIFICATION.md, including history tracking and GCIR code generation.
"""

from django.contrib import admin, messages
from django.db.models import signals
from django.dispatch import receiver
from django import forms
from django.core.exceptions import ValidationError
from simple_history.admin import SimpleHistoryAdmin

from .models import (
    Department,
    ProjectType,
    FundingAgency,
    Investigator,
    ExternalInvestigator,
    Proposal,
    ProposalInvestigator,
    ProposalDocument,
    ProposalAlternateID,
)
from .services import generate_gcir_code, generate_external_investigator_code


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
    list_display = ('code', 'name')
    search_fields = ('code', 'name')


class ProposalInvestigatorForm(forms.ModelForm):
    """Custom form for ProposalInvestigator with proper validation."""
    
    class Meta:
        model = ProposalInvestigator
        fields = ('investigator', 'external_investigator', 'role')
    
    def clean(self):
        """Ensure exactly one of investigator or external_investigator is set."""
        cleaned_data = super().clean()
        investigator = cleaned_data.get('investigator')
        external_investigator = cleaned_data.get('external_investigator')
        
        # Check that exactly one is set
        if not investigator and not external_investigator:
            raise ValidationError(
                "You must select either an Internal Investigator or an External Investigator."
            )
        
        if investigator and external_investigator:
            raise ValidationError(
                "You cannot select both an Internal Investigator and an External Investigator. Please choose one."
            )
        
        return cleaned_data


class ProposalInvestigatorInlineFormSet(forms.BaseInlineFormSet):
    """Inline formset to enforce exactly one PI per proposal."""

    def clean(self):
        super().clean()

        # Count PI roles among forms that are not marked for deletion
        pi_count = 0
        for form in self.forms:
            # Skip forms that failed validation themselves
            if not hasattr(form, 'cleaned_data'):
                continue
            if form.cleaned_data.get('DELETE', False):
                continue
            role = form.cleaned_data.get('role')
            if role == 'PI':
                pi_count += 1

        if pi_count != 1:
            raise ValidationError(
                "Each proposal must have exactly one Principal Investigator (PI). "
                "Please add exactly one PI in the Investigators section."
            )


@admin.register(Investigator)
class InvestigatorAdmin(admin.ModelAdmin):
    list_display = ('psrn', 'name', 'email', 'department')
    list_filter = ('department',)
    search_fields = ('psrn', 'name', 'email')


@admin.register(ExternalInvestigator)
class ExternalInvestigatorAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'organization', 'country', 'created_at')
    list_filter = ('country', 'created_at')
    search_fields = ('code', 'name', 'organization', 'email')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'name', 'email')
        }),
        ('Affiliation', {
            'fields': ('organization', 'department', 'designation', 'country')
        }),
        ('Contact', {
            'fields': ('phone',)
        }),
        ('Additional Information', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


class ProposalInvestigatorInline(admin.TabularInline):
    """Inline editor for investigators on a proposal (internal or external)."""
    model = ProposalInvestigator
    form = ProposalInvestigatorForm
    formset = ProposalInvestigatorInlineFormSet
    extra = 1
    fields = ('investigator', 'external_investigator', 'role')
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Customize foreign key fields for better display."""
        if db_field.name == 'investigator':
            kwargs['label'] = 'Internal Investigator'
        elif db_field.name == 'external_investigator':
            kwargs['label'] = 'External Investigator'
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class ProposalDocumentInline(admin.TabularInline):
    """Inline editor for documents attached to a proposal."""
    model = ProposalDocument
    extra = 1
    fields = ('file', 'document_type', 'uploaded_at')
    readonly_fields = ('uploaded_at',)


class ProposalAlternateIDInline(admin.TabularInline):
    """Inline editor for alternate IDs (legacy tracking) for a proposal."""
    model = ProposalAlternateID
    extra = 1
    fields = ('key', 'value', 'notes', 'created_at')
    readonly_fields = ('created_at',)


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
        ('Status Timeline', {
            'fields': ('date_draft', 'date_permission', 'date_submitted', 'date_review', 
                      'date_approved', 'date_disbursed', 'date_rejected', 'date_closed', 'date_on_hold'),
            'classes': ('collapse',),
            'description': 'Automatically updated timestamps for each status transition'
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
    
    inlines = [ProposalInvestigatorInline, ProposalDocumentInline, ProposalAlternateIDInline]

    def save_model(self, request, obj, form, change):
        """Override save to call clean() for validation."""
        obj.full_clean()  # This calls clean() and validates
        super().save_model(request, obj, form, change)
    
    def save_formset(self, request, form, formset, change):
        """
        Override save_formset to validate PI/Co-PI requirements AFTER the main proposal is saved.
        
        This ensures:
        - Exactly one PI (internal or external)
        - Zero or more Co-PIs (internal or external)
        """
        # Save all instances first
        formset.save()
        
        # Now validate that we have exactly one PI among all investigators
        proposal = form.instance
        
        # Get all investigators for this proposal (including just-saved ones)
        pi_count = proposal.proposal_investigators.filter(role='PI').count()
        co_pi_count = proposal.proposal_investigators.filter(role='CO_PI').count()
        
        # Show appropriate message to user
        if pi_count == 0:
            messages.warning(
                request,
                "⚠️  Warning: This proposal has no Principal Investigator (PI). "
                "Each proposal must have exactly one PI. Please add one in the Investigators section."
            )
        elif pi_count > 1:
            messages.error(
                request,
                f"❌ Error: This proposal has {pi_count} Principal Investigators (PIs), but only one is allowed. "
                "Please remove the extras."
            )
        else:
            # Exactly one PI - this is good
            messages.success(
                request,
                f"✓ Proposal saved. PI: 1, Co-PIs: {co_pi_count}"
            )


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


@admin.register(ProposalAlternateID)
class ProposalAlternateIDAdmin(admin.ModelAdmin):
    list_display = ('proposal', 'key', 'value', 'created_at')
    list_filter = ('key', 'created_at')
    search_fields = ('proposal__gcir_code', 'key', 'value')
    readonly_fields = ('created_at',)


# Signal handler to auto-generate GCIR code on proposal creation
@receiver(signals.pre_save, sender=Proposal)
def auto_generate_gcir_code(sender, instance, **kwargs):
    """
    Signal handler: auto-generates GCIR code if the proposal is new and gcir_code is empty.
    
    This hook runs before saving a Proposal instance. If the proposal is new (pk is None)
    and gcir_code is blank, we generate one using the GCIR code service.
    
    Year derivation:
    - If application_date is set, use its year (for retroactively added historical proposals)
    - Otherwise, use current calendar year (no need to pass explicitly, service handles it)
    """
    # Check if this is a new proposal (no primary key yet)
    if instance.pk is None and not instance.gcir_code:
        # Generate GCIR code using the service
        instance.gcir_code = generate_gcir_code(
            project_type_id=instance.project_type_id,
            department_id=instance.department_id,
            funding_agency_id=instance.funding_agency_id,
            application_date=instance.application_date,
        )


# Signal handler to auto-generate external investigator code on creation
@receiver(signals.pre_save, sender=ExternalInvestigator)
def auto_generate_external_investigator_code(sender, instance, **kwargs):
    """
    Signal handler: auto-generates external investigator code if not provided.
    
    This hook runs before saving an ExternalInvestigator instance. If the external investigator
    is new (pk is None) and code is blank, we generate one using the code generator service.
    
    Format: E{serial} (e.g., E0001, E0002, etc.)
    """
    # Check if this is a new external investigator (no primary key yet)
    if instance.pk is None and not instance.code:
        # Generate external investigator code using the service
        instance.code = generate_external_investigator_code()

