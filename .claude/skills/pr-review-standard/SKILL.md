---
name: pr-review-standard
description: "Compare this repository's PR review setup (guidelines, reviewer agent, posting of the review) with the standard and bring it up to date; run when the standard changes. Reports first, changes nothing until OK."
disable-model-invocation: true
argument-hint: "[check]"
---

Compare this repository's PR review setup with the standard below, and bring it up to date.

**The standard**

- `docs/review-guidelines.md` has a *Procedure* section with the six points below, plus the repository's own checks (conventions, decision records, tests, changelog, confidentiality, writing).
- `.claude/agents/pr-reviewer.md`: read-only (read tools only; Bash only for commands that read), `model: fable`. It is given the branch, the PR's description (the draft if not opened) and its number; it runs `git fetch origin` and compares with `origin/develop`, never a local `develop`; it reads a branch's files with `git show <branch>:<path>`; it names binary files that changed; it reports as *Must fix*, *Should fix*, *Questions*, *Checked*, titled `Review of #<number> (<title>)` or `Review of <branch>`; where a finding is about personal data, internal material or a secret it describes it and never quotes it.
- `CONTRIBUTING.md` (*Review*) and `CLAUDE.md` (and `AGENTS.md` if present) say the same in one or two lines each and point to the guidelines.

Procedure (the same text in every repository; only the platform's commands differ):

1. The author's Claude Code session runs the reviewer agent on every branch before opening the PR. If the author used the same model, the PR says so.
2. The author fixes what holds up before opening the PR, and answers the rest.
3. The review is posted as the first comment on the PR, once it is opened. It starts with a status line: either all findings were handled before opening, or which are still open. Then the reviewer's report unchanged, except that anything it quotes that may not be in the repository is replaced by a description. Under each finding, a line says how it was handled: fixed in which commit, answered, or left and why. A review without findings is posted too. The description gets one line: who reviewed, on which model, and that the report is in the comments. A later review, after larger changes, is a new comment.
4. Posting is part of opening the PR: on GitHub `gh pr comment <number> --body-file <file>`, on GitLab through the API. Without access, the session gives the author the text to paste.
5. Without Claude Code, the author checks the PR against the guidelines and asks the maintainer to run the agent and post its report before approving.
6. Advisory: CI is the required check, and the maintainer approves or merges.

**Steps**

1. **Compare, change nothing.** Read the files above, if they exist. Show a short table: file, what it says now, what the standard says. A missing agent or guidelines file counts. Keep the repository's own checks; only the procedure, the agent's instructions and the pointers change. If the argument is `check`, stop here.
2. **Wait for my OK.**
3. **Apply it** on a new branch `docs/pr-review-procedure` from `origin/develop` (never on a feature branch, `develop` or `main`), one commit. Don't push and don't open the PR.
4. **Report:** the files changed, anything left alone and why.

Never mention a vault in the repository's files.
