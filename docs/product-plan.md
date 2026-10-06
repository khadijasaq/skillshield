# SkillShield Product Implementation Plan

## 1. Objective

This plan defines the implementation required to produce a **working end-to-end SkillShield prototype**.

The final prototype must allow a user to:

```text
Launch SkillShield
       ↓
Upload a downloaded Agentic Skill
       ↓
Run assessment
       ↓
View D/S/R/P analysis
       ↓
View findings and evidence
       ↓
Receive an overall security recommendation
```

The implementation must prioritize a simple, product-independent architecture.

---

# 2. Development Strategy

Implementation will proceed in controlled milestones.

Each milestone must:

1. implement only its defined scope,
2. preserve the product-independent architecture,
3. avoid speculative abstractions,
4. include tests,
5. pass linting,
6. provide a clear implementation report,
7. be validated before the next milestone begins.

The final objective is not merely a library.

The final objective is a **usable local prototype**.

---

# 3. Milestone Overview

```text
P0  Core Foundation
        ↓
P1  Skill Ingestion
        ↓
P2  Static Analysis
        ↓
P3  Controlled Execution + Runtime
        ↓
P4  D/S/R/P Conformance + Assessment
        ↓
P5  End-to-End Application Interface
        ↓
P6  Functional UI
        ↓
★ WORKING END-TO-END PROTOTYPE ★
        ↓
P7  Research Evaluation
        ↓
P8  Optional Integrations
```

P0–P6 are required to produce the working prototype.

P7 and P8 happen after the prototype is usable.

---

# 4. P0 — Product-Independent Core Foundation

## Goal

Establish the minimal security/conformance foundation.

## Implement

* Skill model,
* Capability model,
* Evidence model,
* Security events,
* D/S/R/P representation,
* finding model,
* severity,
* assessment model,
* conformance engine.

## Requirements

The core must not depend on:

* vuln-agentic-skills-app,
* OpenClaw,
* Dify,
* n8n,
* GitHub,
* SkillsMP,
* any benchmark dataset.

## Validation

* unit tests,
* model validation,
* schema validation,
* conformance tests,
* linting.

## Done When

The core can represent and compare capability evidence without any application-specific dependency.

---

# 5. P1 — Generic Skill Ingestion

## Goal

Allow SkillShield to receive already-downloaded skills.

## Supported Inputs

Exactly:

```text
1. Local directory
2. ZIP/archive
```

## Implement

* input validation,
* directory ingestion,
* archive ingestion,
* archive safety validation,
* safe extraction,
* file inventory,
* metadata discovery,
* declaration discovery,
* content digest,
* provenance metadata,
* SkillArtifact,
* canonical Skill translation.

## Security Requirements

Handle at least:

* path traversal,
* malformed archives,
* unsupported archives,
* invalid skill structure,
* missing declaration,
* malformed declaration.

## Important

Do not implement:

* GitHub downloading,
* SkillsMP downloading,
* marketplace APIs,
* remote network retrieval,
* application adapters.

## Validation

The same skill supplied as a directory and ZIP must result in equivalent canonical representations.

---

# 6. P2 — Static Analysis

## Goal

Generate static capability evidence S.

## Implement

* source discovery,
* supported source-file handling,
* capability detectors,
* static evidence,
* capability normalization,
* analysis result model.

## Output

```text
Skill
 ↓
Static Analyzer
 ↓
S + Evidence
```

Example:

```text
filesystem.read

Evidence:
    file: skill.py
    location: ...
    detector: ...
```

## Constraint

Static analysis indicates possible behavior.

It must not claim that static detection proves runtime execution.

## Validation

Create representative skills demonstrating:

* declared capability,
* undeclared capability,
* multiple capabilities,
* no detectable capability,
* unsupported source construct,
* analysis failure.

---

# 7. P3 — Controlled Execution and Runtime Monitoring

## Goal

Generate runtime capability evidence R.

## Implement

* execution configuration,
* controlled subprocess execution,
* timeout,
* termination,
* working directory,
* runtime event monitoring,
* runtime capability mapping,
* execution result,
* execution failure handling.

## Required Safety Review

Before testing malicious datasets at scale, explicitly assess:

* process isolation,
* filesystem access,
* network access,
* environment variables,
* credentials,
* child processes,
* resource usage,
* timeout,
* termination.

## Important

Do not call the mechanism a secure sandbox unless the security guarantees have been demonstrated.

## Validation

Create controlled test skills that demonstrate:

* expected runtime capability,
* undeclared runtime capability,
* policy-relevant capability,
* timeout,
* execution failure.

---

# 8. P4 — D/S/R/P Conformance and Assessment

## Goal

Combine all evidence into a security assessment.

## Implement

At minimum:

```text
S - D
R - D
S - R
R - S
R - P
```

Generate structured findings.

## Initial Finding Types

```text
UNDECLARED_CAPABILITY
STATIC_RUNTIME_MISMATCH
POLICY_VIOLATION
INVALID_DECLARATION
ANALYSIS_FAILURE
EXECUTION_FAILURE
```

## Severity

Implement deterministic severity rules.

The exact rules must be documented and tested.

## Assessment

Produce:

```text
NO ISSUES FOUND
REVIEW BEFORE USE
DO NOT USE
```

## Important

The assessment must not claim:

```text
"This skill is malicious."
```

unless a future, separately justified classification system explicitly supports such a claim.

The initial product reports evidence and risk-oriented recommendations.

## Validation

At least the following must work:

```text
Clean skill
      ↓
NO ISSUES FOUND

Undeclared behavior
      ↓
Finding

Policy violation
      ↓
Finding + appropriate recommendation

Static/runtime mismatch
      ↓
Finding
```

---

# 9. P5 — End-to-End Application Interface

## Goal

Connect the complete assessment pipeline into one callable application workflow.

This milestone is mandatory before UI development.

## Implement

A simple application interface that can:

```text
submit skill
      ↓
start assessment
      ↓
execute complete pipeline
      ↓
return assessment
```

The interface should support both:

```text
local directory
ZIP/archive
```

## Preferred First Interface

A simple CLI/local application interface is preferred.

Conceptually:

```text
skillshield scan ./my-skill
```

and:

```text
skillshield scan ./my-skill.zip
```

## Required Result

The command/application must perform the entire pipeline:

```text
Input
 ↓
Ingestion
 ↓
Declaration
 ↓
Static
 ↓
Runtime
 ↓
D/S/R/P
 ↓
Findings
 ↓
Assessment
```

## Validation

A complete assessment must be generated from a single command/workflow without manually calling internal modules.

This establishes the backend end-to-end path before adding the UI.

---

# 10. P6 — Functional SkillShield UI

## Goal

Create the actual user-facing prototype.

This milestone is required.

The UI must allow the user to upload a downloaded skill and receive the results of the SkillShield assessment.

---

## 10.1 User Flow

```text
Open SkillShield
       ↓
Upload Skill
       ↓
Select ZIP / supported folder
       ↓
Start Assessment
       ↓
Processing
       ↓
Assessment Complete
       ↓
View Results
```

---

## 10.2 Upload

The UI must support the product's defined input formats.

At minimum:

```text
ZIP/archive upload
```

If the selected local UI technology supports directory selection appropriately, also support:

```text
Local skill directory
```

The implementation must not compromise the security boundary merely to support directory upload.

---

## 10.3 Assessment Screen

The UI should show an assessment state such as:

```text
Preparing skill...
Analyzing declaration...
Running static analysis...
Running controlled execution...
Correlating evidence...
Generating assessment...
```

The exact presentation may be simple.

---

## 10.4 Results Screen

The result screen must show:

### Overall recommendation

```text
NO ISSUES FOUND
REVIEW BEFORE USE
DO NOT USE
```

### Capability summary

```text
Declared capabilities
Static capabilities
Runtime capabilities
Policy permissions
```

### Findings

Each finding should show:

* severity,
* type,
* capability,
* explanation.

### Evidence

The user should be able to inspect relevant evidence.

For example:

```text
Policy Violation

Capability:
network.egress

Declared:
No

Static:
Yes

Runtime:
Yes

Policy:
DENY

Source:
skill.py
```

---

# 11. UI Architecture Rules

The UI must remain thin.

```text
UI
 ↓
Application Interface
 ↓
SkillShield Assessment Pipeline
 ↓
Security Core
```

The UI must not implement:

* static detectors,
* runtime detection,
* D/S/R/P comparisons,
* policy decisions,
* severity rules,
* assessment recommendation rules.

Those remain in the backend/core.

---

# 12. P6 End-to-End Acceptance Criteria

P6 is complete only when all of the following work:

### AC1 — Application Starts

A developer/user can launch SkillShield locally.

### AC2 — UI Opens

The user can access the SkillShield interface.

### AC3 — Skill Upload

The user can upload a supported downloaded skill.

### AC4 — Assessment Starts

The user can initiate an assessment without manually invoking internal modules.

### AC5 — Full Pipeline Runs

The system executes:

```text
Ingestion
 → Declaration
 → Static
 → Runtime
 → D/S/R/P
 → Findings
 → Assessment
```

### AC6 — Results Display

The UI displays the final recommendation.

### AC7 — Findings Display

The UI displays detected findings.

### AC8 — Evidence Display

The user can inspect evidence for findings.

### AC9 — ZIP Works

A downloaded ZIP skill can be assessed.

### AC10 — Local Skill Works

A supported local skill directory can be assessed.

### AC11 — Clean Example Works

A known clean test skill produces the expected clean result.

### AC12 — Problematic Example Works

A controlled skill with an intentionally introduced discrepancy produces the expected finding.

### AC13 — No Application Dependency

The prototype runs without `vuln-agentic-skills-app`.

---

# 13. Prototype Demonstration

At the end of P6, the team must be able to demonstrate:

```text
                    SKILLSHIELD

             Assess Agentic Skill
                  Before Use

               [Upload Skill]

                     ↓

                my_skill.zip

                     ↓

                  [Assess]

                     ↓

              Running Analysis...

                     ↓

          ┌─────────────────────┐
          │ REVIEW BEFORE USE   │
          └─────────────────────┘

          Declared:       2
          Static:         5
          Runtime:        4
          Policy issues:  2

          Findings:
          • Undeclared capability
          • Policy violation

          [View Evidence]
```

This demonstration is the required proof that SkillShield is an actual working prototype rather than only a research library.

---

# 14. P7 — Research Evaluation

Only after P0–P6 produce a working prototype should large-scale research evaluation begin.

## Candidate datasets

Potential sources:

* Trail of Bits Overtly Malicious Skills,
* MalSkillBench,
* MaliciousSkillBench,
* SkillTrustBench.

Dataset labels must be inspected and verified before use.

---

# 15. Evaluation Protocol

For every evaluation:

1. identify dataset version/commit,
2. record provenance,
3. separate development and evaluation data,
4. define positive criteria before evaluation,
5. freeze scanner configuration,
6. freeze policy configuration,
7. record execution configuration,
8. record isolation settings,
9. record timeout/resource limits,
10. preserve raw results.

---

# 16. Research Metrics

Where ground-truth labels permit:

* precision,
* recall,
* F1,
* false-positive rate,
* false-negative rate,
* coverage,
* scanner failure rate,
* execution failure rate,
* runtime overhead,
* scalability.

---

# 17. Ablation Study

Evaluate:

```text
A1  Declaration only

A2  Static only

A3  Runtime only

A4  Static + Runtime

A5  Static + Runtime + Policy

Full
    Declaration + Static + Runtime + Policy
```

The purpose is to determine the contribution of each evidence source.

---

# 18. Baselines

Where technically appropriate:

### Baseline 1

Declaration-only trust.

### Baseline 2

Static-only assessment.

### Baseline 3

Existing external security scanners.

All comparisons must use a documented common evaluation protocol.

No dataset-specific detection logic should be introduced into SkillShield solely to improve benchmark performance.

---

# 19. P8 — Future Integrations

After the product and research evaluation are stable, optional integrations may be added.

## Source integrations

```text
GitHub
SkillsMP
Other marketplaces
Other repositories
```

Flow:

```text
Remote Source
     ↓
Source Adapter
     ↓
SkillArtifact
     ↓
Existing SkillShield Pipeline
```

## Host integrations

Potential future support:

```text
OpenClaw
Dify
n8n
Other Agentic Platforms
```

These remain optional.

---

# 20. Role of vuln-agentic-skills-app

`vuln-agentic-skills-app` is not part of the SkillShield product.

It may be used for:

* controlled development,
* evaluation,
* representative examples,
* test cases.

SkillShield must work without it.

The product architecture must never require it.

---

# 21. Development Rules for Claude

Claude must:

1. Read the current specification before implementation.
2. Implement only the current milestone.
3. Avoid unrelated changes.
4. Avoid speculative abstractions.
5. Keep the core product-independent.
6. Keep UI logic separate from security logic.
7. Keep testbed-specific logic out of production core.
8. Test every milestone.
9. Run linting.
10. Run the complete relevant test suite.
11. Provide a changed-files summary.
12. Provide validation results.
13. Report known limitations honestly.
14. Do not modify `.gitignore` merely to expose tests/examples unless explicitly instructed.
15. Do not perform Git operations unless explicitly instructed.
16. Do not start the next milestone until the current milestone passes validation.

---

# 22. Batch Strategy

Implementation should be performed in controlled batches.

Recommended grouping:

## Batch 1

```text
P0 + P1
Core foundation
+
Skill ingestion
```

Validate completely.

## Batch 2

```text
P2
Static analysis
```

Validate completely.

## Batch 3

```text
P3
Controlled execution
+
Runtime monitoring
```

Validate completely.

## Batch 4

```text
P4
D/S/R/P
+
Findings
+
Assessment
```

Validate completely.

## Batch 5

```text
P5
Complete application interface
```

Validate complete end-to-end backend workflow.

## Batch 6

```text
P6
Functional UI
```

Validate actual upload → assessment → results workflow.

Only after Batch 6 should the prototype be declared complete.

---

# 23. Final Prototype Definition of Done

SkillShield's first working prototype is complete only when:

```text
✓ User launches SkillShield

✓ User uploads a downloaded skill

✓ ZIP input works

✓ Supported local skill input works

✓ Skill is ingested safely

✓ Declaration is extracted

✓ Static analysis runs

✓ Controlled execution runs

✓ Runtime monitoring runs

✓ D/S/R/P are generated

✓ Findings are generated

✓ Severity is calculated

✓ Assessment is generated

✓ Results are available through the application interface

✓ Results are displayed in the UI

✓ Evidence can be inspected

✓ Clean test case works

✓ Discrepancy test case works

✓ SkillShield does not depend on vuln-agentic-skills-app

✓ Security limitations are documented
```

---

# 24. Final Research/Product Separation

The project has two distinct outcomes.

## Product outcome

```text
Downloaded Skill
      ↓
SkillShield
      ↓
Security Assessment
```

The user can actually use the prototype.

## Research outcome

```text
D + S + R + P
      ↓
Conformance Model
      ↓
Evaluation
      ↓
Research Evidence
```

The research evaluates whether the combined approach provides measurable value.

The product must remain usable independently of the research datasets.

---

# 25. Final Product Vision

The final first-version user experience is:

```text
┌──────────────────────────────────────────────┐
│                  SKILLSHIELD                 │
│                                              │
│       Assess an Agentic Skill Before Use     │
│                                              │
│              [ Upload Skill ]                │
│                                              │
└──────────────────────────────────────────────┘

                     ↓

              Skill Assessment

                     ↓

       ┌──────────────────────────┐
       │    REVIEW BEFORE USE     │
       └──────────────────────────┘

       Declared capabilities: 2
       Static capabilities:   5
       Runtime capabilities:  4
       Policy violations:     2

       Findings
       ────────────────────────
       HIGH
       Policy violation
       network.egress

       MEDIUM
       Undeclared capability
       filesystem.read

       [View Evidence]
```

The product should therefore satisfy the simple promise:

> **Upload a downloaded Agentic Skill, let SkillShield analyze what it declares, what its code indicates, what it does under controlled execution, and what policy permits, and receive an evidence-based security assessment.**
