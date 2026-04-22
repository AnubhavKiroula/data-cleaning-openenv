# Phase 4.2b - FREE Deployment Guide (Vercel + Railway + Supabase)

**Total Cost: $0 forever** | **No Credit Card Needed**

---

## Step 1: Create Supabase PostgreSQL Database (FREE)

1. Go to https://supabase.com
2. Click **Sign Up** → Use GitHub (no email needed)
3. Create new project:
   - **Name**: data-cleaning
   - **Database Password**: Generate strong password
   - **Region**: Pick closest to you
   - **Plan**: Free
4. Click **Create New Project** (wait 2-3 minutes)
5. Once ready, go to **Settings** → **Database**
6. Copy the **Connection String** under "Connection pooling" section
7. Format: `postgresql://postgres:[PASSWORD]@[HOST]:[PORT]/postgres`
8. Save this as `DATABASE_URL`

---

## Step 2: Deploy Backend to Railway (FREE $5/month credit)

1. Go to https://railway.app
2. Click **Login with GitHub**
3. Select repo: `AnubhavKiroula/data-cleaning-openenv`
4. Click **Deploy**
5. Railway will auto-detect and ask for configuration
6. Create new service:
   - **Name**: data-cleaning-backend
   - **Build Command**: Leave blank (Railway auto-detects)
   - **Start Command**: `bash ./backend/entrypoint.sh`
   - **Port**: 8000

7. Add environment variables:
   ```
   DATABASE_URL=postgresql://postgres:[PASSWORD]@[SUPABASE_HOST]/postgres
   REDIS_URL=redis://localhost:6379/0  (Railway provides this)
   JWT_SECRET=[Your generated secret]
   ENVIRONMENT=production
   LOG_LEVEL=INFO
   API_BASE_URL=https://api-inference.huggingface.co/v1
   MODEL_NAME=meta-llama/Llama-3.2-1B-Instruct
   HF_TOKEN=[Your HuggingFace token]
   ```

8. Add Redis plugin:
   - Click **Add Service** → **Redis**
   - Railway auto-configures REDIS_URL

9. Deploy!

---

## Step 3: Deploy Frontend to Vercel (FREE)

1. Go to https://vercel.com
2. Click **Import Project**
3. Select your GitHub repo
4. Configure:
   - **Framework**: Vite
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
5. Add environment variable:
   ```
   VITE_API_BASE_URL=https://[railway-backend-url]/api
   ```
   (Railway gives you the public URL after deployment)
6. Click **Deploy**

---

## Step 4: Verify Deployment

```bash
# Test backend health
curl https://[railway-backend-url]/health

# Test API docs
curl https://[railway-backend-url]/docs

# Run health check script
python scripts/health_check.py https://[railway-backend-url] --frontend https://[vercel-frontend-url]
```

---

## Cost Breakdown

| Service | Plan | Cost | Renewal |
|---------|------|------|---------|
| Supabase PostgreSQL | Free | $0 | Every month |
| Railway Backend | Free credit | $5/mo | Every month |
| Railway Redis | Free credit | Included | Every month |
| Vercel Frontend | Free | $0 | Every month |
| **Total** | | **$0** | **$5 credit** |

Railway gives you **$5/month free credit** that renews every month = always free!

---

## Advantages

✅ Zero credit card needed
✅ Zero cost forever
✅ Production-grade services
✅ Better than Render free tier (no cold starts!)
✅ Automatic deployments on git push
✅ Professional URLs

---

## Disadvantages

⚠️ Railway: Need GitHub account (free)
⚠️ Supabase: Free tier has limits (but plenty for student project)
⚠️ Limited to $5 credit (enough for low traffic)

---

## Quick Setup (5 minutes total)

1. Supabase: 2 minutes (just click, wait)
2. Railway: 2 minutes (connect GitHub, auto-deploy)
3. Vercel: 1 minute (connect GitHub, set env var)

That's it! You're live 🚀

---

## Next Steps

1. Update GitHub Secrets with production URLs
2. Test file upload → cleaning job → results
3. Share live link on portfolio
4. Create demo video

Done!
