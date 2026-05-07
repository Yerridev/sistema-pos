# Skill Registry

**Delegator use only.** Any agent that launches sub-agents reads this registry to resolve compact rules, then injects them directly into sub-agent prompts. Sub-agents do NOT read this registry or individual SKILL.md files.

See `_shared/skill-resolver.md` for the full resolution protocol.

## User Skills

| Trigger | Skill | Path |
|---------|-------|------|
| when drafting or posting feedback, review comments, maintainer replies, Slack messages, or GitHub comments | comment-writer | C:\Users\yerri\.config\opencode\skills\comment-writer\SKILL.md |
| when writing guides, READMEs, RFCs, onboarding docs, architecture docs, or review-facing documentation | cognitive-doc-design | C:\Users\yerri\.config\opencode\skills\cognitive-doc-design\SKILL.md |
| when a PR would exceed 400 changed lines, when planning chained PRs, stacked PRs, or reviewable slices | chained-pr | C:\Users\yerri\.config\opencode\skills\chained-pr\SKILL.md |
| When creating a GitHub issue, reporting a bug, or requesting a feature | issue-creation | C:\Users\yerri\.config\opencode\skills\issue-creation\SKILL.md |
| When creating a pull request, opening a PR, or preparing changes for review | branch-pr | C:\Users\yerri\.config\opencode\skills\branch-pr\SKILL.md |
| When user asks to create a new skill, add agent instructions, or document patterns for AI | skill-creator | C:\Users\yerri\.config\opencode\skills\skill-creator\SKILL.md |
| When writing Go tests, using teatest, or adding test coverage | go-testing | C:\Users\yerri\.config\opencode\skills\go-testing\SKILL.md |
| When user says "judgment day", "judgment-day", "review adversarial", "dual review", "doble review", "juzgar", "que lo juzguen" | judgment-day | C:\Users\yerri\.config\opencode\skills\judgment-day\SKILL.md |
| when implementing a change, preparing commits, splitting PRs, or planning chained or stacked PRs | work-unit-commits | C:\Users\yerri\.config\opencode\skills\work-unit-commits\SKILL.md |

## Compact Rules

Pre-digested rules per skill. Delegators copy matching blocks into sub-agent prompts as `## Project Standards (auto-resolved)`.

### comment-writer
- Start with the actionable point, skip long recaps
- Warm and direct tone, 1 to 3 short paragraphs or tight bullets
- Explain why when requesting a change
- Avoid pile-ons, comment on the highest-value issue
- Match the thread language (Spanish uses voseo)
- No em dashes, use commas or periods

### cognitive-doc-design
- Lead with the decision or outcome first
- Use progressive disclosure: happy path then details
- Chunk content into small sections and short lists
- Add signposting with headings and labels
- Prefer recognition over recall: tables, checklists, templates
- Make review paths explicit and scoped

### chained-pr
- MUST split when additions + deletions exceed 400 unless `size:exception`
- Ask the user to choose chain strategy before splitting
- Each PR must be autonomous, reviewable, and rollback-safe
- Document chain boundaries: start, end, before, after, out of scope
- Use a tracker PR when chain has more than 2 PRs
- Include a chain diagram marking the current PR
- Ensure child PRs target the immediate parent branch

### issue-creation
- Blank issues are disabled, always use a template
- New issues get `status:needs-review` automatically
- PRs require `status:approved` on the linked issue
- Questions go to Discussions, not issues
- Search for duplicates before creating

### branch-pr
- Every PR must link an approved issue and have exactly one `type:*` label
- Branch names must match the required regex (type/description)
- Use the PR template, include linked issue and test plan
- Commit messages must follow Conventional Commits regex
- Run shellcheck on modified scripts before PR
- No `Co-Authored-By` trailers

### skill-creator
- Create skills only for reusable patterns, not one-offs
- Follow skills/{skill-name}/SKILL.md structure
- Frontmatter must include name, description+Trigger, license, metadata
- references/ must point to local files, not web URLs
- Add new skills to AGENTS.md
- Keep rules and examples minimal and actionable

### go-testing
- Prefer table-driven tests for multiple cases
- Test Bubbletea models by calling Update directly
- Use teatest for interactive TUI flows
- Use golden files for view output when appropriate
- Use t.TempDir for filesystem tests

### judgment-day
- Resolve compact rules from the skill registry before launching judges
- Launch two judges via delegate in parallel, never sequential
- Classify warnings as real vs theoretical
- Do not fix until the user confirms confirmed issues
- After fixes, immediately re-judge in parallel
- After 2 iterations, ask user before continuing

### work-unit-commits
- Commit by deliverable work unit, not by file type
- Keep tests and docs with the behavior they verify
- Each commit should stand alone with reasonable rollback
- Use SDD workload forecast to decide on chained PRs
- Keep review size under 400 changed lines when possible

## Project Conventions

| File | Path | Notes |
|------|------|-------|
| AGENTS.md | Y:\proyects26\sistema-pos\AGENTS.md | Index — references files below |
| copilot-instructions.md | Y:\proyects26\sistema-pos\.github\copilot-instructions.md | |

Read the convention files listed above for project-specific patterns and rules. All referenced paths have been extracted — no need to read index files to discover more.
