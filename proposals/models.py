from django.db import models
from django.core.exceptions import ValidationError
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
	name = models.CharField(max_length=255, unique=True)

	def __str__(self) -> str:
		return self.name


class Investigator(models.Model):
	# PSRN (Personal/Personnel serial) - use as unique identifier
	psrn = models.CharField(max_length=32, unique=True)
	name = models.CharField(max_length=255)
	email = models.EmailField(blank=True, null=True)
	department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='investigators')

	def __str__(self) -> str:
		return f"{self.name} ({self.psrn})"


class Proposal(models.Model):
	# GCIR code (unique identifier). Kept as a regular field (unique) rather than PK to preserve default ids.
	gcir_code = models.CharField(max_length=64, unique=True, blank=True)
	title = models.CharField(max_length=500)
	project_type = models.ForeignKey(ProjectType, on_delete=models.PROTECT, related_name='proposals')
	department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='proposals')
	funding_agency = models.ForeignKey(FundingAgency, on_delete=models.SET_NULL, null=True, blank=True)

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
		Validate that proposal has exactly one PI and zero or more Co-PIs.
		
		Raises ValidationError if validation fails.
		"""
		# Only validate if proposal is already saved (has a pk)
		if self.pk is None:
			return

		pi_count = self.proposal_investigators.filter(role='PI').count() # type: ignore
		
		if pi_count == 0:
			raise ValidationError("Proposal must have exactly one Principal Investigator (PI).")
		elif pi_count > 1:
			raise ValidationError("Proposal can have only one Principal Investigator (PI).")
		
		# Co-PIs are optional, so no validation needed for them
class ProposalInvestigator(models.Model):
	ROLE_CHOICES = [
		('PI', 'Principal Investigator'),
		('CO_PI', 'Co-Principal Investigator'),
	]
	proposal = models.ForeignKey(Proposal, on_delete=models.CASCADE, related_name='proposal_investigators')
	investigator = models.ForeignKey(Investigator, on_delete=models.PROTECT, related_name='proposal_involvements')
	role = models.CharField(max_length=10, choices=ROLE_CHOICES)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=['proposal', 'investigator'], name='unique_proposal_investigator')
		]
        # enforces that an investigator cannot have multiple roles in the same proposal

	def __str__(self) -> str:
		return f"{self.investigator} - {self.role} on {self.proposal}"


class ProposalDocument(models.Model):
	proposal = models.ForeignKey(Proposal, on_delete=models.CASCADE, related_name='documents')
	file = models.FileField(upload_to='proposal_documents/')
	document_type = models.CharField(max_length=100, blank=True)
	uploaded_at = models.DateTimeField(auto_now_add=True)

	def __str__(self) -> str:
		return f"Document for {self.proposal} ({self.document_type})"

