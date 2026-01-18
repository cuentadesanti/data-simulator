# Release + Rollback Runbook

This document outlines the operational procedures for deploying, monitoring, and recovering the Data Simulator application.

## 🚀 CI/CD Pipeline

The project uses GitHub Actions for CI/CD, targeting **Render** for production hosting.

### Pipeline Stages
1. **Pull Request (Backend/Frontend)**:
   - Runs `pytest` (Backend) or `npm run build` (Frontend).
   - Backend PRs perform an **Alembic Drift Check** to ensure ORM models and migrations are in sync.
2. **Push to `main`**:
   - Executes full test suite.
   - Runs database migrations on production (Supabase).
   - Triggers deployment via Render Deploy Hook.
   - Executes a **Post-Deploy Smoke Test** against the production URL.

## 📦 Deployment

### Automated Deployment
Deploys are triggered automatically upon a successful merge to `main`. You can monitor progress in the [GitHub Actions tab](https://github.com/cuentadesanti/data-simulator/actions).

### Manual Deployment
If you need to trigger a deploy manually:
```bash
curl -X POST https://api.render.com/deploy/srv-YOUR_SERVICE_ID?key=YOUR_DEPLOY_TOKEN
```

## 🔄 Rollback Procedures

### 1. Revert Code (GitHub)
- Find the last stable merge commit in `main`.
- Use `git revert` or manually reset `main` and force push (caution!).
- This will trigger the automated pipeline and re-deploy the old code.

### 2. Database Rollback (Alembic)
If a release included a breaking migration that needs to be reverted:
```bash
cd backend
# Downgrade by 1 revision
uv run alembic downgrade -1
```
> [!CAUTION]
> **Data Loss Risk**: Downgrading migrations may drop columns or tables. Always verify the migration script before running `downgrade`.

### 3. Immediate Render Rollback
Using the Render Dashboard:
1. Navigate to the **Events** tab.
2. Find the previous successful deployment.
3. Select **Rollback to this revision**.

## 🛠️ Required Secrets

The following secrets must be configured in GitHub Repo Settings:

| Secret | Description |
|--------|-------------|
| `DS_DATABASE_URL` | Production PostgreSQL connection string (Supabase). |
| `RENDER_DEPLOY_HOOK_URL` | The private hook URL from Render Dashboard. |
| `BACKEND_URL` | The public URL of the deployed API (for smoke tests). |

---
> [!NOTE]
> For more details on the initial Actions setup, see [GITHUB_ACTIONS_SETUP.md](file:///Users/cuentadesanti/code/data-simulator/GITHUB_ACTIONS_SETUP.md).
