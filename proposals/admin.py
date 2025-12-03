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

from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.db import transaction
import io
import csv

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

    # show custom change form template so we can add the button
    change_form_template = "admin/proposals/investigator/change_form.html"

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        """Add upload URL to template context so template can render the button."""
        if extra_context is None:
            extra_context = {}
        extra_context['upload_url'] = reverse('admin:proposals_investigator_upload_psrn')
        return super().changeform_view(request, object_id, form_url, extra_context=extra_context)

    # Upload form for PSRN mapping
    class PSRNUploadForm(forms.Form):
        file = forms.FileField(label='Excel/CSV file', help_text='Accepted: .xlsx, .xls, .csv')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('upload-psrn/', self.admin_site.admin_view(self.upload_psrn_view), name='proposals_investigator_upload_psrn'),
        ]
        return custom_urls + urls

    def upload_psrn_view(self, request):
        """
        Admin view to upload a spreadsheet (CSV or Excel) with columns:
        PSRN, NAME, DEPT

        Behavior:
        - Column headers are case-insensitive.
        - If DEPT value does not match an existing Department, create a Department
          with code=DEPT and name=DEPT.
        - For each row, update_or_create Investigator by psrn.
        """
        if request.method == 'POST':
            form = self.PSRNUploadForm(request.POST, request.FILES)
            if form.is_valid():
                uploaded = form.cleaned_data['file']
                filename = uploaded.name.lower()
                rows = []
                # Read file bytes once
                data = uploaded.read()
                try:
                    try:
                        import pandas as pd
                    except Exception:
                        pd = None

                    if pd:
                        if filename.endswith(('.xls', '.xlsx')):
                            df = pd.read_excel(io.BytesIO(data))
                        else:
                            # csv or other text formats
                            df = pd.read_csv(io.StringIO(data.decode('utf-8')))
                        # normalize columns
                        df.columns = [str(c).strip().lower() for c in df.columns]
                        for _, r in df.iterrows():
                            # convert row to dict with lowercased keys
                            row = {k: (None if pd.isna(v) else v) for k, v in r.items()}
                            rows.append(row)
                    else:
                        # pandas not available: support CSV only
                        if not filename.endswith('.csv'):
                            raise RuntimeError("pandas not installed; only CSV supported as fallback. Install pandas to read Excel files.")
                        text = data.decode('utf-8')
                        reader = csv.DictReader(io.StringIO(text))
                        for r in reader:
                            rows.append({k.strip().lower(): v for k, v in r.items()})
                except Exception as e:
                    messages.error(request, f"Error reading uploaded file: {e}")
                    return render(request, 'admin/proposals/investigator/upload_psrn.html', {'form': form, 'opts': self.model._meta})

                if not rows:
                    messages.error(request, "Uploaded file contains no rows.")
                    return render(request, 'admin/proposals/investigator/upload_psrn.html', {'form': form, 'opts': self.model._meta})

                # required column check
                sample_keys = set(rows[0].keys())
                if 'psrn' not in sample_keys:
                    messages.error(request, "Missing required column 'PSRN'. Column headers are case-insensitive.")
                    return render(request, 'admin/proposals/investigator/upload_psrn.html', {'form': form, 'opts': self.model._meta})

                created = 0
                updated = 0
                failed = 0
                errors = []

                with transaction.atomic():
                    for i, row in enumerate(rows, start=1):
                        psrn = (row.get('psrn') or '').strip()
                        if not psrn:
                            failed += 1
                            errors.append(f"Row {i}: empty PSRN")
                            continue
                        name = (row.get('name') or '').strip()
                        dept_val = (row.get('dept') or '').strip()

                        department_obj = None
                        if dept_val:
                            dept_code = dept_val.strip()
                            # Try to find existing department by code or name (case-insensitive)
                            department_obj = Department.objects.filter(code__iexact=dept_code).first() or Department.objects.filter(name__iexact=dept_code).first()
                            if not department_obj:
                                # create new department with code and name set to provided value
                                try:
                                    department_obj = Department.objects.create(code=dept_code, name=dept_code)
                                except Exception as e:
                                    # creation failed
                                    failed += 1
                                    errors.append(f"Row {i} (psrn={psrn}): failed creating department '{dept_code}': {e}")
                                    continue

                        try:
                            defaults = {}
                            if name:
                                defaults['name'] = name
                            if department_obj:
                                defaults['department'] = department_obj
                            obj, created_flag = Investigator.objects.update_or_create(
                                psrn=psrn,
                                defaults=defaults
                            )
                            if created_flag:
                                created += 1
                            else:
                                updated += 1
                        except Exception as e:
                            failed += 1
                            errors.append(f"Row {i} (psrn={psrn}): {e}")

                # Report results to admin
                if created:
                    messages.success(request, f"Created {created} investigators.")
                if updated:
                    messages.success(request, f"Updated {updated} investigators.")
                if failed:
                    messages.error(request, f"Failed {failed} rows. See up to first 10 errors below.")
                    for err in errors[:10]:
                        messages.error(request, err)
                    if len(errors) > 10:
                        messages.error(request, f"... and {len(errors)-10} more errors.")

                return redirect('admin:proposals_investigator_changelist')
        else:
            form = self.PSRNUploadForm()

        context = {
            'form': form,
            'opts': self.model._meta,
            'app_label': self.model._meta.app_label,
        }
        return render(request, 'admin/proposals/investigator/upload_psrn.html', context)


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

