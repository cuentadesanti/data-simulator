# GitHub Actions Setup for Database Migrations

## Quick Start

### 1. Add GitHub Secrets

Go to your repository on GitHub:

1. Navigate to `Settings` → `Secrets and variables` → `Actions`
2. Click `New repository secret`
3. Add the following secrets:

**Secret 1: Database URL**

**Name:** `DS_DATABASE_URL`

**Value:** Your Supabase pooled PostgreSQL connection string:
```
postgresql+psycopg://[user]:[password]@aws-1-eu-west-1.pooler.supabase.com:5432/postgres
```

**Secret 2: Render Deploy Hook**

**Name:** `RENDER_DEPLOY_HOOK_URL`

**Value:** Your Render deploy hook URL (from Render dashboard → Settings → Deploy Hook)
```
https://api.render.com/deploy/srv-xxxxxxxxxxxxx?key=xxxxxxxxxxxxxx
```

### 2. Verify Workflow

The workflow file is located at `.github/workflows/backend-ci.yml`.

It will automatically:
- ✅ Run on every push to `main` that touches `backend/`
- ✅ Run tests with SQLite
- ✅ Apply migrations to your Supabase database
- ✅ Trigger Render deployment via deploy hook
- ✅ Render deploys only after migrations succeed

### 3. Test the Setup

Create a test migration to verify everything works:

```bash
cd backend
alembic revision -m "test migration setup"
git add alembic/versions/
git commit -m "test: verify GitHub Actions migration workflow"
git push origin main
```

Then check:
1. GitHub Actions tab - should show green checkmark
2. Render - should auto-deploy after Actions complete

### 4. Render Configuration

Ensure your Render service has:

**Environment Variable:**
- `DS_DATABASE_URL` = Same Supabase URL as GitHub secret

**Auto-Deploy:**
- ❌ **Disabled** (deployments are triggered by GitHub Actions)

**Deploy Hook:**
- ✅ Created and added to GitHub secrets as `RENDER_DEPLOY_HOOK_URL`

## Workflow Diagram

```
Developer pushes to main
         ↓
GitHub Actions triggered
         ↓
    Run pytest
         ↓
  Apply migrations
         ↓
 Trigger Render deploy
         ↓
    Render deploys
         ↓
  Production ready
```

## Important Notes

- Migrations run **before** Render deployment
- If migrations fail, Render won't deploy (safe!)
- Always test migrations locally first
- See `MIGRATIONS.md` for detailed workflow

## Troubleshooting

**Actions fail with "No module named 'pydantic_settings'"**
- Ensure `requirements.txt` includes `pydantic-settings>=2.1.0`

**Migrations fail with connection error**
- Verify `DS_DATABASE_URL` secret is set correctly
- Check Supabase connection string format

**Render deploys before migrations**
- This shouldn't happen - GitHub Actions must complete first
- Check that workflow is triggered on `push` to `main`
