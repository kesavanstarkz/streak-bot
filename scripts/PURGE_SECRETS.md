# Purge Secrets (Windows / PowerShell)

This file contains recommended commands to remove secrets from git history on Windows using BFG or git filter-branch.

## Using BFG (recommended)

1. Download BFG (https://rtyley.github.io/bfg-repo-cleaner/)
2. Create a file `secrets.txt` listing each secret string (one per line)
3. Mirror your repo to a bare repository:

```powershell
git clone --mirror https://github.com/youruser/yourrepo.git
cd yourrepo.git
```

4. Run BFG to replace secrets (this replaces them with **_REMOVED_**):

```powershell
java -jar path\to\bfg.jar --replace-text ../secrets.txt
```

5. Cleanup and force-push:

```powershell
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push --force
```

## Using git filter-branch (slower, built-in)

```powershell
# Example: remove a file from all history (dangerous - creates rewritten history)
git filter-branch --force --index-filter "git rm --cached --ignore-unmatch usingAzure.py .env" --prune-empty --tag-name-filter cat -- --all

# Cleanup and force-push
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push --force
```

Make backups of your repo before running any of these operations. Coordinate with teammates because a force-push rewrites public history.
