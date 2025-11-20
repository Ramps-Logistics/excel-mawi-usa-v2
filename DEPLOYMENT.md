# Railway Deployment Guide

## Prerequisites

1. A Railway account (https://railway.app)
2. Your API keys:
   - LLMWhisperer API key
   - OpenAI API key

## Deployment Steps

### 1. Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin <your-github-repo-url>
git push -u origin main
```

### 2. Deploy on Railway

1. Go to https://railway.app
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your repository
5. Railway will auto-detect the Python app

### 3. Configure Environment Variables

In Railway dashboard, go to your project → Variables tab and add:

```
LLMWHISPERER_API_KEY=your_llmwhisperer_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
CORS_ORIGINS=*
```

**For production, use specific origins:**
```
CORS_ORIGINS=https://yourfrontend.com,https://www.yourfrontend.com
```

### 4. Verify Deployment

Railway will:
- ✓ Detect Python from `runtime.txt`
- ✓ Install dependencies from `requirements.txt`
- ✓ Run the command from `Procfile`
- ✓ Assign a public URL

### 5. Test Your API

Once deployed, Railway will provide a URL like: `https://your-app.railway.app`

Test it:
```bash
# Health check
curl https://your-app.railway.app/health

# Test OpenAI
curl -X POST https://your-app.railway.app/test-openai

# Extract invoice
curl -X POST https://your-app.railway.app/extract-invoice \
  -F "file=@your_invoice.xlsx"
```

## Troubleshooting

### View Logs
- Go to Railway dashboard → Your project → Deployments → View logs

### Common Issues

**"Environment variable required" error:**
- Make sure both API keys are set in Railway Variables

**Port binding issues:**
- Railway automatically sets $PORT - don't override it

**Timeout errors:**
- Large files may take 2-3 minutes to process
- Railway has request timeout limits on free tier

## Local vs Production

**Local:**
```bash
uvicorn main:app --reload --port 8000
```

**Railway (automatic):**
```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

The `Procfile` handles this automatically.

