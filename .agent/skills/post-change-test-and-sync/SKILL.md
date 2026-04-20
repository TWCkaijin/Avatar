---
name: post-change-test-and-sync
description: "After every code change or addition by the agent, establish full tests, execute tests, and fix until all pass. Finally, synchronize the change summary to .claude/skills/gdg-course-design-pattern/references. Use when: add feature, bugfix, refactor, update tests, verify code change."
argument-hint: "The scope of this change (features, files, modules)"
---

# Post Change Test And Sync

## Purpose

To integrate the "verify after change" mindset into a standard workflow, preventing situations where code is modified without verification, or where specifications are not synced after verification.

## When to Use

- After adding a new feature
- After fixing a bug
- After refactoring
- After adjusting API contracts, data structures, error handling, or boundary conditions

## Inputs

- The functional scope of the current change
- Affected files and modules
- Expected behavior and failure cases

## Standard Workflow

1. Inventory the changes and test scope.
2. Complete full tests first (positive, negative, boundary, regression).
3. Execute tests targeted at the change.
4. If failures occur, determine whether it's a product code issue or test issue, then fix and rerun.
5. Repeat until tests pass.
6. Synchronize the details of the modifications to .claude/skills/gdg-course-design-pattern/references.

## Detailed Steps

### Step 1: Inventory Changes

- Read the change diffs and list:
  - Which files were modified
  - Affected functional points
  - Existing paths that might be affected
- Create a list of test cases for each functional point.

### Step 2: Establish Full Tests

- Prioritize creating tests that "precisely target the change"; do not run full suite tests yet.
- Each functional point must include at least:
  - Positive cases (expected success)
  - Negative cases (invalid input or error paths)
  - Boundary cases (null values, extreme values, missing fields, length limits)
  - Regression cases (to prevent old issues from recurring)

### Step 3: Execute Tests

- Run the minimum necessary test set first.
- For Python projects, use the appropriate command based on the environment:
  - uv run pytest <target>
  - conda run -n <env> pytest <target>
  - python3 -m pytest <target>
- Expand to the test set of affected modules if necessary.

### Step 4: Failure Triage and Fix

- If it's a product code logic error: fix the product code.
- If it's a false premise in the test: fix the test.
- If it's a lack of test infrastructure (fixture/mock/setup): complete the test environment.
- Rerun the exact same batch of target tests after every fix.

### Step 5: Iterate to Pass

- Continue the "fix -> rerun" cycle until all targeted tests show green.
- After targeted tests pass, run necessary adjacent regression tests to ensure no spillover breakage.

### Step 6: Sync to GDG references

- Add or update a change log document in .claude/skills/gdg-course-design-pattern/references.
- Suggested filename: change-log.md (create if it does not exist).
- Record at least the following each time:
  - Date
  - Summary of changes
  - Affected files
  - New or updated tests
  - Test execution results

Suggested format for the record:

```markdown
## YYYY-MM-DD

- Summary: <Key points of this change>
- Files: <Comma-separated files>
- Tests Added/Updated: <Test files and cases>
- Test Result: <All passed / Still have failures (with reasons)>
```

## Quality Gates

- Complete tests that correspond to the changes already exist.
- All target tests have passed.
- Necessary regression tests have passed.
- .claude/skills/gdg-course-design-pattern/references has been synced with the current changes.
- Explicitly list in the response: what was changed, what was tested, and what the results are.

## Handling Failures

- Must not skip failing tests to declare completion directly.
- Deleting tests is not allowed as a replacement for fixing them (unless there is an explicit requirement change and traceability).
- If still failing after the third fix attempt, output the blocking reason and actionable next steps.

## Direct Trigger Phrases

- "Please apply post-change-test-and-sync to this change"
- "Execute the post-change testing workflow until passing and sync references"
- "After changing this feature, follow the standard workflow to add tests, run tests, and update specification records"
