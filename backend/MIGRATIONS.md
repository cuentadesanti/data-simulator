# Database Migrations Guide

## Overview

This project uses **Alembic** for database schema migrations. Migrations are automatically applied via **GitHub Actions** when code is merged to `main`.

## Architecture

- **Development**: SQLite (`data_simulator.db`)
- **Production**: PostgreSQL (Supabase)
- **Migration Trigger**: GitHub Actions on push to `main`
- **Deployment**: Render auto-deploys after migrations complete

## Workflow

### 1. Making Schema Changes

When you modify SQLAlchemy models in `backend/app/db/models.py`:

```bash
# From backend/ directory
cd backend

# Create a new migration
alembic revision --autogenerate -m "describe your change"

# Review the generated migration in alembic/versions/
# Edit if needed to ensure it's correct

# Test locally
alembic upgrade head

# Commit the migration
git add alembic/versions/
git commit -m "feat: add migration for [your change]"
```

### 2. Deployment Process

```mermaid
graph LR
    A[Push to main] --> B[GitHub Actions]
    B --> C[Run Tests]
    C --> D[Run Migrations]
    D --> E[Render Auto-Deploy]
    E --> F[Production Ready]
```

**Steps:**
1. Push/merge to `main` branch
2. GitHub Actions runs:
   - Install dependencies
   - Run `pytest` (with SQLite)
   - Run `alembic upgrade head` (against Supabase PostgreSQL)
3. Render detects the push and auto-deploys
4. By the time Render starts, schema is already up-to-date

### 3. GitHub Secrets Required

Set this in your repository settings (`Settings` → `Secrets and variables` → `Actions`):

| Secret Name | Value |
|-------------|-------|
| `DS_DATABASE_URL` | `postgresql+psycopg://[user]:[password]@aws-1-eu-west-1.pooler.supabase.com:5432/postgres` |

> **Important**: Use the **pooled connection string** from Supabase for GitHub Actions.

### 4. Environment Variables

The system reads the database URL from the `DS_DATABASE_URL` environment variable:

- **Local Development**: Set in `backend/.env`
- **GitHub Actions**: Set as repository secret
- **Render**: Set in service environment variables

## Commands Reference

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations locally
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history

# View current version
alembic current
```

## Rules

1. ✅ **Always create migrations for schema changes**
2. ✅ **Commit migrations to git before merging**
3. ✅ **Test migrations locally first**
4. ❌ **Never modify the database schema manually in Supabase**
5. ❌ **Never run migrations manually on Render**
6. ❌ **Never hardcode database URLs in code**

## Troubleshooting

### Migration fails in GitHub Actions

1. Check the Actions log for the specific error
2. Verify `DS_DATABASE_URL` secret is set correctly
3. Test the migration locally with a PostgreSQL database
4. Ensure the migration file is committed to git

### Schema out of sync

```bash
# Check current database version
alembic current

# Check pending migrations
alembic history

# If needed, manually run migrations (emergency only)
DS_DATABASE_URL="your-db-url" alembic upgrade head
```

### Render deployment fails

1. Check that GitHub Actions completed successfully
2. Verify Render's `DS_DATABASE_URL` matches your Supabase connection
3. Check Render logs for specific errors

## Best Practices

- **Small migrations**: Keep each migration focused on one change
- **Descriptive names**: Use clear, descriptive migration messages
- **Review generated code**: Always review auto-generated migrations
- **Test rollbacks**: Ensure your migrations can be rolled back
- **Data migrations**: For data changes, create separate migrations

## Example Migration

```python
"""add user preferences table

Revision ID: abc123
Revises: xyz789
Create Date: 2026-01-18 05:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

def upgrade() -> None:
    op.create_table(
        'user_preferences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('theme', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    op.drop_table('user_preferences')
```
