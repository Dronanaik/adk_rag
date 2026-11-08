# Versioning, Tagging & Release Workflow Guidelines (`VERSIONING.md`)

Whenever implementing a **new feature** or a **bug/defect fix**, every coding agent MUST follow this exact versioning, git tagging, and GitHub Release workflow.

---

## 1. Three-Digit Version Numbering Rule (`vX.Y.Z`)

Every release tag uses the format `v[MAJOR].[FEATURE].[DEFECT]`:

```text
v [MAJOR] . [FEATURE] . [DEFECT]
     │          │          └── 3rd Digit (Z): Bug / Defect Fix or UI/Extraction Polish
     │          │                             (increment Z by +1, e.g. v2.3.3 -> v2.3.4)
     │          └───────────── 2nd Digit (Y): New Feature Implementation
     │                                        (increment Y by +1 and reset Z to 0, e.g. v2.2.0 -> v2.3.0)
     └──────────────────────── 1st Digit (X): Major Application / Platform Generation (e.g. v2.0.0)
```

- **If the user specifies an explicit target version** (e.g., `2.3.3` or `2.3.4`), use that exact version.
- **If the user asks for a feature or defect fix without specifying the version**, automatically inspect the latest version in [`frontend/package.json`](../../frontend/package.json) and increment the appropriate digit (`Y` for feature, `Z` for defect fix).

---

## 2. Files That MUST Be Updated Together on Every Version Bump

Before committing on the `development` branch, update `X.Y.Z` (and `vX.Y.Z`) across **all 8 locations**:

| # | File | Exact Field / Line to Update |
| :- | :--- | :--- |
| **1** | [`frontend/package.json`](../../frontend/package.json) | `"version": "X.Y.Z"` |
| **2** | [`app/api.py`](../../app/api.py) | `version="X.Y.Z"` inside `FastAPI(...)` |
| **3** | [`docs/javascripts/repo-version-sync.js`](../../docs/javascripts/repo-version-sync.js) | `var FALLBACK_VERSION = "vX.Y.Z";` |
| **4** | [`mkdocs.yml`](../../mkdocs.yml) | `- Release Notes (vX.Y.Z): RELEASE_NOTES.md` |
| **5** | [`setup.sh`](../../setup.sh) | Banner string `(vX.Y.Z)` |
| **6** | [`setup.bat`](../../setup.bat) | Banner string `(vX.Y.Z)` |
| **7** | [`RELEASE_NOTES.md`](../../RELEASE_NOTES.md) | Prepend a new `# Release Notes — \`vX.Y.Z\`` section at the top (separated from the previous version by `---`). **Never delete or overwrite previous `# Release Notes — \`v...\`` sections below it.** |
| **8** | [`docs/RELEASE_NOTES.md`](../../docs/RELEASE_NOTES.md) | Copy the updated `RELEASE_NOTES.md` to `docs/RELEASE_NOTES.md` (`cp RELEASE_NOTES.md docs/RELEASE_NOTES.md`). |

---

## 3. Mandatory Two-Step Tagging & PR Release Flow

### Step 1: Sync `development` with `main`, Create & Push the Git Tag (`vX.Y.Z`) FIRST

Before starting or pushing any work on `development`, **always pull both `origin/development` AND `origin/main`** (because every PR merged on GitHub creates a merge commit on `origin/main`; if you only pull `origin/development`, GitHub will report `development` as behind `main` by those merge commits):

0. **Sync `development` with `origin/development` and `origin/main`**:
   ```bash
   git checkout development
   git pull origin development
   git pull origin main --no-edit
   ```

After completing the implementation and updating all 8 versioned files on the `development` branch:

1. **Commit all changes to `development`**:
   ```bash
   git checkout development
   git add -A
   git commit -m "feat/fix(vX.Y.Z): <concise summary of changes>"
   ```
2. **Create the annotated Git tag `vX.Y.Z` BEFORE creating the PR to `main`**:
   ```bash
   git tag -a vX.Y.Z -m "Release vX.Y.Z: <Release Title>"
   ```
3. **Push both the `development` branch AND the new tag `vX.Y.Z` to `origin`**:
   ```bash
   git push origin development
   git push origin vX.Y.Z
   ```

### Step 2: Open / Merge PR to `main` (Automated Tag-to-Release Linking)

When a Pull Request is opened or merged from `development` → `main`, [`.github/workflows/mkdocs-deploy.yml`](../../.github/workflows/mkdocs-deploy.yml) automatically triggers and executes the following:

1. **Verifies or Creates the Tag (`vX.Y.Z`)**:
   - Reads `"version": "X.Y.Z"` from `frontend/package.json`.
   - Fetches all remote tags (`git fetch --tags --force`). If `vX.Y.Z` was not pushed yet, it creates and pushes the annotated tag `vX.Y.Z` automatically so `LATEST_TAG` is never stale.
2. **Extracts Isolated Per-Tag Release Notes**:
   - Splits `RELEASE_NOTES.md` by `# Release Notes — \`vX.Y.Z\`` headers so each tag (`v2.0.0`, `v2.0.1`, `v2.1.0`, `v2.1.1`, `v2.2.0`, `v2.3.0`, `v2.3.3`, `v2.3.4`, etc.) receives **only its own release notes section**—never overwriting an older tag (such as `v2.2.0` or `v2.3.0`) with a newer version's release notes.
3. **Links the Tag (`vX.Y.Z`) to the GitHub Release**:
   - Runs `gh release create vX.Y.Z --verify-tag --title "ADK Agentic RAG vX.Y.Z" --notes-file /tmp/release_notes_vX.Y.Z.md` (or `gh release edit` if already created) and marks the highest semantic version tag as `--latest`.
4. **Deploys MkDocs to GitHub Pages (`gh-pages`)**:
   - When merged/pushed to `main`, builds and deploys the updated documentation portal via `mkdocs gh-deploy --force --clean`.
