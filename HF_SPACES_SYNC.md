# 🤗 HuggingFace Spaces Sync Guide

Your latest code is ready on GitHub! Here's how to sync HF Spaces with the latest code.

## Why?

HF Spaces had old binary files (models, venv) in git history. The cleaner approach is to sync HF Spaces directly from GitHub.

## Steps to Sync HF Spaces

### Option 1: Automatic Sync (Recommended)

1. Go to: https://huggingface.co/spaces/01ammu/data-cleaning-openenv/settings
2. Scroll to **"Linked Repository"**
3. Enter: `https://github.com/AnubhavKiroula/data-cleaning-openenv`
4. Click **"Link Repository"**
5. HF Spaces will auto-pull and redeploy! ✅

### Option 2: Manual Redeploy

1. Go to: https://huggingface.co/spaces/01ammu/data-cleaning-openenv
2. Click **Settings** (gear icon)
3. Scroll down → **"Repo settings"**
4. Find your GitHub repo and click **"Sync"**
5. Wait 2-3 minutes for redeploy

## What Gets Updated

- ✅ Latest backend code
- ✅ Latest frontend code  
- ✅ Latest API endpoints
- ✅ Updated documentation
- ✅ Deployment guides (Vercel, etc.)

**NOT updated** (on purpose):
- ❌ `.venv/` (created automatically)
- ❌ `models/` (created on first ML training)
- ❌ `plots/` (generated during training)

These are excluded from git to keep repos small and clean.

## Live URLs After Sync

- **Backend**: https://01ammu-data-cleaning-openenv.hf.space
- **Frontend**: Deploy to Vercel separately (see DEPLOY_CHECKLIST.md)
- **API Docs**: https://01ammu-data-cleaning-openenv.hf.space/docs

## Done!

HF Spaces will now stay in sync with your GitHub repo. Any push to `main` = automatic redeploy! 🚀
