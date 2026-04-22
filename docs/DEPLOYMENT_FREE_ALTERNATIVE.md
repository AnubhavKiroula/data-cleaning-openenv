# Phase 4.2b - FREE Deployment Guide (Vercel + Oracle Cloud + Supabase)

**Total Cost: $0 FOREVER** | **No Credit Card Needed** | **No Trial Expiration**

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

## Step 2: Deploy Backend to Oracle Cloud Always Free (TRULY FREE, NO EXPIRATION)

### 2A. Create Oracle Cloud Account

1. Go to https://www.oracle.com/cloud/free/
2. Click **Sign Up** → Fill in details
   - **Note**: Oracle requires a credit card for verification, but **WILL NOT CHARGE YOU** for Always Free services
   - Set spending limit to $0 if you want (optional)
3. Verify email and create account
4. Log in to Oracle Cloud console

### 2B. Create Compute Instance

1. Go to **Compute** → **Instances**
2. Click **Create Instance**
3. Configure:
   - **Name**: data-cleaning-backend
   - **Image**: Ubuntu 22.04 (Free Tier eligible)
   - **Shape**: Ampere (ARM) - always in free tier
   - **Network**: Use default VCN
4. Add SSH key:
   - Download the private key file (save it!)
   - This is your access key
5. Click **Create**
6. Wait 2-3 minutes for instance to boot
7. Copy the **Public IP Address**

### 2C. Connect and Deploy Backend

```bash
# SSH into instance (from your local machine)
ssh -i /path/to/private-key ubuntu@[PUBLIC_IP]

# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.10 python3-pip git redis-server

# Clone your repo
git clone https://github.com/AnubhavKiroula/data-cleaning-openenv.git
cd data-cleaning-openenv

# Install Python dependencies
pip3 install -r backend/requirements.txt

# Create .env file
cat > backend/.env << EOF
DATABASE_URL=postgresql://postgres:[PASSWORD]@[SUPABASE_HOST]/postgres
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=[Your generated secret]
ENVIRONMENT=production
LOG_LEVEL=INFO
API_BASE_URL=https://api-inference.huggingface.co/v1
MODEL_NAME=meta-llama/Llama-3.2-1B-Instruct
HF_TOKEN=[Your HuggingFace token]
EOF

# Start Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Start backend (in screen or tmux so it stays running)
screen -S backend
cd backend && python3 -m uvicorn app:app --host 0.0.0.0 --port 8000
# Press Ctrl+A then D to detach
```

### 2D. Allow Firewall Access

```bash
# Allow port 8000
sudo iptables -I INPUT -p tcp -m tcp --dport 8000 -j ACCEPT

# Save (persistent)
sudo apt install -y iptables-persistent
sudo iptables-save | sudo tee /etc/iptables/rules.v4
```

### 2E. Set Up a Permanent Process Manager (Optional but Recommended)

```bash
# Install supervisord
sudo apt install -y supervisor

# Create config
sudo cat > /etc/supervisor/conf.d/backend.conf << EOF
[program:data-cleaning-backend]
directory=/home/ubuntu/data-cleaning-openenv/backend
command=python3 -m uvicorn app:app --host 0.0.0.0 --port 8000
user=ubuntu
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/backend.log
EOF

# Start supervisor
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start data-cleaning-backend
```

**Backend URL**: `http://[PUBLIC_IP]:8000`

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
   VITE_API_BASE_URL=http://[ORACLE_PUBLIC_IP]:8000/api
   ```
   (Replace with your Oracle instance public IP)
6. Click **Deploy**

**Frontend URL**: `https://[vercel-domain].vercel.app`

---

## Step 4: Verify Deployment

```bash
# Test backend health
curl http://[ORACLE_PUBLIC_IP]:8000/health

# Test API docs
curl http://[ORACLE_PUBLIC_IP]:8000/docs

# Run health check script
python scripts/health_check.py http://[ORACLE_PUBLIC_IP]:8000 --frontend https://[vercel-frontend-url]
```

---

## Cost Breakdown

| Service | Plan | Cost | Note |
|---------|------|------|------|
| Supabase PostgreSQL | Free Tier | $0 | Free forever |
| Oracle Cloud Backend | Always Free | $0 | 1 free ARM instance forever |
| Oracle Cloud Redis | Always Free | $0 | Runs on same instance |
| Vercel Frontend | Free | $0 | Free forever |
| **Total** | | **$0** | **NO EXPIRATION** |

---

## Advantages

✅ **Truly FREE forever** - No trial expiration (unlike Railway)
✅ **No credit card needed** - Oracle just needs verification (won't charge)
✅ **Always running** - No cold starts like Render
✅ **Production-grade** - Real server, real database
✅ **Full control** - SSH access to backend for debugging
✅ **Professional URLs** - Vercel gives you custom domain
✅ **Unlimited requests** - Not metered like other free tiers

---

## Disadvantages

⚠️ **Setup takes longer** - Need to SSH and configure manually (~10 min)
⚠️ **Oracle requires credit card** - For verification only, won't charge
⚠️ **Need to manage server** - Update OS, manage processes (supervisord helps)
⚠️ **Need SSH skills** - But steps above walk you through it

---

## Quick Setup (20 minutes total)

1. **Supabase**: 2 min (just click, wait)
2. **Oracle Cloud**: 5 min (create account, create instance)
3. **SSH & Deploy**: 10 min (copy-paste commands)
4. **Vercel**: 2 min (connect GitHub, set env var)
5. **Firewall**: 1 min (allow port 8000)

---

## Keeping Backend Running Forever

The backend will stay running because:
- ✅ Oracle Always Free instances never expire
- ✅ supervisord auto-restarts if process crashes
- ✅ No idle timeouts like Railway/Render

**Check status anytime:**
```bash
sudo supervisorctl status data-cleaning-backend
```

---

## Next Steps

1. ✅ Create Oracle Cloud account + instance
2. ✅ SSH and deploy backend
3. ✅ Create Supabase database
4. ✅ Deploy frontend on Vercel
5. ✅ Test file upload → cleaning → results
6. ✅ Share link on portfolio
7. ✅ Create demo video

Done! You have a **production-grade, zero-cost data cleaning platform** 🚀
