## Completion Claim Discipline (HARD BLOCK)

Before posting ANY message containing completion language ("shipped", "merged", "landed", "deployed", "PR #N merged", commit hashes), you MUST:

1. Run the actual verification command and capture its output:
   - PR claims: `bash scripts/verify_pr.sh <N>` — check state=MERGED
   - Commit claims: `git cat-file -t <hash>` — must return "commit"
   - Deploy claims: `systemctl --user status <service>` — must show active
2. Paste VERBATIM terminal output in your message. Never paraphrase.
3. If verification fails or command errors: do NOT post the claim. Fix first.

Context compaction can cause you to conflate "will do" with "did" and generate plausible-but-fake PR numbers, commit hashes, and verify_pr.sh output. This rule exists because 5 fabricated completion claims were caught by peer git verification on 2026-05-11. You cannot trust your own memory of what shipped — only trust shell output.
