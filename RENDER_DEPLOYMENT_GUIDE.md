# Deploy to Render.com - Complete Guide

**Status:** Ready to Deploy  
**Time:** 15-30 minutes  
**Result:** Public URL like `https://bankanalyzer-xyz.onrender.com`

---

## Step 1: Prepare Your Code

### 1.1 Create `requirements.txt` (Backend)

In your `backend/` directory, create a `requirements.txt` file with all dependencies:

```bash
cd backend
pip freeze > requirements.txt
```

**Or manually create it with essential packages:**

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
python-dotenv==1.0.0
pydantic==2.5.0
pydantic-settings==2.1.0
sentry-sdk[fastapi]==1.40.0
redis==5.0.1
aioredis==2.0.1
psycopg2-binary==2.9.9
boto3==1.29.7
azure-storage-blob==12.19.0
google-cloud-storage==2.14.0
python-multipart==0.0.6
```

Verify it works:
```bash
pip install -r requirements.txt
```

### 1.2 Create `Procfile` (Tells Render how to run your app)

In your **project root** (not in backend/), create a file named `Procfile`:

```
web: cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
```

This tells Render:
- Start a web service
- Go to backend directory
- Run Uvicorn on the port Render provides

### 1.3 Create `build.sh` (Optional but recommended)

In your **project root**, create `build.sh`:

```bash
#!/usr/bin/env bash
pip install -r backend/requirements.txt
```

Make it executable (skip if on Windows):
```bash
chmod +x build.sh
```

---

## Step 2: Push to GitHub

If not already done:

```powershell
# In your project root
git init
git add .
git commit -m "Prepare for Render deployment"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/statementbur_python.git
git push -u origin main
```

**Make sure your code is on GitHub** - Render connects directly to GitHub.

---

## Step 3: Deploy on Render.com

### 3.1 Login to Render

Go to https://dashboard.render.com and login with your account.

### 3.2 Create New Web Service

1. Click **"New +"** button
2. Select **"Web Service"**
3. Connect your GitHub repository:
   - Search for `statementbur_python`
   - Click **"Connect"**

### 3.3 Configure the Service

Fill out the form:

| Field | Value |
|-------|-------|
| **Name** | `bankanalyzer` (or any name) |
| **Environment** | `Python 3` |
| **Build Command** | `pip install -r backend/requirements.txt` |
| **Start Command** | `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT` |
| **Plan** | Free (or Starter if you want better uptime) |

### 3.4 Add Environment Variables

Click **"Advanced"** and scroll down to **"Environment Variables"**.

Add these variables (copy from your `backend/.env`):

```
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///./statement_analyzer.db
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
REDIS_URL=redis://localhost:6379
```

**Important:** 
- Use `REDIS_URL` (Render provides this automatically if you add Redis)
- Use `sqlite:///./statement_analyzer.db` for now (we'll upgrade to PostgreSQL later if needed)

### 3.5 Deploy

Click **"Create Web Service"**

Render will:
1. Clone your code from GitHub
2. Install dependencies
3. Start your app
4. Give you a public URL

This takes 2-5 minutes. You'll see deployment logs in real-time.

---

## Step 4: Once Deployed

### 4.1 Find Your Public URL

Once deployment completes, you'll see:
```
Live URL: https://bankanalyzer-xyz.onrender.com
```

Copy this URL - this is what your beta testers will use!

### 4.2 Test Your Deployment

```powershell
# Replace with your actual Render URL
curl https://bankanalyzer-xyz.onrender.com/health -UseBasicParsing

# Should return:
# {"status":"healthy","database":"connected",...}
```

✅ **If you see "healthy", your app is working!**

### 4.3 Check Logs

In Render dashboard:
1. Click your service name
2. Click **"Logs"** tab to see app output
3. If there are errors, they'll show here

---

## Step 5: Setup UptimeRobot (5 min)

Now that you have a public URL, set up monitoring:

1. Go to https://uptimerobot.com
2. Click **"Add New Monitor"**
3. Enter:
   - **Type:** HTTP(s)
   - **URL:** `https://bankanalyzer-xyz.onrender.com/health`
   - **Interval:** 5 minutes
   - **Alert Email:** Your email
4. Click **"Create Monitor"**

✅ **Now UptimeRobot will alert you if the app goes down!**

---

## Step 6: Configure Database Backups for Production

Your SQLite database is now on Render, but it needs backing up.

### Option A: Upgrade to PostgreSQL (Recommended)

Render provides PostgreSQL databases:

1. In Render dashboard, click **"New +"**
2. Select **"PostgreSQL"**
3. Configure:
   - **Name:** `bankanalyzer-db`
   - **PostgreSQL Version:** 15
4. Click **"Create Database"**

4. Copy the connection string (Render shows it)
5. In your Web Service, update `DATABASE_URL` to the PostgreSQL URL

✅ **PostgreSQL has automatic daily backups!**

### Option B: Keep SQLite with Backup Script

If you keep SQLite:

1. Add this to Render environment variables:
   ```
   BACKUP_STORAGE=local
   ```

2. Set up manual backups (you'll need to download from Render)

**Recommendation:** Use PostgreSQL for production - it's more reliable and Render handles backups automatically.

---

## Step 7: Update Your Backup Schedule

Since the database is now on Render (cloud), update your backup process:

### For Local Testing (on your PC):
```powershell
# Still schedule daily backups on your development machine
# Use the Windows Task Scheduler command from LAUNCH_QUICKSTART.md
```

### For Production (on Render):
```bash
# Option 1: Use PostgreSQL backups (automatic - nothing to do!)
# Option 2: Add backup endpoint to your app that Render can call daily
```

---

## Troubleshooting

### "Deploy Failed - Build Error"

**Check logs:**
1. Click your service in Render
2. Click "Logs"
3. Look for error messages

**Common fixes:**
- Check `requirements.txt` is in backend/ directory
- Check `Procfile` is in project root (not backend/)
- Check all imports in code are valid
- Make sure `main:app` matches your FastAPI app

### "App Deployed but Returns 500 Error"

Check logs in Render:
```
Level: Error
Message: [your error here]
```

Common causes:
- Database not accessible
- Missing environment variable
- Code error on startup

### "Health Endpoint Not Working"

Make sure your `/health` endpoint exists and works:
```bash
# Test locally first
python -m uvicorn backend.main:app --reload
curl http://localhost:8000/health -UseBasicParsing
```

If it works locally but not on Render, check environment variables are set correctly.

---

## After Deployment Checklist

```
✅ Code pushed to GitHub
✅ Web Service created on Render
✅ Environment variables set
✅ Deployment completed successfully
✅ Health endpoint returns 200
✅ UptimeRobot configured with your URL
✅ You have public URL to share with beta testers
```

---

## Next Steps

1. **Test the app** - Visit `https://your-render-url` in browser
2. **Share the URL** - Send to beta testers
3. **Monitor in Render** - Check logs regularly
4. **Monitor uptime** - UptimeRobot alerts if app goes down
5. **Test backups** - If using SQLite, run `backup_database.py` manually

---

## Your Public URL for Beta Testing

Once deployed, your beta testers will access your app at:

```
https://bankanalyzer-xyz.onrender.com
```

Send them this in your beta invitation email.

---

## Questions?

- **Deployment issues:** Check [Render docs](https://render.com/docs)
- **App errors:** Check Render logs tab
- **Health check fails:** Test locally first with `curl http://localhost:8000/health`
- **Database issues:** Check DATABASE_URL environment variable

---

**Status:** Ready to deploy  
**Estimated time:** 20 minutes  
**Result:** Public URL for 50-100 beta testers
