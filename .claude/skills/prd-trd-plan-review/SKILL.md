---
name: prd-trd-plan-review
description: Draft or review PRD/TRD and implementation plans, and use the user's Claude Code subscription for an independent review when requested.
---

# PRD/TRD plan review

Use this workflow when the user asks to create a project plan and have Claude review it, or asks for a separate Claude review of an existing PRD/TRD or implementation plan.

## Workflow

1. For a new project, clarify the user's goal and key scope choices before drafting. Keep confirmed facts, assumptions, and open decisions distinct. For this stock-data project, follow the existing `CLAUDE.md` planning guidance and use `docs/planning.md` for a small combined PRD/TRD.
2. Finish a reviewable Markdown plan before requesting the review. Do not invent missing requirements to make it appear complete.
3. When the user requested Claude review, explain that it runs through their logged-in Claude Code account and uses that account's usage allowance. The plan text is passed to Claude Code locally.
4. Run the helper from the project root:

   ```powershell
   powershell -NoProfile -File tools/claude_plan_review.ps1 docs/planning.md -Kind prd-trd
   ```

   For an implementation plan, pass its Markdown path and `-Kind code-plan`.
5. If the helper reports an API key, stop and explain that `ANTHROPIC_API_KEY` overrides the subscription in `claude -p`. Do not unset it silently; ask the user to remove it from the environment and restart VS Code if they want to use their Pro allowance.
6. Summarize Claude's verdict, blocking issues, and important questions. Keep the original plan unchanged unless the user asks to revise it. The helper stores each review under `docs/reviews/`.

## Required PRD/TRD review criteria

Treat the PRD/TRD as a decision plan for work that has not started. Review these four areas:

1. **Goal and scope:** Is the problem, target user, intended outcome, first-version scope, and out-of-scope work clear?
2. **Requirements and acceptance:** Are requirements unambiguous and are completion criteria observable or measurable?
3. **Technical feasibility:** Are data sources and their terms, API access/limits/costs, architecture, data flow, runtime environment, and dependencies understood well enough?
4. **Risks and open decisions:** Are security/privacy/secrets, failure and missing-data handling, operational risks, assumptions, and decisions that block a start identified?

For each area, distinguish what is covered from gaps and open decisions. Do not invent requirements or mark every gap as a blocker; explain which decisions prevent a responsible start.

## Review boundaries

- Claude is a second reviewer, not the source of truth. Check factual claims, especially data source terms, API access, and financial definitions, against primary sources before treating them as confirmed.
- Do not turn review suggestions into requirements without the user's decision.
- The helper sends the plan text to the logged-in Claude Code CLI and does not use an API key. It stops if `ANTHROPIC_API_KEY` is found in process, user, or machine environment variables.
