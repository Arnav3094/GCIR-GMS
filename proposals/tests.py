from django.test import TestCase
from django.db import IntegrityError
from django.core.exceptions import ValidationError

from .models import Department, ProjectType, Proposal, Investigator, ProposalInvestigator
from .services import generate_gcir_code


class GCIRCodeGeneratorTest(TestCase):
    """Test GCIR code generation logic."""

    def setUp(self):
        """Create test fixtures: Department and ProjectType."""
        self.dept_cs = Department.objects.create(code='CS', name='Computer Science')
        self.dept_me = Department.objects.create(code='ME', name='Mechanical Engineering')
        self.type_ind = ProjectType.objects.create(code='IND', name='Industry')
        self.type_gov = ProjectType.objects.create(code='GOV', name='Government')

    def test_generate_first_gcir_code(self):
        """Test generating the first GCIR code for a department/type combination."""
        code = generate_gcir_code(
            project_type_id=self.type_ind.id,  # type: ignore
            department_id=self.dept_cs.id,  # type: ignore
            year=2025
        )
        self.assertEqual(code, 'G-2025-CS-IND-0001')

    def test_generate_second_gcir_code_increments_serial(self):
        """Test that second code increments the serial number."""
        # Create first proposal
        Proposal.objects.create(
            gcir_code='G-2025-CS-IND-0001',
            title='First Proposal',
            department=self.dept_cs,
            project_type=self.type_ind,
        )

        # Generate second code
        code = generate_gcir_code(
            project_type_id=self.type_ind.id,  # type: ignore
            department_id=self.dept_cs.id,  # type: ignore  # type: ignore
            year=2025
        )
        self.assertEqual(code, 'G-2025-CS-IND-0002')

    def test_separate_sequences_for_different_department(self):
        """Test that different departments have separate serial sequences."""
        # Create a CS proposal
        Proposal.objects.create(
            gcir_code='G-2025-CS-IND-0001',
            title='CS Proposal',
            department=self.dept_cs,
            project_type=self.type_ind,
        )

        # Generate code for ME department (should start at 0001)
        code = generate_gcir_code(
            project_type_id=self.type_ind.id,  # type: ignore  # type: ignore
            department_id=self.dept_me.id,  # type: ignore  # type: ignore
            year=2025
        )
        self.assertEqual(code, 'G-2025-ME-IND-0001')

    def test_separate_sequences_for_different_project_type(self):
        """Test that different project types have separate serial sequences."""
        # Create an IND proposal
        Proposal.objects.create(
            gcir_code='G-2025-CS-IND-0001',
            title='Industry Proposal',
            department=self.dept_cs,
            project_type=self.type_ind,
        )

        # Generate code for GOV type (should start at 0001)
        code = generate_gcir_code(
            project_type_id=self.type_gov.id,  # type: ignore
            department_id=self.dept_cs.id,  # type: ignore
            year=2025
        )
        self.assertEqual(code, 'G-2025-CS-GOV-0001')

    def test_separate_sequences_for_different_year(self):
        """Test that different years have separate serial sequences."""
        # Create a 2025 proposal
        Proposal.objects.create(
            gcir_code='G-2025-CS-IND-0001',
            title='2025 Proposal',
            department=self.dept_cs,
            project_type=self.type_ind,
        )

        # Generate code for 2026 (should start at 0001)
        code = generate_gcir_code(
            project_type_id=self.type_ind.id,  # type: ignore
            department_id=self.dept_cs.id,  # type: ignore
            year=2026
        )
        self.assertEqual(code, 'G-2026-CS-IND-0001')

    def test_generates_many_codes_without_duplicates(self):
        """Test that generating multiple codes in sequence produces no duplicates."""
        codes = set()
        for i in range(1, 6):
            code = generate_gcir_code(
                project_type_id=self.type_ind.id,  # type: ignore
                department_id=self.dept_cs.id,  # type: ignore
                year=2025
            )
            # Create a proposal to ensure next call increments
            Proposal.objects.create(
                gcir_code=code,
                title=f'Proposal {i}',
                department=self.dept_cs,
                project_type=self.type_ind,
            )
            codes.add(code)

        # Should have 5 unique codes
        self.assertEqual(len(codes), 5)
        expected_codes = {
            'G-2025-CS-IND-0001',
            'G-2025-CS-IND-0002',
            'G-2025-CS-IND-0003',
            'G-2025-CS-IND-0004',
            'G-2025-CS-IND-0005',
        }
        self.assertEqual(codes, expected_codes)

    def test_nonexistent_project_type_raises_error(self):
        """Test that requesting a nonexistent project type raises DoesNotExist."""
        with self.assertRaises(ProjectType.DoesNotExist):
            generate_gcir_code(
                project_type_id=9999,
                department_id=self.dept_cs.id,  # type: ignore
                year=2025
            )

    def test_nonexistent_department_raises_error(self):
        """Test that requesting a nonexistent department raises DoesNotExist."""
        with self.assertRaises(Department.DoesNotExist):
            generate_gcir_code(
                project_type_id=self.type_ind.id,  # type: ignore
                department_id=9999,
                year=2025
            )


class ProposalAutoGenerationTest(TestCase):
    """Test that GCIR codes are auto-generated on proposal creation."""

    def setUp(self):
        """Create test fixtures."""
        self.dept = Department.objects.create(code='CS', name='Computer Science')
        self.type_proj = ProjectType.objects.create(code='IND', name='Industry')

    def test_proposal_creation_auto_generates_gcir_code(self):
        """Test that creating a proposal without gcir_code auto-generates one."""
        proposal = Proposal.objects.create(
            title='Test Proposal',
            department=self.dept,
            project_type=self.type_proj,
        )
        # After save, gcir_code should be populated
        self.assertIsNotNone(proposal.gcir_code)
        self.assertTrue(proposal.gcir_code.startswith('G-'))
        self.assertIn('CS-IND', proposal.gcir_code)

    def test_proposal_with_explicit_gcir_code_is_not_overwritten(self):
        """Test that providing an explicit gcir_code is not overwritten."""
        custom_code = 'G-2025-CS-IND-0099'
        proposal = Proposal.objects.create(
            gcir_code=custom_code,
            title='Custom Code Proposal',
            department=self.dept,
            project_type=self.type_proj,
        )
        # Should keep the custom code
        self.assertEqual(proposal.gcir_code, custom_code)


class ProposalPIValidationTest(TestCase):
    """Test that proposals enforce exactly one PI per proposal."""

    def setUp(self):
        """Create test fixtures."""
        self.dept = Department.objects.create(code='CS', name='Computer Science')
        self.type_proj = ProjectType.objects.create(code='IND', name='Industry')
        self.inv1 = Investigator.objects.create(psrn='INV001', name='Dr. Alice', department=self.dept)
        self.inv2 = Investigator.objects.create(psrn='INV002', name='Dr. Bob', department=self.dept)
        self.inv3 = Investigator.objects.create(psrn='INV003', name='Dr. Carol', department=self.dept)

        # Create a proposal
        self.proposal = Proposal.objects.create(
            title='Test Proposal',
            department=self.dept,
            project_type=self.type_proj,
        )

    def test_proposal_with_no_pi_fails_validation(self):
        """Test that clean() raises ValidationError if no PI is assigned."""
        # Try to validate with no PIs
        with self.assertRaises(ValidationError) as cm:
            self.proposal.clean()
        
        self.assertIn("must have exactly one Principal Investigator", str(cm.exception))

    def test_proposal_with_one_pi_passes_validation(self):
        """Test that clean() passes with exactly one PI."""
        # Add one PI
        ProposalInvestigator.objects.create(
            proposal=self.proposal,
            investigator=self.inv1,
            role='PI'
        )
        
        # Should not raise
        self.proposal.clean()

    def test_proposal_with_multiple_pis_fails_validation(self):
        """Test that clean() raises ValidationError if multiple PIs are assigned."""
        # Add two PIs (should not be allowed)
        ProposalInvestigator.objects.create(
            proposal=self.proposal,
            investigator=self.inv1,
            role='PI'
        )
        ProposalInvestigator.objects.create(
            proposal=self.proposal,
            investigator=self.inv2,
            role='PI'
        )
        
        # Should fail validation
        with self.assertRaises(ValidationError) as cm:
            self.proposal.clean()
        
        self.assertIn("only one Principal Investigator", str(cm.exception))

    def test_proposal_with_one_pi_and_multiple_copis_passes_validation(self):
        """Test that clean() passes with one PI and multiple Co-PIs."""
        # Add one PI and two Co-PIs
        ProposalInvestigator.objects.create(
            proposal=self.proposal,
            investigator=self.inv1,
            role='PI'
        )
        ProposalInvestigator.objects.create(
            proposal=self.proposal,
            investigator=self.inv2,
            role='CO_PI'
        )
        ProposalInvestigator.objects.create(
            proposal=self.proposal,
            investigator=self.inv3,
            role='CO_PI'
        )
        
        # Should not raise
        self.proposal.clean()

    def test_proposal_with_only_copis_fails_validation(self):
        """Test that clean() fails if only Co-PIs are assigned (no PI)."""
        # Add only Co-PIs (no PI)
        ProposalInvestigator.objects.create(
            proposal=self.proposal,
            investigator=self.inv1,
            role='CO_PI'
        )
        ProposalInvestigator.objects.create(
            proposal=self.proposal,
            investigator=self.inv2,
            role='CO_PI'
        )
        
        # Should fail validation
        with self.assertRaises(ValidationError) as cm:
            self.proposal.clean()
        
        self.assertIn("must have exactly one Principal Investigator", str(cm.exception))
