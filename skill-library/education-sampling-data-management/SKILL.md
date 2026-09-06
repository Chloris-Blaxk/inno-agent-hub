---
name: education-sampling-data-management
category: 教学辅导
subject: 跨学科
kind: 教研科研
description: Use before collecting education research data, or when planning samples, recruitment, participant tracking, school/class/teacher/student data structures, consent, anonymization, data dictionaries, file naming, secure storage, and dataset readiness. This second-layer execution skill supports quantitative, qualitative, mixed-methods, experimental, action research, DBR, program evaluation, psychometric, and learning analytics workflows.
metadata:
  short-description: Plan education samples, recruitment, anonymization, and data management
---

# Education Sampling Data Management

## Goal

Create a practical sampling, recruitment, participant-ID, consent, anonymization, and data-management plan for education research.

## Use After

Use after a study path and basic research design are selected:

- `education-quantitative-study-design`
- `education-qualitative-study-design`
- `education-mixed-methods-design`
- `education-action-research-design`
- `education-design-based-research`
- `education-program-evaluation`
- `education-psychometric-scale-development`
- `education-learning-analytics-design`

Do not expose the skill name to users. Present it as "样本与数据管理设计".

## Inputs

- Paper type and research design
- Target participants: students, teachers, parents, administrators, schools/classes
- Education level, subject, grade, region
- Data sources: surveys, tests, interviews, observations, student work, logs, documents
- Whether minors are involved
- Access constraints: school permission, class access, teacher cooperation
- Data sensitivity and sharing requirements

## Workflow

1. Identify sampling unit:
   - student
   - teacher
   - class
   - school
   - lesson/session
   - artifact/document
   - platform account/log
2. Select sampling strategy:
   - convenience
   - purposive
   - stratified
   - cluster/class-based
   - random
   - snowball
   - maximum variation
   - theoretical sampling for grounded theory
3. Define inclusion/exclusion criteria.
4. Estimate sample size needs:
   - quantitative: power/precision/model complexity
   - qualitative: information richness/saturation
   - psychometric: item-to-participant and factor analysis needs
   - meta/log data: unit count and time window
5. Design recruitment workflow:
   - school/administrator permission
   - teacher coordination
   - parent/guardian consent if minors
   - student assent when appropriate
   - participant reminders
6. Create anonymized participant ID scheme.
7. Create data dictionary and linking table plan.
8. Define secure storage, file naming, versioning, and access control.
9. Plan missing-data and attrition tracking.
10. Output a data-management package.

## Tool Calls

Dependency policy: inspect the current environment first. Do not install packages, clone repositories, or change the user's environment without explicit approval. Prefer a project-local Python virtual environment or R library, and record package versions used for reproducibility.

### Sample Size and Power

```text
G*Power: https://www.psychologie.hhu.de/arbeitsgruppen/allgemeine-psychologie-und-arbeitspsychologie/gpower
```

R packages:

```r
install.packages(c("pwr", "simr", "WebPower"))
```

### Participant/Data Tracking

```text
Excel / Google Sheets
Airtable: https://www.airtable.com/
REDCap: https://www.project-redcap.org/
Notion: https://www.notion.so/
Open Science Framework: https://osf.io/
```

### Secure Survey/Data Collection

```text
Qualtrics: https://www.qualtrics.com/
问卷星: https://www.wjx.cn/
Google Forms: https://forms.google.com/
REDCap: https://www.project-redcap.org/
```

## Output Format

### 1. Sampling Plan

| Item | Decision |
|---|---|
| Target population |  |
| Sampling unit |  |
| Sampling strategy |  |
| Inclusion criteria |  |
| Exclusion criteria |  |
| Expected sample size |  |
| Minimum acceptable sample |  |
| Recruitment channel |  |
| Key feasibility risk |  |

### 2. Recruitment Workflow

| Step | Actor | Material Needed | Output |
|---|---|---|---|
| School permission | Researcher/school admin | Study brief | Permission |
| Teacher coordination | Researcher/teacher | Schedule and task description | Class access |
| Parent/guardian consent | Parent/guardian | Consent form | Consent record |
| Student assent | Student | Age-appropriate explanation | Assent record |
| Data collection | Researcher/teacher | Survey/test/interview protocol | Dataset |

### 3. Participant ID Scheme

Use anonymous IDs, not names.

Example:

| Entity | ID Pattern | Example |
|---|---|---|
| School | S + two digits | S01 |
| Class | S + school + C + class | S01C02 |
| Student | S + school + C + class + ST + number | S01C02ST015 |
| Teacher | S + school + T + number | S01T003 |
| Interview | INT + participant ID + date | INT-S01T003-20260609 |

### 4. Data Dictionary

| Variable Name | Label | Level | Type | Allowed Values | Missing Code | Source | Notes |
|---|---|---|---|---|---|---|---|

Example levels:

- student-level
- teacher-level
- class-level
- school-level
- session-level
- item-level
- artifact-level

### 5. Dataset Inventory

| Dataset/File | Unit of Analysis | Key ID | Sensitive Fields | Storage Location | Access |
|---|---|---|---|---|---|

### 6. Consent and Ethics Checklist

| Check | Status | Notes |
|---|---|---|
| School permission | Pending/Done |  |
| Parent/guardian consent | Pending/Done/Not needed |  |
| Student assent | Pending/Done/Not needed |  |
| Teacher consent | Pending/Done/Not needed |  |
| Data anonymization | Pending/Done |  |
| AI/tool data policy checked | Pending/Done/Not relevant |  |
| Withdrawal option explained | Pending/Done |  |

## Recommended File Naming

```text
projectname_dataset_unit_date_version.ext
aiwriting_survey_student_20260609_v01.xlsx
aiwriting_interview_teacher_20260609_v01.docx
aiwriting_score_student_prepost_20260609_v01.xlsx
```

## Data-Linking Rule

Maintain two layers:

1. Analysis datasets with anonymous IDs only.
2. Separate identity linking table stored securely and not included in analysis exports.

Never put real names, phone numbers, parent contacts, student numbers, or school-identifying details in the analysis dataset unless there is a clear approved reason.

## Education-Specific Risks

- Minors require extra consent/assent attention.
- Class-based sampling often creates nested data; record class/school IDs.
- Intervention studies need attrition tracking by group.
- Teacher-collected data may create pressure on students; make voluntariness explicit.
- AI platform logs may include sensitive prompts, writing samples, or account identifiers; anonymize text artifacts carefully.

## Quality Rules

- Every dataset must have a unique participant or unit ID.
- Record group assignment, time point, and data source early; do not reconstruct later from memory.
- Keep raw data, cleaned data, and analysis data separate.
- Use consistent missing-value codes.
- Record all data exclusions with reasons.
- For multi-level education data, preserve school/class/teacher/student hierarchy.

## User-Facing Closure

End by asking for the most important missing feasibility detail:

```text
接下来需要确认一个实际条件：你预计能接触几个班、多少名学生/教师？我可以据此帮你把样本表、匿名编号规则和数据字典做成可直接采集的版本。
```
