# 🚀 Phase 4.2 - Production Deployment Checklist

**Status**: Ready for Production | **Estimated Time**: 5 minutes | **Cost**: $0 (NO CREDIT CARD NEEDED)

---

## ✅ What's Already Done

- [x] Backend deployed to HuggingFace Spaces (`https://01ammu-data-cleaning-openenv.hf.space`)
- [x] Database: SQLite (included with HF Spaces)
- [x] API endpoints working
- [ ] **Frontend deployed** ← You are here

---

## 🎯 Your Task: Deploy Frontend to Vercel (5 minutes)

### Step 1: Go to Vercel

1. [ ] Open https://vercel.com
2. [ ] Click **Sign Up**
3. [ ] Choose **GitHub** (simplest)
4. [ ] Authorize Vercel to access your repos

### Step 2: Import Your Project

1. [ ] Click **+ New Project**
2. [ ] Search for: `data-cleaning-openenv`
3. [ ] Click **Import**

### Step 3: Configure Project

1. [ ] **Framework**: Vite
2. [ ] **Root Directory**: `frontend`
3. [ ] **Build Command**: `npm run build` (auto-filled)
4. [ ] **Output Directory**: `dist` (auto-filled)

### Step 4: Add Environment Variable

1. [ ] Scroll to **Environment Variables**
2. [ ] Click **+ Add**
3. [ ] **Name**: `VITE_API_BASE_URL`
4. [ ] **Value**: `https://01ammu-data-cleaning-openenv.hf.space/api`
5. [ ] Click **Add**

### Step 5: Deploy!

1. [ ] Click **Deploy**
2. [ ] Wait 1-2 minutes
3. [ ] ✅ Done! Vercel shows your live URL

---

## ✨ Your Live URLs

Once deployed, you'll have:

| Service | URL |
|---------|-----|
| **Frontend** | `https://data-cleaning-openenv.vercel.app` (or custom domain) |
| **Backend** | `https://01ammu-data-cleaning-openenv.hf.space` |
| **API Docs** | `https://01ammu-data-cleaning-openenv.hf.space/docs` |

---

## 🧪 Verify It Works

### Test in Browser

1. [ ] Open your Vercel URL
2. [ ] Upload a CSV file
3. [ ] Click "Start Cleaning"
4. [ ] Wait for job to complete
5. [ ] Download cleaned data

### Test API

```bash
# Check backend is alive
curl https://01ammu-data-cleaning-openenv.hf.space/health

# Expected: {"status": "ok"}
```

---

## ⚠️ Important Notes

### HF Spaces Sleep Behavior

- **Sleeps after**: 48 hours without access
- **Wake-up time**: ~30 seconds (auto-wakes on first request)
- **Why**: Free tier pauses unused services
- **Solution**: Just refresh the page, it'll wake up

### No Credit Card Needed

- ✅ HuggingFace Spaces: No credit card
- ✅ Vercel: No credit card
- ✅ SQLite Database: Included (no separate DB)
- ✅ **Total Cost: $0 forever**

---

## 📝 Update Your Portfolio

Once live, add to your resume:

```
Live Demo: https://data-cleaning-openenv.vercel.app
(Backend: HuggingFace Spaces, Frontend: Vercel)
```

---

## 🎓 What This Deployment Shows

✨ **Full-Stack Skills**:
- React + TypeScript frontend (Vercel)
- FastAPI backend (HF Spaces)
- SQLite database
- Production deployment experience

✨ **Cloud Knowledge**:
- Multiple cloud platforms (Vercel + HF Spaces)
- Environment variable management
- CI/CD (Vercel auto-deploys on git push)
- Free tier optimization (no credit card = resourcefulness)

---

## Done! 🚀

When all checkboxes above are complete:

1. ✅ Frontend is live on Vercel
2. ✅ Backend is live on HF Spaces
3. ✅ File upload → cleaning → download works
4. ✅ You have a production-grade portfolio project
5. ✅ Zero cost, zero credit cards, 5 minutes setup

**Next**: Share your live link! This is portfolio gold 💎

---

## Troubleshooting

### "Vercel deployment failed"

1. Check GitHub repo is public (Vercel needs access)
2. Verify `frontend` directory exists
3. Check `package.json` has correct build script
4. View Vercel logs for details

### "Frontend can't reach backend"

1. Make sure `VITE_API_BASE_URL` is set to: `https://01ammu-data-cleaning-openenv.hf.space/api`
2. Backend URL must end with `/api` (don't forget!)
3. Re-deploy frontend: Vercel dashboard → Deployments → Redeploy

### "Backend is slow / timing out"

HF Spaces might be sleeping. Just refresh the page. It'll wake up in 30 seconds.

---

## Cost Breakdown

| Component | Service | Monthly Cost | Credit Card |
|-----------|---------|--------------|------------|
| Frontend | Vercel | $0 | No ✓ |
| Backend | HF Spaces | $0 | No ✓ |
| Database | SQLite | $0 | No ✓ |
| **Total** | | **$0** | **No** ✓ |

Perfect for a student portfolio! 🎓
