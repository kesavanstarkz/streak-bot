# Security actions

This repository previously contained sensitive keys in commits. Follow these steps to fully remediate:

1. Revoke the leaked keys immediately (Azure OpenAI key, Telegram bot token, Google service-account key, OCR.Space key).
2. Generate new keys and rotate any credentials that may have been exposed.
3. Add secrets to environment variables or a secrets manager (Render, GitHub Actions secrets, etc.).
4. Purge secrets from git history (examples below).

Purge historical secrets (BFG recommended):

# Using the BFG Repo-Cleaner (recommended)

# Requires Java and that you have a bare repo clone

# Replace 'secrets.txt' with a file that lists the raw secret strings

# 1. Create 'secrets.txt' with literals to remove

# 2. Run:

# java -jar bfg.jar --replace-text secrets.txt repo.git

# 3. Cleanup and force-push:

# cd repo.git

# git reflog expire --expire=now --all && git gc --prune=now --aggressive

# git push --force

# Alternatively use git filter-repo (if installed):

# git filter-repo --replace-refs delete-no-force --replace-text secrets.txt

Note: Rewriting history requires a force-push and will disrupt collaborators. Coordinate with your team before proceeding.
