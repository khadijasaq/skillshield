# SkillShield Product Specification

## 1. Product Definition

**SkillShield is a product-independent security assessment layer for downloaded Agentic Skills that detects discrepancies between what a skill declares, what its code indicates, what it actually does under controlled execution, and what its security policy permits.**

The system combines four sources of information:

* **D — Declared capabilities:** what the skill explicitly declares.
* **S — Statically inferred capabilities:** what the source code indicates the skill can do.
* **R — Runtime-observed capabilities:** what the skill actually does during controlled execution.
* **P — Policy-permitted capabilities:** what the configured security policy permits.

SkillShield compares these dimensions and produces security findings and an overall assessment before the skill is trusted or used.

---

# 2. Problem Statement

Agentic Skills can interact with files, networks, processes, tools, APIs, or other resources.

A skill's declared capabilities do not necessarily describe all behavior present in its implementation or all behavior that occurs during execution.

Therefore, relying only on declarations is insufficient for security assessment.

SkillShield addresses this problem by combining:

```text
Declaration
     D
     +
Static evidence
     S
     +
Runtime evidence
     R
     +
Security policy
     P
     ↓
Security / Conformance Assessment
```

The system identifies observable discrepancies between these dimensions.

SkillShield does **not** claim to mathematically prove that a skill is safe or malicious.

Instead, it produces evidence-based findings that help determine whether a skill should be trusted, reviewed, or rejected.

---

# 3. Research Contribution

The research contribution is a product-independent security and conformance layer for Agentic Skills that combines declared, statically inferred, runtime-observed, and policy-permitted capabilities to identify behavioral discrepancies before a skill is trusted.

The primary research question is:

> Can a product-independent combination of declared, statically inferred, runtime-observed, and policy-permitted capabilities identify security-relevant behavioral discrepancies in Agentic Skills before they are trusted?

The system must be designed so that the research contribution does not depend on a particular Agentic Skill host application.

---

# 4. Product Goal

The initial SkillShield prototype must provide a complete user-facing workflow:

```text
User
 ↓
Launch SkillShield
 ↓
Upload downloaded Agentic Skill
 ↓
Skill ingestion
 ↓
Declaration extraction
 ↓
Static analysis
 ↓
Controlled execution
 ↓
Runtime monitoring
 ↓
D / S / R / P correlation
 ↓
Security policy evaluation
 ↓
Findings
 ↓
Assessment
 ↓
Results displayed to user
```

The user must be able to test downloaded skills themselves.

The end-to-end prototype is therefore a mandatory product objective, not an optional future feature.

---

# 5. User Workflow

The intended user workflow is:

```text
1. User downloads an Agentic Skill.

2. User opens SkillShield.

3. User uploads:
   - a skill ZIP/archive, or
   - a supported local skill directory.

4. User starts an assessment.

5. SkillShield analyzes the skill.

6. SkillShield executes the skill in a controlled environment
   where runtime analysis is applicable.

7. SkillShield generates findings.

8. SkillShield displays:
   - overall recommendation,
   - D/S/R/P capability information,
   - findings,
   - severity,
   - evidence,
   - limitations.
```

The user should not need to interact with internal implementation details.

---

# 6. Input Scope

The initial product accepts already-downloaded skills.

Supported inputs:

```text
Local Skill Directory
        OR
ZIP / Archive
```

A skill may originally have come from:

* GitHub,
* SkillsMP,
* another marketplace,
* a personal repository,
* another source.

The origin does not affect the core assessment architecture.

### Important

SkillShield does **not** initially need to download skills from GitHub or SkillsMP.

The user provides the downloaded artifact.

Future source-download integrations may be added later.

---

# 7. Product Independence

The SkillShield core must not depend on:

* OpenClaw,
* Dify,
* n8n,
* GitHub,
* SkillsMP,
* any particular marketplace,
* any particular vulnerable application,
* any particular evaluation dataset.

The security core must operate on a generic downloaded Agentic Skill.

Future host/application integrations may be implemented as optional adapters.

---

# 8. High-Level Architecture

```text
                         ┌──────────────────────┐
                         │     SkillShield UI   │
                         │                      │
                         │ Upload Skill         │
                         │ Start Assessment     │
                         │ View Results         │
                         └──────────┬───────────┘
                                    │
                                    ↓
                         ┌──────────────────────┐
                         │ Application Interface│
                         └──────────┬───────────┘
                                    │
                                    ↓
                         ┌──────────────────────┐
                         │   Skill Ingestion    │
                         └──────────┬───────────┘
                                    │
                                    ↓
                         ┌──────────────────────┐
                         │    SkillArtifact     │
                         └──────────┬───────────┘
                                    │
                                    ↓
                         ┌──────────────────────┐
                         │    Canonical Skill   │
                         └──────────┬───────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              ↓                     ↓                     ↓
       Declaration D         Static Analysis S     Controlled Execution
                                                            │
                                                            ↓
                                                    Runtime Monitoring R
              └─────────────────────┬─────────────────────┘
                                    ↓
                         ┌──────────────────────┐
                         │ Capability Model     │
                         └──────────┬───────────┘
                                    ↓
                         ┌──────────────────────┐
                         │ Conformance Engine   │
                         └──────────┬───────────┘
                                    ↓
                         ┌──────────────────────┐
                         │ Security Policy P    │
                         └──────────┬───────────┘
                                    ↓
                         ┌──────────────────────┐
                         │ Findings + Severity  │
                         └──────────┬───────────┘
                                    ↓
                         ┌──────────────────────┐
                         │ Security Assessment  │
                         └──────────┬───────────┘
                                    ↓
                         ┌──────────────────────┐
                         │ Results / Report     │
                         └──────────────────────┘
```

The UI is a presentation and interaction layer.

Security decisions must remain in the SkillShield core.

---

# 9. Core Components

The initial product consists of the following logical components:

1. Skill ingestion
2. SkillArtifact representation
3. Canonical Skill representation
4. Declaration extraction
5. Static analysis
6. Controlled execution
7. Runtime monitoring
8. Capability normalization
9. D/S/R/P correlation
10. Policy evaluation
11. Finding generation
12. Severity classification
13. Assessment generation
14. Application interface
15. User interface

These components should be implemented as small, understandable modules.

No component should be introduced merely for hypothetical future requirements.

---

# 10. SkillArtifact

`SkillArtifact` represents the downloaded physical artifact supplied by the user.

It may contain:

* input type,
* temporary/local location,
* archive information,
* file inventory,
* provenance information available from the artifact,
* content digest,
* metadata/declaration locations,
* ingestion status.

`SkillArtifact` describes the supplied artifact.

It must not contain security assessment results.

It must not contain:

* D,
* S,
* R,
* P,
* findings,
* severity,
* assessment recommendation.

---

# 11. Canonical Skill

The canonical `Skill` represents the normalized security-domain representation.

It should contain information required by the analysis pipeline, such as:

* skill identity,
* declaration,
* declared capabilities,
* source files,
* metadata,
* entrypoint information where available.

The core must operate on canonical representations rather than source-specific structures.

The same skill supplied as:

```text
skill/
```

and:

```text
skill.zip
```

should produce an equivalent canonical representation.

---

# 12. Capability Model

A capability represents a security-relevant operation or permission.

Examples include:

```text
task.read
filesystem.read
filesystem.write
network.egress
process.execute
```

Capabilities should have stable identifiers.

Capability evidence should preserve its source where applicable:

* declaration,
* static analysis,
* runtime,
* policy.

The vocabulary must remain small and extensible.

---

# 13. Declaration — D

D represents capabilities explicitly declared by the skill.

Example:

```text
D = {
    task.read
}
```

Declaration information must be preserved as evidence.

Missing or malformed declarations must be represented as findings or structured assessment limitations rather than silently ignored.

---

# 14. Static Analysis — S

S represents capabilities inferred from the skill's source code.

Example:

```text
S = {
    task.read,
    filesystem.read,
    network.egress
}
```

Static analysis must provide evidence such as:

* file,
* location,
* detector,
* detected operation,
* normalized capability.

Static inference means:

> The source code indicates that this capability may be used.

It must not automatically mean:

> This capability definitely occurs during execution.

---

# 15. Runtime Observation — R

R represents capabilities observed during controlled execution.

Example:

```text
R = {
    task.read,
    filesystem.read
}
```

Runtime observations must preserve evidence about:

* execution,
* event,
* capability,
* relevant resource/action,
* timestamp or execution context where practical.

Runtime absence must not automatically be interpreted as proof that a capability can never occur.

Runtime results are tied to the execution scenario.

---

# 16. Policy — P

P represents the capabilities permitted by the configured security policy.

Example:

```text
P = {
    task.read,
    filesystem.read
}
```

The initial policy system should remain simple and deterministic.

The project must not attempt to create a universal policy language during the initial implementation.

---

# 17. Conformance Analysis

SkillShield compares D, S, R and P.

At minimum, the system should detect:

### Undeclared static capability

```text
S - D
```

A capability indicated by source code but not declared.

### Undeclared runtime capability

```text
R - D
```

A capability observed during execution but not declared.

### Static/runtime mismatch

```text
S - R
R - S
```

Differences between statically indicated and runtime-observed capabilities.

### Policy violation

```text
R - P
```

An observed capability that is not permitted by policy.

Additional relationships may be retained if they provide useful diagnostic evidence.

---

# 18. Findings

Findings represent observable discrepancies, violations, or analysis problems.

Examples:

```text
UNDECLARED_CAPABILITY
STATIC_RUNTIME_MISMATCH
POLICY_VIOLATION
INVALID_DECLARATION
ANALYSIS_FAILURE
EXECUTION_FAILURE
```

A finding should contain, where applicable:

* finding type,
* severity,
* capability,
* explanation,
* evidence references,
* affected source location,
* policy information.

Finding terminology must describe observable evidence.

The system must not automatically label a skill "malicious" simply because a finding exists.

---

# 19. Assessment

The assessment converts findings into an understandable security recommendation.

Initial recommendations:

```text
NO ISSUES FOUND
REVIEW BEFORE USE
DO NOT USE
```

The mapping from findings to recommendations must be deterministic and documented.

For example:

```text
No security findings
        ↓
NO ISSUES FOUND

Review-level findings
        ↓
REVIEW BEFORE USE

Critical/high-risk policy or structural violations
        ↓
DO NOT USE
```

The exact severity-to-recommendation mapping must be defined during implementation and remain deterministic.

---

# 20. Evidence and Explainability

Every important finding should be explainable.

The user should be able to understand:

```text
What was detected?
Why was it detected?
Where was it detected?
Was it declared?
Was it statically inferred?
Was it observed at runtime?
Did policy permit it?
```

Example:

```text
Finding:
    UNDECLARED_CAPABILITY

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

Evidence:
    skill.py
    relevant source location
```

This evidence-oriented design is important for both usability and research reproducibility.

---

# 21. Controlled Execution

Runtime analysis requires controlled execution.

The initial implementation may use a restricted subprocess mechanism for development and controlled testing.

However:

> A subprocess is not automatically a secure sandbox.

The implementation must explicitly document its guarantees and limitations.

Before large-scale execution of potentially malicious datasets, the project must validate:

* process isolation,
* filesystem restrictions,
* network restrictions,
* environment variables,
* credential exposure,
* child-process behavior,
* timeout enforcement,
* resource limits,
* termination behavior,
* runtime evidence collection.

If the initial mechanism cannot provide a particular guarantee, that limitation must be clearly reported.

---

# 22. User Interface

A functional UI is required for the end-to-end prototype.

The UI must allow a user to:

1. launch SkillShield,
2. upload a downloaded skill,
3. select a ZIP/archive or supported local skill,
4. start an assessment,
5. wait for processing,
6. view the final assessment,
7. inspect findings,
8. inspect D/S/R/P information,
9. inspect evidence.

The UI should be intentionally simple.

A target interface:

```text
┌──────────────────────────────────────────────┐
│                  SkillShield                 │
│                                              │
│       Assess an Agentic Skill Before Use     │
│                                              │
│          [ Upload Skill ]                    │
│                                              │
│          selected_skill.zip                  │
│                                              │
│              [ Assess ]                      │
└──────────────────────────────────────────────┘
```

After assessment:

```text
┌──────────────────────────────────────────────┐
│              SECURITY ASSESSMENT              │
│                                              │
│           REVIEW BEFORE USE                  │
│                                              │
│ Declared capabilities       2                │
│ Static capabilities         5                │
│ Runtime capabilities        4                │
│ Policy violations           2                │
│                                              │
│ Findings                                     │
│                                              │
│ HIGH   Policy Violation                      │
│        network.egress                        │
│                                              │
│ MEDIUM Undeclared Capability                 │
│        filesystem.read                       │
│                                              │
│ [ View Evidence ]                            │
└──────────────────────────────────────────────┘
```

The UI must not implement security logic.

---

# 23. Application Interface

The UI must communicate with the SkillShield application layer through a clean interface.

Conceptually:

```text
UI
 ↓
Application Interface
 ↓
SkillShield Assessment Pipeline
 ↓
Core
```

The interface should support:

```text
submit skill
start assessment
retrieve assessment status
retrieve assessment result
retrieve findings/evidence
```

The exact mechanism may be selected during implementation.

The first prototype does not require cloud infrastructure.

A local application is sufficient.

---

# 24. Source Independence

The initial system does not download skills remotely.

Future sources may include:

```text
GitHub
SkillsMP
Other marketplaces
Other repositories
```

Future source adapters should transform external sources into the same `SkillArtifact` input.

Therefore:

```text
GitHub ────────┐
SkillsMP ──────┤
Other source ──┤
               ↓
        SkillArtifact
               ↓
        Same SkillShield Core
```

No source should require changes to the security engine.

---

# 25. Application Independence

Future host integrations may include:

```text
OpenClaw
Dify
n8n
Other Agentic Platforms
```

They are outside the initial product.

If implemented later, they must use adapters around the existing core.

---

# 26. Evaluation/Testbeds

The product must be testable without any particular vulnerable application.

`vuln-agentic-skills-app` may be used later as a controlled evaluation/testbed source.

It is not a product dependency.

Other evaluation resources may include:

* Trail of Bits Overtly Malicious Skills,
* MalSkillBench,
* MaliciousSkillBench,
* SkillTrustBench.

Dataset semantics and labels must be verified before evaluation.

Real-world, benchmark, controlled, and synthetic cases must be reported separately.

---

# 27. Research Evaluation

The research evaluation should measure:

* precision,
* recall,
* F1,
* false-positive rate,
* false-negative rate,
* coverage,
* analysis failure rate,
* execution failure rate,
* runtime overhead,
* scalability.

Where labels are available, predicted-positive criteria must be defined before evaluating the test set.

Scanner configuration and policy configuration must be frozen before final evaluation.

---

# 28. Ablation Study

The following configurations should be compared:

```text
A1  Declaration only

A2  Static only

A3  Runtime only

A4  Static + Runtime

A5  Static + Runtime + Policy

Full:
    Declaration + Static + Runtime + Policy
```

This determines whether combining the four dimensions provides measurable benefit.

---

# 29. Reproducibility

Assessment runs should record:

* SkillShield version/commit,
* artifact identity,
* content digest,
* dataset identifier/version where applicable,
* policy configuration,
* scanner configuration,
* execution configuration,
* timeout,
* resource limits,
* isolation configuration,
* raw assessment output.

A locally computed digest must not be presented as a publisher-provided signature.

Cryptographic signature verification is outside the initial product scope.

---

# 30. Explicit Non-Goals

The initial product must not include:

* GitHub downloader,
* SkillsMP downloader,
* marketplace manager,
* remote source registry,
* OpenClaw integration,
* Dify integration,
* n8n integration,
* application discovery,
* database infrastructure,
* cloud infrastructure,
* LLM-based security reasoning,
* universal policy language,
* automatic dependency installation,
* automatic patch generation,
* cryptographic signature verification,
* complex frontend architecture.

These may be considered later if justified by actual requirements.

---

# 31. Design Principles

SkillShield must follow these principles:

1. Product-independent security core.
2. Downloaded skills are the primary input.
3. Local folder and ZIP are the initial supported formats.
4. D/S/R/P are separate evidence dimensions.
5. Evidence must be traceable.
6. Static possibility must not be confused with runtime observation.
7. Runtime observation must not be treated as exhaustive proof.
8. Findings must not automatically imply maliciousness.
9. UI must not contain security logic.
10. Source integrations must remain outside the core.
11. Application integrations must remain outside the core.
12. Modules should be small and understandable.
13. Avoid speculative abstractions.
14. Security claims must match actual isolation guarantees.
15. The product must be usable end-to-end before large-scale research evaluation.

---

# 32. End-to-End Prototype Definition

The initial SkillShield prototype is considered functionally complete when a user can perform the following without modifying source code:

```text
Launch SkillShield
      ↓
Open UI
      ↓
Upload downloaded skill
      ↓
Start assessment
      ↓
SkillShield ingests skill
      ↓
Extracts D
      ↓
Performs S
      ↓
Performs controlled R
      ↓
Applies P
      ↓
Correlates D/S/R/P
      ↓
Generates findings
      ↓
Generates assessment
      ↓
Displays results in UI
```

The user must be able to test this workflow using independently downloaded skills.

This is the primary acceptance criterion for the prototype.

---

# 33. Prototype Acceptance Test

At minimum, the team must demonstrate:

### Test 1 — Clean Skill

A skill with behavior matching its declaration and policy produces:

```text
NO ISSUES FOUND
```

### Test 2 — Undeclared Capability

A skill containing an undeclared capability produces a corresponding finding.

### Test 3 — Policy Violation

A skill performing a policy-prohibited capability produces:

```text
POLICY_VIOLATION
```

and an appropriate recommendation.

### Test 4 — ZIP Input

The same skill supplied as a ZIP can be assessed.

### Test 5 — Local Input

The same skill supplied as a local directory can be assessed.

### Test 6 — UI

All above assessments can be initiated and inspected through the UI.

### Test 7 — Evidence

The user can inspect why a finding was generated.

---

# 34. Final Product Vision

The final prototype should feel simple to the user:

```text
              SKILLSHIELD

     Assess an Agentic Skill
          Before You Trust It

          ┌─────────────┐
          │ Upload Skill│
          └─────────────┘

                ↓

            Assessing...

                ↓

       ┌───────────────────┐
       │ REVIEW BEFORE USE │
       └───────────────────┘

       Declared        2
       Static          5
       Runtime         4
       Policy          2

       Findings:
       • Undeclared capability
       • Policy violation
       • Evidence available

       [View Details]
```

The complexity of security analysis remains inside the product core while the user experience remains simple.

The core product is therefore:

> **Upload → Analyze → Observe → Compare → Assess → Explain**
