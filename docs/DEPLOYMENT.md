# FlipIQ Deployment Guide

## Overview

This guide covers deploying FlipIQ for customer validation:
1. **Streamlit Dashboard** - The main product demo
2. **Landing Page** - Lead capture and marketing
3. **Analytics** - Tracking signups and engagement

---

## Part 1: Streamlit Cloud Deployment

### Prerequisites
- GitHub account
- Streamlit Cloud account (free at streamlit.io)

### Step 1: Prepare Repository

Ensure your repository has these files:
```
zillow/
├── streamlit_app.py          # Main dashboard
├── requirements.txt          # Python dependencies
├── src/                      # Source modules
├── data/
│   ├── raw/zillow/          # Zillow CSV files
│   └── processed/           # Agent outputs
└── .streamlit/
    └── config.toml          # Streamlit config (optional)
```

### Step 2: Create requirements.txt

If not already present, create/update `requirements.txt`:
```
streamlit>=1.30.0
pandas>=2.0.0
numpy>=1.24.0
plotly>=5.18.0
scikit-learn>=1.3.0
matplotlib>=3.7.0
seaborn>=0.13.0
```

### Step 3: Create Streamlit Config (Optional)

Create `.streamlit/config.toml`:
```toml
[theme]
primaryColor = "#2563eb"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f8fafc"
textColor = "#1e293b"
font = "sans serif"

[server]
maxUploadSize = 200
enableCORS = false

[browser]
gatherUsageStats = false
```

### Step 4: Deploy to Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click "New app"
3. Connect your GitHub repository
4. Select:
   - Repository: `yourusername/flipiq` (or your repo name)
   - Branch: `main`
   - Main file path: `streamlit_app.py`
5. Click "Deploy"

### Step 5: Configure Secrets (If Needed)

If your app needs secrets (API keys, etc.):
1. In Streamlit Cloud, go to your app settings
2. Click "Secrets"
3. Add secrets in TOML format:
```toml
[api_keys]
zillow_api = "your_api_key_here"

[database]
connection_string = "your_connection_string"
```

Access in code:
```python
import streamlit as st
api_key = st.secrets["api_keys"]["zillow_api"]
```

### Step 6: Custom Domain (Optional)

1. In Streamlit Cloud, go to app settings
2. Click "Custom domain"
3. Add your domain: `app.flipiq.ai`
4. Add CNAME record in your DNS:
   - Type: CNAME
   - Name: app
   - Value: `your-app.streamlit.app`

### Updating Deployed App

When you push to GitHub, Streamlit Cloud auto-redeploys:
```bash
git add .
git commit -m "Update dashboard"
git push origin main
```

Force redeploy:
1. Go to Streamlit Cloud
2. Click "Reboot app" in menu

---

## Part 2: Landing Page Deployment

### Option A: Netlify (Recommended)

#### Step 1: Prepare Files
```
landing/
├── index.html      # Rename landing_page.html
├── images/         # Any images
└── _redirects      # For SPA routing (optional)
```

#### Step 2: Deploy via Netlify

**Method 1: Drag and Drop**
1. Go to [netlify.com](https://netlify.com)
2. Sign up / log in
3. Drag your `landing/` folder to the deploy area
4. Get instant URL

**Method 2: GitHub Integration**
1. Create new site from Git
2. Connect GitHub repository
3. Configure build:
   - Base directory: `/` (or where HTML lives)
   - Build command: (leave empty for static)
   - Publish directory: `/` (or your folder)
4. Deploy

#### Step 3: Custom Domain
1. In Netlify, go to Domain settings
2. Add custom domain: `flipiq.ai`
3. Update nameservers at your registrar to Netlify's:
   - dns1.p01.nsone.net
   - dns2.p01.nsone.net
   - dns3.p01.nsone.net
   - dns4.p01.nsone.net

Or add CNAME if using subdomain:
- Type: CNAME
- Name: www
- Value: `your-site.netlify.app`

#### Step 4: Enable HTTPS
- Netlify provides free SSL automatically
- Force HTTPS in Domain settings

#### Step 5: Form Handling (Netlify Forms)

Update your form to use Netlify Forms:
```html
<form name="signup" method="POST" data-netlify="true" netlify-honeypot="bot-field">
    <input type="hidden" name="form-name" value="signup">
    <p class="hidden">
        <label>Don't fill this out: <input name="bot-field"></label>
    </p>
    <!-- rest of form fields -->
</form>
```

View submissions in Netlify dashboard under Forms.

---

### Option B: Vercel

#### Step 1: Install Vercel CLI
```bash
npm install -g vercel
```

#### Step 2: Deploy
```bash
cd /path/to/landing
vercel
```

Follow prompts:
- Set up and deploy: Yes
- Link to existing project: No
- Project name: flipiq-landing
- Directory: ./

#### Step 3: Custom Domain
```bash
vercel domains add flipiq.ai
```

Or in Vercel dashboard:
1. Go to Project Settings > Domains
2. Add your domain
3. Follow DNS instructions

---

### Option C: GitHub Pages

#### Step 1: Enable GitHub Pages
1. Go to repository Settings
2. Scroll to Pages section
3. Source: Deploy from branch
4. Branch: main, / (root)
5. Save

#### Step 2: Access Your Site
- URL: `https://yourusername.github.io/flipiq/landing_page.html`

#### Step 3: Custom Domain
1. In Pages settings, add custom domain
2. Create CNAME file in repo root:
```
flipiq.ai
```
3. Add DNS records:
   - A record: 185.199.108.153
   - A record: 185.199.109.153
   - A record: 185.199.110.153
   - A record: 185.199.111.153

---

## Part 3: Form Integration (Formspree)

### Step 1: Create Formspree Account
1. Go to [formspree.io](https://formspree.io)
2. Sign up (free tier: 50 submissions/month)

### Step 2: Create New Form
1. Click "New Form"
2. Name it "FlipIQ Signups"
3. Copy the endpoint URL (looks like `https://formspree.io/f/xxxxxxxx`)

### Step 3: Update Landing Page
Replace in `landing_page.html`:
```html
<form action="YOUR_FORMSPREE_ENDPOINT" method="POST">
```
with:
```html
<form action="https://formspree.io/f/xxxxxxxx" method="POST">
```

### Step 4: Configure Notifications
In Formspree dashboard:
1. Go to Form Settings
2. Enable email notifications
3. Add team members if needed

### Step 5: Test Submission
1. Open landing page
2. Fill out form
3. Submit
4. Check Formspree dashboard for submission

---

## Part 4: Analytics Setup

### Google Analytics 4

#### Step 1: Create Property
1. Go to [analytics.google.com](https://analytics.google.com)
2. Create new property
3. Name: "FlipIQ"
4. Select Web platform
5. Enter your domain

#### Step 2: Get Measurement ID
- Format: G-XXXXXXXXXX
- Found in Admin > Data Streams > Your stream

#### Step 3: Add to Landing Page

Uncomment and update in `landing_page.html`:
```html
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
<script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('js', new Date());
    gtag('config', 'G-XXXXXXXXXX');
</script>
```

#### Step 4: Set Up Conversion Tracking

In Google Analytics:
1. Go to Admin > Events
2. Create event: `sign_up`
3. Mark as conversion

Add to form submission handler:
```javascript
gtag('event', 'sign_up', {
    'method': 'early_access_form',
    'event_category': 'engagement'
});
```

#### Step 5: Create Dashboard

Recommended metrics to track:
- Sessions
- Users (new vs returning)
- Page views by page
- Form submissions (conversions)
- Traffic sources
- Geographic distribution

### Alternative: Plausible Analytics

Privacy-friendly alternative:
1. Sign up at [plausible.io](https://plausible.io)
2. Add script:
```html
<script defer data-domain="flipiq.ai" src="https://plausible.io/js/script.js"></script>
```

---

## Part 5: Monitoring & Maintenance

### Streamlit Dashboard Health

#### Monitor Uptime
Use UptimeRobot (free):
1. Create account at [uptimerobot.com](https://uptimerobot.com)
2. Add monitor for your Streamlit URL
3. Set check interval: 5 minutes
4. Enable email alerts

#### Check Logs
In Streamlit Cloud:
1. Click "Manage app"
2. View logs for errors
3. Set up alerts for failures

### Landing Page Health

#### Netlify Status
- Check [netlifystatus.com](https://netlifystatus.com)
- View deploy logs in dashboard

#### Page Speed
Test with:
- [PageSpeed Insights](https://pagespeed.web.dev)
- [GTmetrix](https://gtmetrix.com)

Optimize if needed:
- Compress images
- Minify CSS/JS
- Enable caching headers

### Form Submission Monitoring

Set up in Formspree:
1. Daily/weekly email digests
2. Slack integration for instant notifications
3. Export submissions to Google Sheets

---

## Deployment Checklist

### Before Launch
- [ ] Test Streamlit dashboard loads correctly
- [ ] Test all dashboard tabs function
- [ ] Test landing page loads on mobile
- [ ] Test form submission works
- [ ] Verify analytics tracking
- [ ] Check HTTPS enabled
- [ ] Test all links work

### DNS Configuration
- [ ] Point domain to hosting
- [ ] Configure subdomain for dashboard (app.flipiq.ai)
- [ ] Enable SSL certificates
- [ ] Test www and non-www redirects

### Post-Launch
- [ ] Submit sitemap to Google Search Console
- [ ] Set up monitoring alerts
- [ ] Document admin credentials
- [ ] Schedule regular backups

---

## Environment Variables

If deploying with environment variables:

### Streamlit Cloud
Add in Secrets management (TOML format)

### Netlify
Add in Site settings > Environment variables

### Vercel
Add in Project settings > Environment variables

Common variables:
```
FORMSPREE_ENDPOINT=https://formspree.io/f/xxxxx
GA_MEASUREMENT_ID=G-XXXXXXXXXX
STREAMLIT_URL=https://app.flipiq.ai
```

---

## Troubleshooting

### Streamlit Won't Deploy
1. Check requirements.txt for typos
2. Verify all imports exist
3. Check for hardcoded local paths
4. View deploy logs for errors

### Form Not Submitting
1. Verify Formspree endpoint is correct
2. Check browser console for errors
3. Test in incognito mode
4. Verify not blocked by ad blocker

### Analytics Not Tracking
1. Check measurement ID
2. Verify script is not commented out
3. Check for ad blockers
4. Test in GA real-time view

### Custom Domain Not Working
1. Allow 24-48 hours for DNS propagation
2. Verify DNS records are correct
3. Check nameserver settings
4. Test with `dig yourdomain.com`

---

## Quick Reference URLs

| Service | Dashboard URL |
|---------|---------------|
| Streamlit Cloud | share.streamlit.io |
| Netlify | app.netlify.com |
| Vercel | vercel.com/dashboard |
| Formspree | formspree.io/forms |
| Google Analytics | analytics.google.com |
| UptimeRobot | uptimerobot.com |
