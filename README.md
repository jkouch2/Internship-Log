# Jayden's Internship Log

A self-updating internship tracker. A scheduled script pulls live postings
from company job boards (Greenhouse & Lever APIs), filters for internships,
and tags anything that matches skills from your resume (Biomek/lab
automation, embedded systems, Arduino, CAD, HPC/computational work, etc).
GitHub Actions re-runs it every 6 hours, so the site stays current with
zero manual work once it's set up.

## One-time setup (5 minutes)

1. **Create a GitHub account** if you don't have one: https://github.com/signup

2. **Create a new repository**
   - Go to https://github.com/new
   - Name it anything, e.g. `internship-log`
   - Keep it **Public** (required for free GitHub Pages hosting)
   - Don't initialize with a README (you already have one)

3. **Push this project to it.** From this folder, run:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR-USERNAME/internship-log.git
   git push -u origin main
   ```

4. **Turn on GitHub Pages**
   - In your repo, go to **Settings → Pages**
   - Under "Build and deployment," set **Source: Deploy from a branch**
   - Branch: `main`, folder: `/ (root)` → **Save**
   - Your site will be live at `https://YOUR-USERNAME.github.io/internship-log/`
     within a minute or two.

5. **Let the scraper run once manually** (don't wait 6 hours for the first data)
   - Go to the **Actions** tab in your repo
   - Click "Update internship listings" in the left sidebar
   - Click **Run workflow → Run workflow**
   - After ~30 seconds, refresh your site — listings will appear

That's it. From here on, it updates itself every 6 hours, forever, for free.

## Customizing

- **Add/remove companies:** edit `GREENHOUSE_COMPANIES` and `LEVER_COMPANIES`
  in `scripts/scrape.py`. To find a company's token, check their careers page —
  if it's hosted on Greenhouse, the URL looks like
  `boards.greenhouse.io/COMPANY_TOKEN`; for Lever it's `jobs.lever.co/COMPANY_TOKEN`.
  A wrong/dead token is skipped automatically, it won't break anything.
- **Change refresh frequency:** edit the `cron` line in
  `.github/workflows/update.yml` (currently every 6 hours).
- **Adjust relevance tagging:** edit `RESUME_KEYWORDS` in `scripts/scrape.py`
  to match your evolving interests/skills.

## How it works

- `scripts/scrape.py` — hits public Greenhouse/Lever job-board APIs (no keys
  needed), filters titles containing "intern," and writes `data/listings.json`
- `.github/workflows/update.yml` — GitHub's free scheduler runs the script
  every 6 hours and commits the updated JSON automatically
- `index.html` / `style.css` / `app.js` — a static page that reads
  `data/listings.json` and renders it, with search and a relevance filter

No server, no hosting bill, no credentials to manage.
