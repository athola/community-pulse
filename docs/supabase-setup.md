# Supabase Setup Guide

This guide walks through the manual steps required to configure Supabase for Community Pulse deployment.

## Prerequisites

- GitHub repository admin access
- Supabase account (free tier is sufficient)

---

## Phase 1: Create Supabase Project

### Step 1.1: Create Account & Project

1. Go to [supabase.com](https://supabase.com) and sign in (or create account)
2. Click **New Project**
3. Configure:
   - **Name**: `community-pulse`
   - **Database Password**: Generate a strong password and **save it securely**
   - **Region**: Choose closest to your users
4. Click **Create new project**
5. Wait ~2 minutes for provisioning

### Step 1.2: Record Project Reference ID

1. In the Supabase dashboard, go to **Settings** → **General**
2. Find **Reference ID** (format: `abcdefghijkl`)
3. **Copy and save** this value

### Step 1.3: Generate Access Token

1. Go to [supabase.com/dashboard/account/tokens](https://supabase.com/dashboard/account/tokens)
2. Click **Generate new token**
3. Name it `community-pulse-github-actions`
4. **Copy the token immediately** (you won't see it again)

### Step 1.4: Get API URL

1. In your project dashboard: **Settings** → **API**
2. Find **Project URL** (format: `https://abcdefghijkl.supabase.co`)
3. **Copy and save** this value

---

## Phase 2: Configure GitHub Secrets

### Step 2.1: Add Repository Secrets

1. Go to GitHub → `athola/community-pulse` → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret** for each:

| Secret Name | Value | Description |
|------------|-------|-------------|
| `SUPABASE_ACCESS_TOKEN` | Token from Step 1.3 | CLI authentication |
| `SUPABASE_PROJECT_REF` | Reference ID from Step 1.2 | Project identifier |
| `SUPABASE_DB_PASSWORD` | Password from Step 1.1 | Database access |
| `SUPABASE_API_URL` | URL from Step 1.4 | Frontend API endpoint |

### Step 2.2: Verify Secrets

After adding all secrets, you should see 4 secrets listed:
- `SUPABASE_ACCESS_TOKEN`
- `SUPABASE_PROJECT_REF`
- `SUPABASE_DB_PASSWORD`
- `SUPABASE_API_URL`

---

## Phase 3: Initialize Local Supabase (Optional)

If you want to run Supabase locally for development:

### Step 3.1: Install Supabase CLI

```bash
# macOS
brew install supabase/tap/supabase

# npm
npm install -g supabase

# Or download from https://github.com/supabase/cli/releases
```

### Step 3.2: Link to Remote Project

```bash
cd /path/to/community-pulse
supabase link --project-ref <your-project-ref>
# Enter your database password when prompted
```

### Step 3.3: Start Local Development

```bash
supabase start
# This starts local Postgres, Auth, Storage, etc.
```

---

## Phase 4: Create Database Migrations

### Step 4.1: Create Initial Migration

```bash
supabase migration new init_schema
```

This creates a file like `supabase/migrations/20241217000000_init_schema.sql`

### Step 4.2: Write Your Schema

Edit the migration file with your database schema:

```sql
-- Example schema for Community Pulse
CREATE TABLE IF NOT EXISTS communities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS pulses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    community_id UUID REFERENCES communities(id),
    content TEXT NOT NULL,
    velocity FLOAT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### Step 4.3: Test Migration Locally

```bash
supabase db reset  # Resets local DB and runs all migrations
```

### Step 4.4: Push to Production

```bash
supabase db push  # Applies migrations to remote database
```

---

## Phase 5: Verify Deployment Pipeline

### Step 5.1: Check Workflow Status

After pushing to master, verify in GitHub Actions:

1. **Backend CI** - Should pass (lint, typecheck, test)
2. **Frontend CI** - Should pass (typecheck, build)
3. **Deploy to Supabase** - Should pass if secrets are configured
4. **Tag Version** - Creates tag if version changed
5. **Release** - Builds Docker + wheel + frontend on new tag

### Step 5.2: Verify Supabase Deployment

In Supabase dashboard:
- **Database** → Check tables exist
- **Edge Functions** → Check functions deployed (if any)
- **Storage** → Check website bucket has files (if frontend deployed)

---

## Troubleshooting

### "Cannot find project ref"

The `SUPABASE_PROJECT_REF` secret is missing or incorrect. Verify:
1. Secret exists in GitHub
2. Value matches the Reference ID from Supabase dashboard

### "Invalid access token"

The `SUPABASE_ACCESS_TOKEN` is expired or invalid:
1. Generate a new token at [supabase.com/dashboard/account/tokens](https://supabase.com/dashboard/account/tokens)
2. Update the GitHub secret

### Migrations Not Running

Check if migrations exist:
```bash
ls supabase/migrations/*.sql
```

The deploy workflow only runs `supabase db push` if `.sql` files exist.

### Edge Functions Not Deploying

Check if functions exist:
```bash
ls supabase/functions/
```

The deploy workflow only runs `supabase functions deploy` if function directories exist.

---

## Quick Reference

| Resource | Location |
|----------|----------|
| Supabase Dashboard | [supabase.com/dashboard](https://supabase.com/dashboard) |
| API Tokens | [supabase.com/dashboard/account/tokens](https://supabase.com/dashboard/account/tokens) |
| CLI Docs | [supabase.com/docs/guides/cli](https://supabase.com/docs/guides/cli) |
| Migration Docs | [supabase.com/docs/guides/cli/local-development](https://supabase.com/docs/guides/cli/local-development) |
