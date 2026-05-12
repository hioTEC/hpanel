---
name: plan-discussion
description: Run a multi-agent plan discussion with architect, critic, and optional domain expert. Output an accepted durable design artifact.
type: skill
parameters:
  - run_id: string
  - agenda: string
  - max_rounds: number        # default 5
  - roles: string[]          # default [architect, critic]
supported_harnesses: [kimi, claude]
---

# Plan Discussion

## Purpose
Use background sub-agents to discuss, challenge, and converge on a design before locking it.

This skill produces durable design truth in ADRs, specs, project rules, or a
roadmap section. Active-run handoffs may point to those documents, but they do
not own the design lifecycle.

## Process

1. **Agent Spawn**
   - For each role in `roles`:
     - Spawn a background sub-agent with `agent_id: {run_id}-{role}-{round}`
     - Prompt = identity + role description (e.g., architect, critic, domain expert) + agenda + relevant memory

2. **Discussion Loop**
   - Poll `TaskOutput` for each agent
   - Track turn count in conversation context (session metric, not track system)
   - Before starting a new round, call `skills/session-guardrails.md` (turn threshold check)
   - When all agents have returned:
     - Summarize points of agreement and disagreement
     - If unanimous consensus → proceed to Convergence
     - If disagreement:
       - Increment `round`
       - If any agent has been resumed `>= 3` times → **Yellow checkpoint**: warn about agent fatigue
       - If any agent has been resumed `>= 5` times → **Red checkpoint**: recommend killing and respawning the agent
       - Resume each agent with the summary + new focused question
      - If `round >= max_rounds` → pause, mark `blocked_human` in the active run `handoff.md` and record the split decision

3. **Convergence**
   - Resume the `architect` agent: "Write the final design as a structured markdown doc"
   - Resume the `critic` agent: "Review the final design for missed edge cases"
   - Integrate feedback into the chosen durable design artifact declared by
     project `AGENTS.md`: ADR/spec/rule/roadmap, or `src/lib/{domain}/spec.md`
     / `src/components/{domain}/spec.md` when the design is a module contract.
   - Set the design artifact status to `proposed`

4. **Stealth Challenge**

   Before presenting the design to the human or locking it, it must pass a **cross-harness dual review**: one sub-agent on the same harness + one external reviewer on a different harness. The goal is to verify design completeness while using an independent perspective from a different model family to uncover blind spots of the orchestrator and any single model.

   Review rules are defined in `skills/code-review.md` "Cross-Harness Review Rule": the external reviewer's harness family must differ from the primary agent's.

   **5.1 Orchestrator Self-Check (Hidden Scenarios)**
   - Before summoning any reviewer, the orchestrator must first independently refine the design artifact, ensuring it is a "complete, serious version" (field definitions, state machines, API contracts, and error paths are all clearly specified).
   - The orchestrator independently devises at least 3-5 extreme scenarios (boundary conditions, error paths, high concurrency, abnormal input, permission bypass, partial failure, timing inversion, etc.), but **must not write these scenarios to any file or reveal them to any reviewer in subsequent prompts**.
   - These hidden scenarios serve as an "answer key," used only for later cross-referencing. If the design artifact already covers these scenarios, verify whether the reasoning is sufficiently thorough.

   **5.2 Internal Critic (Sub-agent, same harness)**

   Launch the in-harness critic per `{{DOTPANEL_ROOT}}/protocol/skills/code-review.md` section "Resolver" (context = design artifact only; do not pass workspace/memory/history). The critic and the external reviewer in 5.3 must be launched in parallel.

   **5.3 External Reviewer (different harness, either codex or kimi-cli)**

   Select the reviewer per `{{DOTPANEL_ROOT}}/protocol/skills/code-review.md` section 2 "Select External Reviewer"; compose the review brief and launch per sections 3-4, scope = "design". For design reviews, prefer kimi-cli (prompt-native). The reviewer must not receive the orchestrator's hidden scenarios.

   **5.4 Cross-Reference and Adjudication**
   - Once both reviewers return, the orchestrator performs a four-way comparison:
     a) **Issues found by the internal critic** -- scenarios and gaps independently identified by the same-harness sub-agent
     b) **Issues found by the external reviewer** -- scenarios and gaps independently identified by the cross-harness reviewer
     c) **Orchestrator's hidden scenarios** -- extreme scenarios devised during the self-check
     d) **Current design artifact coverage** -- are all of the above three adequately covered by the existing design?
   - Synthesis rules follow `{{DOTPANEL_ROOT}}/protocol/skills/code-review.md` section 5 "Synthesize". Specific to this step:
     - If either the internal or external reviewer found a blind spot the orchestrator did not anticipate (compared against hidden scenarios) -> **must roll back**: record the new issue in the active run `handoff.md`, return to Step 3 (Discussion Loop) or Step 4 (Convergence) to revise the design artifact, then re-enter Stealth Challenge.
     - If the reviewers' findings are already covered by the design artifact but the explanation is insufficiently clear or explicit -> update the relevant sections of the design artifact to strengthen the reasoning, then re-enter Stealth Challenge.
     - If all scenarios (hidden + internal + external) are adequately covered by the design artifact with sufficient reasoning -> proceed to Step 5 (Decision Registry).
   - **Loop limit:** Maximum 3 rounds of Stealth Challenge. If convergence is not reached after 3 rounds -> pause, record the unresolved points of disagreement in the active run `handoff.md`, mark `blocked_human`, and wait for human intervention.

5. **Decision Registry**

   Generate a decision registry table at the end of the design artifact. Classify each decision produced during discussion:

   ```markdown
   ## Decision Registry

   | ID | Decision | Level | Rationale |
   |----|----------|-------|-----------|
   | D-01 | Use NextAuth v5 Credentials + Google OAuth | locked | Verified, immutable |
   | D-02 | Use data-testid for semantic button targeting on Review page | locked | Test infrastructure dependency |
   | D-03 | Store images locally in public/ for now, migrate to R2 later | deferred | Not implemented in current phase |
   | D-04 | Pagination strategy (cursor vs offset) | discretion | Agent decides based on data volume |
   ```

   **Three levels:**

   | Level | Meaning | Implementation-phase constraint |
   |-------|---------|-------------------------------|
   | `locked` | Explicitly decided by the user, or consensus reached during discussion | Must be implemented item by item. Verifier checks each one during verification. |
   | `deferred` | Explicitly excluded from the current round | Must not appear in the plan. If an agent discovers it must be done earlier, return to the plan phase to discuss. |
   | `discretion` | Delegated to the agent's judgment | Agent decides independently and records the choice and rationale in run verification/evidence. |

   **Source rules:**
   - User explicitly says "use X" during discussion → `locked`
   - User says "deal with this later" / "not urgent" → `deferred`
   - No clear conclusion reached during discussion, but a decision is needed at implementation time → `discretion`
   - Purely technical decision with no user involvement, consensus reached by architect/critic → `discretion`

6. **Human Gate / Auto-Confirmation Manifest**

   This step distinguishes between interactive mode and non-interactive mode (e.g., Kimi `-y`).

   **Interactive mode:**
   - Present the design to the user with options:
     - A) Lock and proceed to implement
     - B) Modify something first
     - C) Pause, review later
   - User reviews Decision Registry — can upgrade/downgrade any decision level
   - On A → design artifact status = `accepted`, active run `handoff.md` updated with implementation scope and Resume here; run manifest remains `active`. Use the stale-write guard: manifest `revision` must match handoff `manifest_revision`, then both increment together.
   - On B/C → keep `proposed`, update handoff with requested changes

   **Non-interactive mode (-y / auto-approved):**
   > Key principle: Auto-approval of `ExitPlanMode` **does not mean** a human has reviewed the plan. The following internal confirmation ritual must be performed before the plan can be considered "agreed upon."

   - Orchestrator must append a `## Auto-Confirmation Manifest` section at the end of the design artifact (update it if it already exists). The content must include:
     1. **Core Decisions Reviewed** -- Summarize each `locked` level decision in one sentence
     2. **Risk Acknowledgment** -- List the highest-risk points identified in the design and their mitigations
     3. **Boundary Assumptions** -- State the external assumptions the design depends on (e.g., "user is logged in", "database transaction isolation level is READ COMMITTED")
     4. **Stealth Challenge Result** -- State: "This plan has completed {N} rounds of Stealth Challenge review; all discovered scenarios conform to normal usage logic"
     5. **Self-Attestation** -- Full sentence: "As the orchestrator, I have reviewed the final design, the decision registry, and the stealth challenge output. I attest that this plan is complete, internally consistent, and ready for implementation."
   - Only after writing the above manifest may the design artifact status be updated to `accepted`, using the stale-write guard to update the active run handoff's implementation scope.
   - If the orchestrator has genuine low confidence about any part → **must not** auto-accept; write the uncertainty to the active run `handoff.md`, mark `blocked_human`, and report to the user.
