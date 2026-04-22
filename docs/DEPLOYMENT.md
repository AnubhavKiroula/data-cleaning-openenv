# Production Deployment Guide

## Deploying data-cleaning-openenv to Render.com

---

## Prerequisites

Before deploying, you will need:

1. **Render.com account** (free tier available)
2. **GitHub account** (already have this)
3. **HuggingFace account** (for API token) - OR use OpenAI API key
4. Repository connected to Render

---

## Step 1: Create External Accounts

### 1.1 Render Account

1. Go to https://render.com
2. Click **Sign Up** (free)
3. Sign up with your GitHub account (recommended)
4. Verify your email

### 1.2 HuggingFace Account (if using HF API)

1. Go to https://huggingface.co
2. Click **Sign Up** (free)
3. Go to Settings → Access Tokens
4. Click **New token**
5. Name: `data-cleaning-openenv`
6. Role: `read`
7. Copy the token (starts with `hf_...`)

**Alternative**: Use OpenAI API key instead (starts with `sk-...`)

---

## Step 2: Generate a JWT Secret

Run this locally to generate a secure JWT secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy the output. You will paste it into Render in Step 4.

---

## Step 3: Connect GitHub Repo to Render

1. Go to https://dashboard.render.com
2. Click **New +** → **Blueprint**
3. Connect your GitHub account if not already connected
4. Select `AnubhavKiroula/data-cleaning-openenv`
5. Click **Apply**

Render will read `render.yaml` and create all services automatically.

**Note**: The blueprint creates services but some env vars must be set manually.

---

## Step 4: Set Required Environment Variables

After the blueprint creates services, you need to set two secret variables manually:

### For `data-cleaning-backend` service:

1. Go to dashboard → select `data-cleaning-backend`
2. Click **Environment** tab
3. Add these environment variables:

| Key | Value | Notes |
|-----|-------|-------|
| `JWT_SECRET` | *(paste your generated secret)* | From Step 2 |
| `HF_TOKEN` | *(paste your HF or OpenAI token)* | From Step 1.2 |

4. Click **Save Changes**
5. Click **Manual Deploy** → **Deploy Latest Commit**

### For `data-cleaning-celery` service:

1. Go to dashboard → select `data-cleaning-celery`
2. Click **Environment** tab
3. Add the same `JWT_SECRET` and `HF_TOKEN`
4. Save and deploy

---

## Step 5: Verify Deployment

### Wait for Services to Start

Render free tier services take 2-3 minutes to start (cold start).

### Check Backend Health

```bash
curl https://data-cleaning-backend.onrender.com/health
```

Expected response:
```json
{"status": "ok"}
```

### Check API Docs

Open in browser:
```
https://data-cleaning-backend.onrender.com/docs
```

You should see the FastAPI Swagger UI.

### Check Frontend

Open in browser:
```
https://data-cleaning-frontend.onrender.com
```

You should see the React application loading.

---

## Step 6: Run Database Migrations

If the database tables are not created automatically, run migrations from the backend service shell:

1. Go to dashboard → `data-cleaning-backend`
2. Click **Shell** tab
3. Run:
```bash
python -m alembic upgrade head
```

Alternatively, migrations run automatically via `entrypoint.sh`.

---

## Step 7: Test Full Workflow

1. **Upload a CSV file** through the frontend
2. **Start a cleaning job**
3. **Verify** in the dashboard that jobs appear
4. **Check** Celery worker logs to see tasks processing

---

## Service URLs (After Deployment)

| Service | URL Pattern |
|---------|-------------|
| Frontend | `https://data-cleaning-frontend.onrender.com` |
| Backend API | `https://data-cleaning-backend.onrender.com` |
| API Docs | `https://data-cleaning-backend.onrender.com/docs` |
| Health Check | `https://data-cleaning-backend.onrender.com/health` |

---

## Troubleshooting

### 502 Bad Gateway
- Backend is still starting. Wait 2-3 minutes and refresh.

### Database Connection Error
- Check that `DATABASE_URL` env var is set correctly
- Verify PostgreSQL service is "Live" in Render dashboard

### Redis Connection Error
- Check that `REDIS_URL` env var is set correctly
- Verify Redis service is "Live"

### Frontend Blank Page
- Check browser console for CORS errors
- Verify `VITE_API_BASE_URL` points to the correct backend URL

### Celery Not Processing Jobs
- Check Celery worker logs in Render dashboard
- Verify `REDIS_URL` is set and Redis is running

### Out of Memory
- Free tier has limited RAM. Reduce worker concurrency or upgrade plan.

---

## Cost Optimization

| Service | Render Plan | Monthly Cost |
|---------|-------------|--------------|
| PostgreSQL | Free (512MB) | $0 |
| Redis | Free (100MB) | $0 |
| Backend | Free (512MB) | $0 |
| Frontend | Static (free) | $0 |
| Celery | Free (512MB) | $0 |
| **Total** | | **$0** |

**Note**: Free tier services spin down after 15 minutes of inactivity. First request after idle may take 10-30 seconds.

---

## Scaling Up

If you need more resources:

1. Go to Render dashboard
2. Select a service
3. Click **Settings** → **Plan**
4. Upgrade to a paid plan ($7-25/month per service)

Recommended upgrade order:
1. Backend (handles API requests)
2. PostgreSQL (data storage)
3. Redis (if many queued jobs)

---

## Backups

### PostgreSQL Backups
Render free tier includes **7 days of automated backups**.

To restore:
1. Go to dashboard → `data-cleaning-db`
2. Click **Backups** tab
3. Select a backup and click **Restore**

---

## Next Steps

- [ ] Set up custom domain (optional)
- [ ] Configure monitoring alerts
- [ ] Add SSL certificate (automatic on Render)
- [ ] Set up log aggregation

---

## Support

- Render docs: https://render.com/docs
- Render status: https://status.render.com
- Issues: Open a GitHub issue in this repo
