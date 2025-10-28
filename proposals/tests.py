from django.test import TestCase
from django.db import IntegrityError
from django.core.exceptions import ValidationError

from .models import Department, ProjectType, Proposal, Investigator, ProposalInvestigator, FundingAgency, ExternalInvestigator
from .services import generate_gcir_code, generate_external_investigator_code


class GCIRCodeGeneratorTest(TestCase):
    """Test GCIR code generation logic."""

    def setUp(self):
        """Create test fixtures: Department and ProjectType."""
        self.dept_cs = Department.objects.create(code='CS', name='Computer Science')
        self.dept_me = Department.objects.create(code='ME', name='Mechanical Engineering')
        self.type_ind = ProjectType.objects.create(code='IND', name='Industry')
        self.type_gov = ProjectType.objects.create(code='GOV', name='Government')
        self.agency = FundingAgency.objects.create(code='NSF', name='National Science Foundation')

    def test_generate_first_gcir_code(self):
        """Test generating the first GCIR code for a department/type combination."""
        code = generate_gcir_code(
            project_type_id=self.type_ind.id,  # type: ignore
            department_id=self.dept_cs.id,  # type: ignore
            year=2025,
            funding_agency_id=self.agency.id  # type: ignore
        )
        self.assertEqual(code, 'G-2025-CS-IND-NSF-0001')

    def test_generate_second_gcir_code_increments_serial(self):
        """Test that second code increments the serial number."""
        # Create first proposal
        Proposal.objects.create(
            gcir_code='G-2025-CS-IND-NSF-0001',
            title='First Proposal',
            department=self.dept_cs,
            project_type=self.type_ind,
            funding_agency=self.agency,
        )

        # Generate second code
        code = generate_gcir_code(
            project_type_id=self.type_ind.id,  # type: ignore
            department_id=self.dept_cs.id,  # type: ignore  # type: ignore
            year=2025,
            funding_agency_id=self.agency.id  # type: ignore
        )
        self.assertEqual(code, 'G-2025-CS-IND-NSF-0002')

    def test_separate_sequences_for_different_department(self):
        """Test that different departments have separate serial sequences."""
        # Create a CS proposal
        Proposal.objects.create(
            gcir_code='G-2025-CS-IND-NSF-0001',
            title='CS Proposal',
            department=self.dept_cs,
            project_type=self.type_ind,
            funding_agency=self.agency,
        )

        # Generate code for ME department (should start at 0001)
        code = generate_gcir_code(
            project_type_id=self.type_ind.id,  # type: ignore  # type: ignore
            department_id=self.dept_me.id,  # type: ignore  # type: ignore
            year=2025,
            funding_agency_id=self.agency.id  # type: ignore
        )
        self.assertEqual(code, 'G-2025-ME-IND-NSF-0001')

    def test_separate_sequences_for_different_project_type(self):
        """Test that different project types have separate serial sequences."""
        # Create an IND proposal
        Proposal.objects.create(
            gcir_code='G-2025-CS-IND-NSF-0001',
            title='Industry Proposal',
            department=self.dept_cs,
            project_type=self.type_ind,
            funding_agency=self.agency,
        )

        # Generate code for GOV type (should start at 0001)
        code = generate_gcir_code(
            project_type_id=self.type_gov.id,  # type: ignore
            department_id=self.dept_cs.id,  # type: ignore
            year=2025,
            funding_agency_id=self.agency.id  # type: ignore
        )
        self.assertEqual(code, 'G-2025-CS-GOV-NSF-0001')

    def test_separate_sequences_for_different_year(self):
        """Test that different years have separate serial sequences."""
        # Create a 2025 proposal
        Proposal.objects.create(
            gcir_code='G-2025-CS-IND-NSF-0001',
            title='2025 Proposal',
            department=self.dept_cs,
            project_type=self.type_ind,
            funding_agency=self.agency,
        )

        # Generate code for 2026 (should start at 0001)
        code = generate_gcir_code(
            project_type_id=self.type_ind.id,  # type: ignore
            department_id=self.dept_cs.id,  # type: ignore
            year=2026,
            funding_agency_id=self.agency.id  # type: ignore
        )
        self.assertEqual(code, 'G-2026-CS-IND-NSF-0001')

    def test_generates_many_codes_without_duplicates(self):
        """Test that generating multiple codes in sequence produces no duplicates."""
        codes = set()
        for i in range(1, 6):
            code = generate_gcir_code(
                project_type_id=self.type_ind.id,  # type: ignore
                department_id=self.dept_cs.id,  # type: ignore
                year=2025,
                funding_agency_id=self.agency.id  # type: ignore
            )
            # Create a proposal to ensure next call increments
            Proposal.objects.create(
                gcir_code=code,
                title=f'Proposal {i}',
                department=self.dept_cs,
                project_type=self.type_ind,
                funding_agency=self.agency,
            )
            codes.add(code)

        # Should have 5 unique codes
        self.assertEqual(len(codes), 5)
        expected_codes = {
            'G-2025-CS-IND-NSF-0001',
            'G-2025-CS-IND-NSF-0002',
            'G-2025-CS-IND-NSF-0003',
            'G-2025-CS-IND-NSF-0004',
            'G-2025-CS-IND-NSF-0005',
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
        self.agency = FundingAgency.objects.create(code='NSF', name='National Science Foundation')

    def test_proposal_creation_auto_generates_gcir_code(self):
        """Test that creating a proposal without gcir_code auto-generates one."""
        proposal = Proposal.objects.create(
            title='Test Proposal',
            department=self.dept,
            project_type=self.type_proj,
            funding_agency=self.agency,
        )
        # After save, gcir_code should be populated
        self.assertIsNotNone(proposal.gcir_code)
        self.assertTrue(proposal.gcir_code.startswith('G-'))
        self.assertIn('CS-IND', proposal.gcir_code)

    def test_proposal_with_explicit_gcir_code_is_not_overwritten(self):
        """Test that providing an explicit gcir_code is not overwritten."""
        custom_code = 'G-2025-CS-IND-NSF-0099'
        proposal = Proposal.objects.create(
            gcir_code=custom_code,
            title='Custom Code Proposal',
            department=self.dept,
            project_type=self.type_proj,
            funding_agency=self.agency,
        )
        # Should keep the custom code
        self.assertEqual(proposal.gcir_code, custom_code)


class ProposalPIValidationTest(TestCase):
    """Test that proposals enforce exactly one PI per proposal."""

    def setUp(self):
        """Create test fixtures."""
        self.dept = Department.objects.create(code='CS', name='Computer Science')
        self.type_proj = ProjectType.objects.create(code='IND', name='Industry')
        self.agency = FundingAgency.objects.create(code='NSF', name='National Science Foundation')
        self.inv1 = Investigator.objects.create(psrn='INV001', name='Dr. Alice', department=self.dept)
        self.inv2 = Investigator.objects.create(psrn='INV002', name='Dr. Bob', department=self.dept)
        self.inv3 = Investigator.objects.create(psrn='INV003', name='Dr. Carol', department=self.dept)

        # Create a proposal
        self.proposal = Proposal.objects.create(
            title='Test Proposal',
            department=self.dept,
            project_type=self.type_proj,
            funding_agency=self.agency,
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


class ExternalInvestigatorCodeGenerationTest(TestCase):
    """Test external investigator code generation and auto-generation."""

    def test_generate_first_external_investigator_code(self):
        """Test generating the first external investigator code."""
        code = generate_external_investigator_code()
        self.assertEqual(code, 'E0001')

    def test_generate_second_external_investigator_code_increments(self):
        """Test that second code increments the serial number."""
        # Create first external investigator
        ExternalInvestigator.objects.create(
            code='E0001',
            name='Dr. External 1',
            organization='External Org'
        )

        # Generate second code
        code = generate_external_investigator_code()
        self.assertEqual(code, 'E0002')

    def test_external_investigator_creation_auto_generates_code(self):
        """Test that creating an external investigator without code auto-generates one."""
        investigator = ExternalInvestigator.objects.create(
            name='Dr. Auto Generated',
            organization='External Org'
        )
        # After save, code should be populated
        self.assertIsNotNone(investigator.code)
        self.assertTrue(investigator.code.startswith('E'))
        self.assertEqual(len(investigator.code), 5)  # E0001 format

    def test_external_investigator_with_explicit_code_is_not_overwritten(self):
        """Test that providing an explicit code is not overwritten."""
        custom_code = 'E9999'
        investigator = ExternalInvestigator.objects.create(
            code=custom_code,
            name='Dr. Custom Code',
            organization='External Org'
        )
        # Should keep the custom code
        self.assertEqual(investigator.code, custom_code)

    def test_generates_many_external_investigator_codes_without_duplicates(self):
        """Test that generating multiple codes in sequence produces no duplicates."""
        codes = set()
        for i in range(1, 6):
            code = generate_external_investigator_code()
            # Create an investigator to ensure next call increments
            ExternalInvestigator.objects.create(
                code=code,
                name=f'Dr. External {i}',
                organization='External Org'
            )
            codes.add(code)

        # Should have 5 unique codes
        self.assertEqual(len(codes), 5)
        expected_codes = {
            'E0001',
            'E0002',
            'E0003',
            'E0004',
            'E0005',
        }
        self.assertEqual(codes, expected_codes)


class ProposalAdminPIValidationTest(TestCase):
    """Test PI/Co-PI validation in the admin interface."""

    def setUp(self):
        """Create test fixtures."""
        self.dept = Department.objects.create(code='CS', name='Computer Science')
        self.project_type = ProjectType.objects.create(code='IND', name='Individual Research')
        self.investigator = Investigator.objects.create(
            psrn='G0001',
            name='Dr. Test',
            email='test@university.edu',
            department=self.dept
        )
        self.proposal = Proposal.objects.create(
            title='Test Proposal',
            department=self.dept,
            project_type=self.project_type,
        )

    def test_proposal_with_one_pi_is_valid(self):
        """Test that a proposal with exactly one PI passes validation."""
        ProposalInvestigator.objects.create(
            proposal=self.proposal,
            investigator=self.investigator,
            role='PI'
        )
        # Should not raise any exception
        self.proposal.clean()  # This should pass

    def test_proposal_with_one_pi_and_multiple_copis_is_valid(self):
        """Test that a proposal with one PI and multiple Co-PIs is valid."""
        # Create PI
        ProposalInvestigator.objects.create(
            proposal=self.proposal,
            investigator=self.investigator,
            role='PI'
        )
        
        # Create external investigator for Co-PI
        ext_inv = ExternalInvestigator.objects.create(
            name='Dr. External',
            organization='External Org'
        )
        
        # Create Co-PI
        ProposalInvestigator.objects.create(
            proposal=self.proposal,
            external_investigator=ext_inv,
            role='CO_PI'
        )
        
        # Should not raise any exception
        self.proposal.clean()  # This should pass

    def test_proposal_with_no_pi_fails_validation(self):
        """Test that a proposal with no PI fails validation."""
        # Create only a Co-PI, no PI
        ProposalInvestigator.objects.create(
            proposal=self.proposal,
            investigator=self.investigator,
            role='CO_PI'
        )
        
        # Should raise validation error
        with self.assertRaises(ValidationError) as context:
            self.proposal.clean()
        
        self.assertIn('exactly one', str(context.exception).lower())

    def test_proposal_with_multiple_pis_fails_validation(self):
        """Test that a proposal with multiple PIs fails validation."""
        # Create first PI
        ProposalInvestigator.objects.create(
            proposal=self.proposal,
            investigator=self.investigator,
            role='PI'
        )
        
        # Try to create second PI (external)
        ext_inv = ExternalInvestigator.objects.create(
            name='Dr. External',
            organization='External Org'
        )
        
        ProposalInvestigator.objects.create(
            proposal=self.proposal,
            external_investigator=ext_inv,
            role='PI'
        )
        
        # Should raise validation error
        with self.assertRaises(ValidationError) as context:
            self.proposal.clean()
        
        self.assertIn('exactly one', str(context.exception).lower())
