from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Q
from decimal import Decimal
from simple_history.models import HistoricalRecords


class Department(models.Model):
	code = models.CharField(max_length=10, unique=True)
	name = models.CharField(max_length=200)

	def __str__(self) -> str:
		return f"{self.code} - {self.name}"


class ProjectType(models.Model):
	code = models.CharField(max_length=10, unique=True)
	name = models.CharField(max_length=200)

	def __str__(self) -> str:
		return f"{self.code} - {self.name}"


class FundingAgency(models.Model):
	code = models.CharField(max_length=10, unique=True, default='NAN')
	name = models.CharField(max_length=255, unique=True)

	def __str__(self) -> str:
		return f"{self.code} - {self.name}"


class Investigator(models.Model):
	"""Internal faculty/staff investigators (PSRN: GXXXX format)."""
	# PSRN (Personal/Personnel serial) - format: GXXXX
	psrn = models.CharField(max_length=32, unique=True)
	name = models.CharField(max_length=255)
	email = models.EmailField(blank=True, null=True)
	department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='investigators')

	def __str__(self) -> str:
		return f"{self.name} ({self.psrn})"


class ExternalInvestigator(models.Model):
	"""External collaborators/investigators from outside the university (code: EXXXX format)."""
	# External code - format: EXXXX
	code = models.CharField(max_length=32, unique=True, blank=True, null=True, help_text="Leave blank to auto-generate (format: EXXXX). Or enter a custom code.")
	name = models.CharField(max_length=255)
	email = models.EmailField(blank=True, null=True)
	
	# Affiliation details
	organization = models.CharField(max_length=255, help_text="Company/University/Institute name")
	department = models.CharField(max_length=255, blank=True, help_text="Department within the organization")
	country = models.CharField(max_length=100, blank=True, help_text="Country of affiliation")
	designation = models.CharField(max_length=100, blank=True, help_text="Position/Title (e.g., Professor, Research Scientist)")
	
	# Contact & Metadata
	phone = models.CharField(max_length=20, blank=True)
	notes = models.TextField(blank=True, help_text="Additional information about the investigator")
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self) -> str:
		return f"{self.name} ({self.code}) - {self.organization}"


class Proposal(models.Model):
	# GCIR code (unique identifier). Kept as a regular field (unique) rather than PK to preserve default ids.
	gcir_code = models.CharField(max_length=128, unique=True, blank=True)
	title = models.CharField(max_length=500)
	project_type = models.ForeignKey(ProjectType, on_delete=models.PROTECT, related_name='proposals')
	department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='proposals')
	funding_agency = models.ForeignKey(FundingAgency, on_delete=models.PROTECT, related_name='proposals', null=True, blank=True)

	STATUS_CHOICES = [
		('DRAFT', 'Draft'),
		('PERMISSION', 'Permission'),
		('SUBMITTED', 'Submitted'),
		('REVIEW', 'Review'),
		('APPROVED', 'Approved'),
		('DISBURSED', 'Disbursed'),
		('REJECTED', 'Rejected'),
		('CLOSED', 'Closed'),
		('ON_HOLD', 'On Hold'),
	]
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')

	application_date = models.DateField(null=True, blank=True)
	start_date = models.DateField(null=True, blank=True)
	end_date = models.DateField(null=True, blank=True)

	# Status transition dates (auto-tracked per status change)
	date_draft = models.DateField(null=True, blank=True, help_text="Date proposal was created/drafted")
	date_permission = models.DateField(null=True, blank=True, help_text="Date when status changed to PERMISSION")
	date_submitted = models.DateField(null=True, blank=True, help_text="Date when status changed to SUBMITTED")
	date_review = models.DateField(null=True, blank=True, help_text="Date when status changed to REVIEW")
	date_approved = models.DateField(null=True, blank=True, help_text="Date when status changed to APPROVED")
	date_disbursed = models.DateField(null=True, blank=True, help_text="Date when status changed to DISBURSED")
	date_rejected = models.DateField(null=True, blank=True, help_text="Date when status changed to REJECTED")
	date_closed = models.DateField(null=True, blank=True, help_text="Date when status changed to CLOSED")
	date_on_hold = models.DateField(null=True, blank=True, help_text="Date when status changed to ON_HOLD")

	sanction_letter_number = models.CharField(max_length=200, blank=True)
	final_sanctioned_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	# django-simple-history hook
	history = HistoricalRecords()

	def __str__(self) -> str:
		return self.gcir_code or f"Proposal {self.pk}"

	def clean(self):
		"""
		Validate that proposal has exactly one PI (internal or external) and 
		zero or more Co-PIs (internal or external).
		
		Raises ValidationError if validation fails.
		"""
		# Only validate if proposal is already saved (has a pk)
		if self.pk is None:
			return

		pi_count = self.proposal_investigators.filter(role='PI').count() # type: ignore
		
		if pi_count == 0:
			raise ValidationError(
				"Proposal must have exactly one Principal Investigator (PI); only one Principal Investigator is allowed."
			)
		elif pi_count > 1:
			raise ValidationError(
				"Proposal must have exactly one Principal Investigator (PI); only one Principal Investigator is allowed."
			)
		
		# Co-PIs are optional, so no validation needed for them
class ProposalInvestigator(models.Model):
	"""Link between Proposal and either an internal or external investigator."""
	ROLE_CHOICES = [
		('PI', 'Principal Investigator'),
		('CO_PI', 'Co-Principal Investigator'),
	]
	proposal = models.ForeignKey(Proposal, on_delete=models.CASCADE, related_name='proposal_investigators')
	
	# One of these must be set (either internal or external, not both)
	investigator = models.ForeignKey(Investigator, on_delete=models.PROTECT, null=True, blank=True, related_name='proposal_involvements')
	external_investigator = models.ForeignKey(ExternalInvestigator, on_delete=models.PROTECT, null=True, blank=True, related_name='proposal_involvements')
	
	role = models.CharField(max_length=10, choices=ROLE_CHOICES)

	class Meta:
		constraints = [
			# Ensure either internal OR external is set, not both, not neither
			models.CheckConstraint(
				check=(
					Q(investigator__isnull=False, external_investigator__isnull=True) |
					Q(investigator__isnull=True, external_investigator__isnull=False)
				),
				name='either_internal_or_external_investigator'
			),
			# Prevent duplicate internal investigators on same proposal
			models.UniqueConstraint(
				fields=['proposal', 'investigator'],
				condition=Q(investigator__isnull=False),
				name='unique_internal_investigator_per_proposal'
			),
			# Prevent duplicate external investigators on same proposal
			models.UniqueConstraint(
				fields=['proposal', 'external_investigator'],
				condition=Q(external_investigator__isnull=False),
				name='unique_external_investigator_per_proposal'
			),
		]

	def __str__(self) -> str:
		if self.investigator:
			return f"{self.investigator.name} ({self.investigator.psrn}) - {self.role} on {self.proposal}"
		elif self.external_investigator:
			return f"{self.external_investigator.name} ({self.external_investigator.code}) - {self.role} on {self.proposal}"
		return f"Unknown Investigator - {self.role} on {self.proposal}"


class ProposalDocument(models.Model):
	proposal = models.ForeignKey(Proposal, on_delete=models.CASCADE, related_name='documents')
	file = models.FileField(upload_to='proposal_documents/')
	document_type = models.CharField(max_length=100, blank=True)
	uploaded_at = models.DateTimeField(auto_now_add=True)

	def __str__(self) -> str:
		return f"Document for {self.proposal} ({self.document_type})"


class ProposalAlternateID(models.Model):
	"""
	Track legacy/alternate identifiers for proposals.
	
	Used to map GCIR codes to historical IDs from previous systems or 
	to store multiple identifiers for the same proposal (e.g., old reference 
	numbers, funding agency IDs, etc.).
	
	Example:
		- GCIR Code: G-2025-CS-IND-0001
		- Alternate IDs:
		  - key='old_system_id', value='PROP-2024-001'
		  - key='funding_ref', value='NSF-2024-12345'
	"""
	proposal = models.ForeignKey(Proposal, on_delete=models.CASCADE, related_name='alternate_ids')
	key = models.CharField(max_length=100, help_text="Identifier type (e.g., 'old_system_id', 'funding_ref')")
	value = models.CharField(max_length=255, help_text="The alternate identifier value")
	created_at = models.DateTimeField(auto_now_add=True)
	notes = models.TextField(blank=True, help_text="Optional notes about this alternate ID")

	class Meta:
		unique_together = ('proposal', 'key')
		indexes = [
			models.Index(fields=['key', 'value']),  # Useful for searching by alternate ID
		]

	def __str__(self) -> str:
		return f"{self.proposal.gcir_code} - {self.key}={self.value}"

