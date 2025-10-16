# Grant Management System: Requirements & Technical Specification (MVP)

This document outlines the requirements, revised data model, simplified architecture, and deployment strategy for the university's digitized grant management system for the GCIR division.

---

## I. Initial Project Checklist (Conceptual)

1. Define the core **data model** (entities, attributes, relationships) using GCIR Code as the primary key.
2. Detail the **User Interface (UI)** and **User Experience (UX)** for the primary GCIR office staff users (focusing on the Django Admin).
3. Specify the logic and constraints for the **GCIR Code (Proposal ID)** generation.
4. Map the complete **Proposal Lifecycle** to discrete, trackable status states and associated actions.
5. Outline **reporting and search capabilities** for efficient grant tracking and changelog generation.
6. Determine the initial, Python-centric **technology stack** for fast development. 🚀
7. Plan for **data security, validation, and integrity** with minimal deployment overhead.

---

## II. Requirements Documentation

### 1. Functional Requirements (FR)

| ID | Requirement Description | Priority |
| :--- | :--- | :--- |
| FR1 | The system **MUST** allow GCIR staff to create a new **Project Proposal** record via a structured form. | High |
| FR2 | The system **MUST** automatically **generate a unique GCIR Code (which is the Proposal ID)** upon successful creation of a new Project Proposal record, based on the specified components. | High |
| FR3 | The system **MUST** allow GCIR staff to **view and edit** all details of an existing Project Proposal using the GCIR Code/ID. | High |
| FR4 | The system **MUST** facilitate **status transitions** of a Project Proposal through its lifecycle stages. | High |
| FR5 | The system **MUST** enable the GCIR staff to **search and filter** proposals based on GCIR Code, PI Name/PSRN, Project Title, Department, Status, and Funding Agency. | Medium |
| FR6 | The system **MUST** allow the GCIR staff to **upload and associate documents** (e.g., Sanction Letter) with a Project Proposal record. | Medium |
| FR7 | The system **MUST** provide a **dashboard/summary view** displaying key metrics. | Medium |
| FR8 | The system **MUST** record the **Sanction Letter Number** and **Final Sanctioned Cost** upon status change to 'Approved/Sanctioned'. | High |

### 2. Data Requirements (DR)

| ID | Requirement Description | Constraint |
| :--- | :--- | :--- |
| DR1 | **Project Proposal** Record Fields: Must store all required form fields (Type, Dept, Funding Agency, Title, all dates, Status, Sanction Letter Number, etc.). | Varied (String, Date, Integer) |
| DR2 | **Principal Investigator (PI)** Data: Must store a unique **PSRN** and **Name** for the PI, and a list of Co-PIs. | PI/Co-PIs must be linked to the Proposal (1:1 or 1:Many) |
| DR3 | **GCIR Code (Proposal ID)**: Must store and enforce the uniqueness of the generated code (e.g., **G-2025-CS-IND-001**). | String; Primary Key, Unique |
| DR4 | **Lookup Data:** Must maintain tables/lists for controlled vocabulary fields like **Department** and **Project Type**. | Enumerated List |

### 3. Reporting & Audit Requirements (AR)

| ID | Requirement Description | Priority |
| :--- | :--- | :--- |
| AR1 | The system **MUST** maintain an **Audit Trail/Changelog** recording all modifications to the core `Proposal` data (e.g., status changes, title edits, cost updates). | High |
| AR2 | The system **MUST** generate a **Weekly Change Log Report** accessible to GCIR staff. | Medium |
| AR3 | The Weekly Change Log Report **MUST** clearly detail all Proposal records that were **Created, Modified, or Deleted** within the current reporting week (e.g., Monday 12:00 AM to Sunday 11:59 PM). | High |
| AR4 | The report should include the **GCIR Code**, the **Field Changed** (e.g., 'Status'), the **Previous Value**, the **New Value**, and the **User** and **Timestamp** of the change. | High |
| | *Implementation Note:* A Django package like `django-simple-history` is the recommended path to fulfill these audit requirements with minimal code effort. | |

---

## III. Simplified Technical Specification

### 1. Revised Data Model (Database Schema Outline) 💾

The primary key of the `Proposal` table is now the `GCIR_Code`.

| Table Name | Key Fields | Key Relationships | Notes |
| :--- | :--- | :--- | :--- |
| **`Proposal`** | **`GCIR_Code` (PK)**, `Title`, `ProjectType`, `FundingAgency`, `Status`, `ApplicationDate`, `SanctionLetterNumber`, `FinalCost` | FK to `PI_PSRN` (from `Investigator`), FK to `DepartmentID` | Core entity. GCIR Code serves as the unique Proposal ID. |
| **`Investigator`** | **`PSRN` (PK)**, `Name`, `DepartmentID` (FK) | N/A | Stores faculty data. |
| **`ProposalInvestigator`** | `GCIR_Code` (FK), `InvestigatorPSRN` (FK), **`Role` (PI/CoPI)** | Links PIs and Co-PIs to proposals. | Resolves the Many-to-Many relationship. |
| **`Department`** | `DepartmentID` (PK), `Code` (e.g., CS), `Name` | N/A | Lookup table for controlled vocabulary. |

### 2. GCIR Code Generation Logic (ID)

The GCIR Code is the Primary Key. It must be generated programmatically on saving a new proposal.

| Component | Example | Source/Logic |
| :--- | :--- | :--- |
| **Campus Identifier** | `G` | Static value for Goa campus. |
| **Year** | `2025` | Current **Academic/Financial Year**. |
| **Project Type** | `IND` | Abbreviated code from the `ProjectType` lookup (e.g., Industry $\rightarrow$ IND). |
| **Department** | `CS` | Abbreviated code from the `Department` lookup associated with the **PI**. |
| **Serial Number** | `001` | **A three-digit sequence, unique for the combination of (Campus, Year, Type, Department).** This counter must be reset for each new combination. |
| **Format** | `G-2025-CS-IND-001` | Concatenate components with a hyphen delimiter. |

### 3. Proposed Architecture (MVP Focus)

| Layer | Recommended Technology | Rationale for Speed & Ease |
| :--- | :--- | :--- |
| **Backend/API** | **Django (Python)** | Leverage Python skills and Django's built-in **Admin Interface** for immediate user functionality. |
| **Frontend/UI** | **Django Templates (Jinja2)** | Server-side rendering is faster to develop and requires minimal to no JavaScript expertise. |
| **Database** | **SQLite** | **Zero database setup/management.** A single-file database that's perfect for low-user, no-scaling projects. |

### 4. Proposal Workflow/State Machine

| Status ID | Status Name | Notes |
| :--- | :--- | :--- |
| **S1** | **Draft/Application Received** | Initial state. GCIR Code generated. |
| **S2** | **Permission Letter Prepared** | Internal document is finalized. |
| **S3** | **Submitted to Funding Agency** | Proposal is formally sent out. |
| **S4** | **Under Review/Presentation** | Optional intermediate state. |
| **S5** | **Approved/Sanctioned** | **Crucial state:** Triggers entry of Sanction Letter details. |
| **S6** | **Rejected/Closed** | Terminal state. |
| **S7** | **Funds Disbursed/Accounts Handoff** | Terminal state indicating successful completion of GCIR's workflow. |

* **Successful Path:** S1 $\rightarrow$ S2 $\rightarrow$ S3 $\rightarrow$ S4 $\rightarrow$ S5 $\rightarrow$ S7
* **Rejection Path:** Can transition to S6 from S3, S4, or S5.

---

## IV. Validation and Next Step

**Validation:** The streamlined architecture prioritizes the team's Python comfort and speed-to-deployment by utilizing **SQLite** and the **Django Admin**. The `GCIR_Code` is correctly implemented as the primary ID. All functional requirements, including the new changelog, are accounted for.

**Next Step:** Begin the **Implementation Phase** by setting up the Django project, defining the **Models** (`Proposal`, `Investigator`, `Department`), and writing the logic for the **GCIR Code generation** (FR2).
