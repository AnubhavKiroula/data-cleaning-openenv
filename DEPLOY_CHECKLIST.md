# Go-Live Checklist - data-cleaning-openenv

## Pre-Deployment Setup

### Accounts to Create (do these first!)

- [ ] **Render.com account** created at https://render.com
  - Sign up with GitHub (recommended)
  - Verify email

- [ ] **HuggingFace account** created at https://huggingface.co
  - Generate access token: Settings → Access Tokens → New token
  - Token name: `data-cleaning-openenv`
  - Role: `read`
  - Copy token (starts with `hf_...`)

**Alternative**: Use OpenAI API key (starts with `sk-...`)

### Secrets to Generate

- [ ] **JWT Secret** generated locally:
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
  - Save this value (you will paste it into Render)

---

## Deployment Steps

### Step 1: Deploy via Render Blueprint

- [ ] Go to https://dashboard.render.com
- [ ] Click **New +** → **Blueprint**
- [ ] Connect GitHub repo: `AnubhavKiroula/data-cleaning-openenv`
- [ ] Select branch: `main`
- [ ] Click **Apply Blueprint**
- [ ] Wait for services to be created (may take 2-3 minutes)

### Step 2: Set Secret Environment Variables

After the blueprint creates services, set these manually:

#### data-cleaning-backend service:
- [ ] `JWT_SECRET` = *(paste your generated secret)*
- [ ] `HF_TOKEN` = *(paste your HuggingFace or OpenAI token)*

#### data-cleaning-celery service:
- [ ] `JWT_SECRET` = *(same as above)*
- [ ] `HF_TOKEN` = *(same as above)*

- [ ] Click **Save Changes**
- [ ] Click **Manual Deploy** → **Deploy Latest Commit** for both services

### Step 3: Wait for Services to Start

- [ ] PostgreSQL status = **Live**
- [ ] Redis status = **Live**
- [ ] Backend status = **Live**
- [ ] Frontend status = **Live**
- [ ] Celery status = **Live**

Wait 2-3 minutes for cold start.

---

## Post-Deployment Verification

### Health Checks (run locally)

```bash
# Check backend health
curl https://data-cleaning-backend.onrender.com/health
# Expected: {"status": "ok"}

# Or use the script:
python scripts/health_check.py https://data-cleaning-backend.onrender.com --frontend https://data-cleaning-frontend.onrender.com
```

- [ ] Backend `/health` returns `{"status": "ok"}`
- [ ] API docs at `/docs` load successfully
- [ ] Frontend loads without errors
- [ ] No CORS errors in browser console

### Functional Testing

- [ ] **Upload a CSV file** through the frontend
- [ ] **Start a cleaning job** from the dashboard
- [ ] **Verify job appears** in job history
- [ ] **Check Celery logs** show tasks processing
- [ ] **Download cleaned data** (if implemented)

### Database Verification

- [ ] Database migrations ran successfully (check backend logs)
- [ ] Tables created in PostgreSQL
- [ ] Data persists after container restart

---

## Documentation Updates

- [ ] README.md updated with live URLs
- [ ] GitHub repo description updated
- [ ] Add live demo link to portfolio/resume
- [ ] (Optional) Create demo video (2-3 minutes)

---

## Monitoring & Maintenance

- [ ] Set up Render alerts (email notifications)
- [ ] Monitor logs weekly
- [ ] Check database storage usage monthly
- [ ] Review costs on Render dashboard

---

## Known Limitations (Free Tier)

| Issue | Explanation | Workaround |
|-------|-------------|------------|
| Cold starts | Services spin down after 15 min idle | Ping `/health` every 10 min via cron |
| 512MB RAM | Limited memory | Reduce batch sizes, upgrade if needed |
| No persistent disk (except DB) | Files lost on restart | Use S3 for file storage |
| Shared CPU | Slower processing | Upgrade to paid plan for production |

---

## Rollback Plan

If deployment fails:

1. Check logs in Render dashboard
2. Re-deploy previous commit: `git revert HEAD`
3. Check environment variables are set correctly
4. Verify database migrations: `alembic history` in backend shell

---

## Cost Summary

| Service | Render Plan | Monthly |
|---------|-------------|---------|
| PostgreSQL | Free | $0 |
| Redis | Free | $0 |
| Backend | Free | $0 |
| Frontend | Static (Free) | $0 |
| Celery | Free | $0 |
| **Total** | | **$0** |

Upgrade to paid plans if traffic grows:
- Starter plan: ~$7-15/month per service
- Standard plan: ~$25-50/month per service

---

## Done!

When all boxes above are checked, your app is live and ready for users.

**Live URLs** (update these after deployment):
- Frontend: https://data-cleaning-frontend.onrender.com
- Backend API: https://data-cleaning-backend.onrender.com
- API Docs: https://data-cleaning-backend.onrender.com/docs
