# Git and sync

Run commands from the actual vault root. Remote operations are optional. A remote's existence does not grant permission to fetch, pull, push, or upload; honor local-only/read-only scope even when the usual workflow syncs.

## Routine edits

1. Inspect `git status --short --branch`, `git diff`, and `git diff --cached`. Check `git config --get core.hooksPath` and the existing hook setup. Identify unrelated work before changing files.
2. If sync is authorized and the checkout/index are clean, update from the configured upstream with `git pull --ff-only`. If no upstream exists, don't guess a remote or branch. If the checkout is dirty or diverged, use the recovery procedure below.
3. Make the bounded edit and verify the actual saved content. Stage exact paths, including intended deletions: `git add -- path/to/note.md path/to/log.csv`. Avoid `git add .` and broad staging of another person's work.
4. Review `git diff --cached --stat` and `git diff --cached`. If unrelated files were already staged, do not include them in your commit or silently unstage them. Coordinate a clean index or use an isolated worktree for the task.
5. Commit with a descriptive message. The installed hook is the normal gate; without it, run `python3 scripts/pkb-validate.py` **after staging**. A routine CSV edit does not need a duplicate full graph scan. After bulk moves or structural work, run `--full` explicitly. The validator may regenerate and stage `.agent/index/canonical.json`. After a successful commit, inspect the resulting commit (including generated changes) before reporting success or pushing. Do not bypass a failed hook to declare success.
6. If remote sync is authorized, push to the intended configured upstream and check the exit result. A rejected push does not erase the local commit; reconcile the remote safely instead of force-pushing or repeating the log entry. Otherwise report the local commit as unpushed. If committing was outside scope, report the saved changes without making a commit.

## Dirty or independently synchronized checkouts

File-sync tools and Git clients can deliver changes in different orders. A working tree that appears to match a remote is not proof that its index, branch history, or untracked files are safe to replace.

- Inspect staged, unstaged, and untracked paths separately. Preserve an appropriate local backup of valuable uncommitted work outside Git before a nontrivial reconciliation; don't accidentally include credentials in a checkpoint commit.
- Fetch only when authorized. Compare the branch and configured upstream, and inspect differences for the specific paths involved. Include staged changes in that analysis.
- If the branch is behind but another file-sync tool already delivered similar content, **do not automatically reset the branch or stash everything**. An isolated clean worktree based on the intended upstream is often the simplest place to apply the task, leaving the original checkout intact. Reconcile the original separately once its work is accounted for.
- For real divergence, merge or rebase under the repository's policy after preserving work; resolve conflicts explicitly. Never use `reset --hard`, forced checkout, `clean`, or automatic stash/pop as a generic recovery recipe.
- Re-run the relevant staged checks after reconciliation. Use the authority CLI audit only after reviewing its working-tree input; stage its generated output alongside the intended authority changes. Keep unresolved conflicts and remaining sync steps visible in the handoff.

These are procedures, not a bundled automatic sync or recovery command. No remote access is necessary for local capture, validation, or commits.
