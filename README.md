# Job Radar 📡

A self-hosted job board aggregator that pulls postings from Google Alerts RSS feeds, scores them against your resume, and helps you stay on top of your search — all from a local web app running on your own machine.

**No subscription. No tracking. Your data stays on your computer.**

---

## How It Works

1. You set up Google Alerts using `site:`-targeted search strings that point directly at job board platforms (Greenhouse, Lever, Ashby, Workday, LinkedIn, Indeed) and paste the RSS URLs into `config.json`.
2. Job Radar polls those feeds, fetches the full job posting text, and scores each listing two ways:
   - **ATS Score** — keyword overlap between the posting and your resume.
   - **Fit Score** — a holistic 0–10 score factoring in title match, experience level, domain alignment, and work style.
3. Postings appear in a kanban-style board (New → Saved → Applied → Waiting → Rejected). Low-quality postings and editorial content are auto-filtered before they ever reach your board.
4. Each listing has a right-side panel with salary, location, work style, matched/missing keywords, company info, and notes. LinkedIn postings show a login notice instead of scores since their content is behind a login wall.

---

## AI Setup Assistant

> **For users setting up with AI help:** Paste this README into your AI chat and say *"Help me set up Job Radar."* The AI will ask you everything it needs, then walk you through the full setup with a personalized `config.json` ready to paste in.

---

<!-- AI_SETUP_INSTRUCTIONS
If a user shares this README and asks for help setting up Job Radar, do NOT start giving instructions immediately. Instead, ask the following questions one group at a time and wait for answers before proceeding. Once you have all the answers, generate a complete personalized config.json and walk through setup step by step.

QUESTIONS TO ASK (in this order):

GROUP 1 — System & Installation
- What operating system are you on? (macOS, Windows, or Linux)
- Do you have Python 3.10 or higher already installed? (They can check by running: python3 --version on Mac/Linux or python --version on Windows)
- Do you have Git installed, or would you prefer to download a ZIP file?

GROUP 2 — Resume
- What is the full file path to your resume .docx file? (Example: /Users/yourname/Documents/MyResume.docx on Mac, or C:\Users\yourname\Documents\MyResume.docx on Windows)
- If they don't know the path, tell them to right-click the file → Get Info (Mac) or Properties (Windows) and look for the Location field, then combine it with the filename.

GROUP 3 — Job Search Profile
- What job titles are you targeting? (Ask them to list all titles they want to appear for — e.g. Senior Product Manager, Customer Success Manager, Implementation Manager)
- How many years of relevant experience do you have?
- What industries or domains do you prefer? (Common values: saas, api, platform, proptech, fintech, edtech, healthtech, marketplace — they can list multiple)

GROUP 4 — Location Preferences
- Are you looking for remote roles only, or are you open to hybrid or onsite?
- If open to hybrid or onsite: what cities or regions are you willing to commute to? (e.g. San Francisco, Bay Area, New York)
- Are you based in the US, or open to international roles?

GROUP 5 — Google Alerts (tell them to do this step now if they haven't yet)
- Have you set up your Google Alerts yet? If not, walk them through the Google Alerts Setup section of this README using their specific job titles to determine which of the 9 alert strings are relevant for them. Not all 9 will apply to everyone — help them choose only the ones that match their target roles.
- Once they have set up their alerts, ask them to paste each RSS feed URL along with a label for it.

AFTER COLLECTING ALL ANSWERS:
1. Generate a complete, filled-in config.json they can copy and paste directly. Use their actual resume path, titles, years of experience, domains, location preferences, and RSS feed URLs. Do not leave any placeholder values unfilled.
2. Walk through the installation steps for their specific OS step by step.
3. Tell them which of the 9 alert strings from the README are relevant to their titles, and which they can skip.
4. Confirm the port is 5000 (default) unless they say something else is using that port.
5. Tell them to launch the app and click Refresh Feeds, and what to expect on first run.
-->

---

## Prerequisites

Before running the setup script you need **Python 3.10+** and a way to download the files. Everything else (pip, virtual environment, all Python packages) is handled automatically by the setup script.

Jump to your operating system:
- [macOS setup](#macos-setup)
- [Windows setup](#windows-setup)
- [Linux setup](#linux-setup)

---

## macOS Setup

### 1. Check if Python is already installed

Open **Terminal** (`Cmd + Space` → type "Terminal" → Enter) and run:

```bash
python3 --version
```

If you see `Python 3.10.x` or higher, skip to step 2. Otherwise install Python:

**Option A — Homebrew (recommended):**
```bash
# Install Homebrew if you don't have it:
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Then install Python:
brew install python@3.12
```

**Option B — Direct download:**
Download the macOS installer from [python.org/downloads](https://www.python.org/downloads/) and run it.

### 2. Check if Git is installed

```bash
git --version
```

If you see "command not found", running this command will prompt macOS to install Xcode Command Line Tools (which includes Git). Click **Install** and follow the prompts. Alternatively:

```bash
brew install git
```

### 3. Download and install Job Radar

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/job-radar.git
cd job-radar

# Run one-time setup
chmod +x install.sh
./install.sh
```

`install.sh` will create a virtual environment, install all dependencies, and build a **Job Radar.app** on your Desktop.

> **After the first install, no terminal needed.** Double-click **Job Radar.app** from your Desktop to start.

---

## Windows Setup

Windows requires Python and Git for Windows. The setup script (`install.bat`) handles everything else.

### 1. Install Python

Download the installer from [python.org/downloads](https://www.python.org/downloads/).

> ⚠️ **Critical:** On the first screen of the installer, check the box that says **"Add Python to PATH"** before clicking Install Now. If you skip this, the scripts won't be able to find Python.

Verify it worked — open **Command Prompt** (`Windows key` → type "cmd" → Enter) and run:

```cmd
python --version
```

You should see `Python 3.10.x` or higher.

### 2. Install Git for Windows

Download from [git-scm.com/download/win](https://git-scm.com/download/win) and run the installer. The default options are fine.

Verify:

```cmd
git --version
```

### 3. Download Job Radar

**Option A — Command Prompt:**
```cmd
git clone https://github.com/YOUR_USERNAME/job-radar.git
```

**Option B — No Git:** Click the green **Code** button on the GitHub page → **Download ZIP** → extract the folder anywhere on your computer (e.g., your Desktop or Documents).

### 4. Run setup

Open the `job-radar` folder. **Double-click `install.bat`**.

`install.bat` will:
- Create a Python virtual environment with all dependencies installed inside it
- Create a **Job Radar** shortcut on your Desktop

> **After the first install, no terminal needed.** Double-click the **Job Radar** shortcut on your Desktop to start.

### What gets installed automatically (all platforms)

Once Python is present, the setup script takes care of all Python packages:

| Package | What it does |
|---|---|
| `flask` | Local web server that runs the app |
| `feedparser` | Parses Google Alert RSS feeds |
| `requests` | Fetches full job posting pages |
| `beautifulsoup4` | Extracts text from job posting HTML |
| `lxml` | HTML parser used by BeautifulSoup |
| `python-docx` | Reads your resume `.docx` file |

These are installed into an isolated virtual environment (`venv/`) inside the job-radar folder, so they don't affect anything else on your computer and can be removed simply by deleting the folder.

---

## Linux Setup

```bash
# Install Python and Git
sudo apt update && sudo apt install python3 python3-pip python3-venv git

# Clone and install
git clone https://github.com/YOUR_USERNAME/job-radar.git
cd job-radar
chmod +x install.sh
./install.sh
```

Launch with `./launch.command` from the terminal, or add it as a launcher in your desktop environment.

---

## Other requirements (all platforms)

- A resume saved as a `.docx` (Word) file
- A Google account (for Google Alerts)

---

## Configuration

Open `config.json` and fill in the required fields before launching for the first time.

### Resume path

```json
"resume_path": "path/to/your/resume.docx"
```

Use an absolute path or a path relative to the `job-radar` folder. The app extracts keywords from your resume on first launch and caches them so subsequent starts are instant.

### Google Alerts RSS feeds

Each entry in the `rss_feeds` array needs a URL. See the **Google Alerts Setup** section below for how to get those URLs.

```json
"rss_feeds": [
  {
    "label": "Senior PM — Core",
    "url": "YOUR_GOOGLE_ALERT_RSS_URL_HERE"
  }
]
```

| Field | Purpose |
|---|---|
| `label` | Display name shown in the UI |
| `url` | Google Alert RSS URL |

---

## Google Alerts Setup

### Strategy

Job Radar uses Google Alerts with `site:` operators to target job board platforms directly. This means your alerts only return actual job postings — not news articles, press releases, or blog posts that happen to mention your target titles.

The `site:` operator **does work** in Google Alerts. Each alert string below combines all major platforms in a single query so you need fewer alerts with broader coverage.

### Creating an alert

1. Go to [google.com/alerts](https://www.google.com/alerts)
2. Paste one of the search strings below exactly as written
3. Click **Show options** and set:
   - **How often:** As it happens
   - **Sources:** Automatic
   - **Language:** English
   - **Region:** Any Region
   - **How many:** All results
   - **Deliver to:** RSS feed
4. Click **Create Alert**
5. Click the orange RSS icon next to the new alert to get the feed URL
6. Paste that URL into `config.json` with a descriptive label

### Recommended search strings

Set up one alert per string. These cover all major ATS platforms (Greenhouse, Lever, Ashby, Workday) plus LinkedIn and Indeed in every query.

**Alert 1 — Core PM Titles**
```
site:boards.greenhouse.io OR site:jobs.lever.co OR site:jobs.ashbyhq.com OR site:myworkdayjobs.com OR site:linkedin.com/jobs OR site:indeed.com "senior product manager" OR "lead product manager" OR "principal product manager" remote
```

**Alert 2 — Technical / Platform / Staff PM**
```
site:boards.greenhouse.io OR site:jobs.lever.co OR site:jobs.ashbyhq.com OR site:myworkdayjobs.com OR site:linkedin.com/jobs OR site:indeed.com "technical product manager" OR "platform product manager" OR "staff product manager" remote
```

**Alert 3 — Product Owner / Associate / Group PM**
```
site:boards.greenhouse.io OR site:jobs.lever.co OR site:jobs.ashbyhq.com OR site:myworkdayjobs.com OR site:linkedin.com/jobs OR site:indeed.com "senior product owner" OR "product owner" OR "associate product manager" OR "group product manager" remote
```

**Alert 4 — API / Integration / Developer PM**
```
site:boards.greenhouse.io OR site:jobs.lever.co OR site:jobs.ashbyhq.com OR site:myworkdayjobs.com OR site:linkedin.com/jobs OR site:indeed.com "product manager" "api platform" OR "product manager" "integration platform" OR "product manager" "developer platform" OR "product manager" "data platform" remote
```

**Alert 5 — PropTech / Real Estate PM**
```
site:boards.greenhouse.io OR site:jobs.lever.co OR site:jobs.ashbyhq.com OR site:myworkdayjobs.com OR site:linkedin.com/jobs OR site:indeed.com "product manager" "real estate" OR "product manager" "proptech" OR "product manager" "MLS" remote
```

**Alert 6 — Director / VP / Head of Product**
```
site:boards.greenhouse.io OR site:jobs.lever.co OR site:jobs.ashbyhq.com OR site:myworkdayjobs.com OR site:linkedin.com/jobs OR site:indeed.com "director of product" OR "vp of product" OR "head of product" OR "director of product management" OR "chief product officer" remote
```

**Alert 7 — CSM All Levels**
```
site:boards.greenhouse.io OR site:jobs.lever.co OR site:jobs.ashbyhq.com OR site:myworkdayjobs.com OR site:linkedin.com/jobs OR site:indeed.com "customer success manager" OR "senior customer success manager" OR "enterprise customer success manager" OR "customer success lead" OR "client success manager" remote
```

**Alert 8 — Technical CS / TAM / Partner / Strategic**
```
site:boards.greenhouse.io OR site:jobs.lever.co OR site:jobs.ashbyhq.com OR site:myworkdayjobs.com OR site:linkedin.com/jobs OR site:indeed.com "technical customer success manager" OR "technical account manager" OR "partner success manager" OR "strategic account manager" remote
```

**Alert 9 — Implementation / CS Operations / Solutions**
```
site:boards.greenhouse.io OR site:jobs.lever.co OR site:jobs.ashbyhq.com OR site:myworkdayjobs.com OR site:linkedin.com/jobs OR site:indeed.com "implementation manager" OR "customer success operations" OR "support operations manager" OR "solutions consultant" remote
```

> **Note on LinkedIn:** LinkedIn postings are included in the alerts but cannot be scored because LinkedIn requires a login to view full job content. They appear on your board with a blue "LinkedIn" badge and a notice to navigate directly to the posting. The URL opens the listing in your browser where you can log in and read the full description.

> **Tip:** These 9 strings cover product management and customer success roles. Adapt the titles to match your target roles. Keep exact phrases in quotes — this is the most important factor in alert quality.

---

## Personalizing Fit Scoring

The fit scorer uses your profile from `config.json` to rank how well each posting matches you. Edit the `user_profile` block:

```json
"user_profile": {
  "titles": [
    "Senior Product Manager",
    "Product Manager",
    "Customer Success Manager"
  ],
  "years_experience": 7,
  "preferred_domains": ["saas", "api", "platform", "proptech"]
}
```

| Field | Effect |
|---|---|
| `titles` | Job titles in order of preference. The scorer checks if the posting title contains any of these (most → least senior). |
| `years_experience` | Your total years of relevant experience. Used to score experience-level fit. |
| `preferred_domains` | Industry keywords you prefer. Common values: `saas`, `api`, `platform`, `proptech`, `fintech`, `edtech`, `healthtech`. |

Postings scoring **8 or higher** are automatically marked with a ⭐ gold badge.

---

## Customizing Job Filters

The `job_filters` block in `config.json` controls what gets filtered out before reaching your board:

```json
"job_filters": {
  "require_us_only": true,
  "allow_remote": true,
  "onsite_regions": ["San Francisco", "Bay Area", "New York", "Seattle"]
}
```

| Field | Effect |
|---|---|
| `require_us_only` | When `true`, drops postings that mention non-US cities/regions. |
| `allow_remote` | When `true`, remote postings always pass regardless of location. |
| `onsite_regions` | Regions you're willing to commute to for onsite/hybrid roles. Leave as `[]` to allow all locations. |

The app also automatically filters out:
- Cybersecurity-focused roles (unless you want them — edit `SECURITY_TITLE_TERMS` in `modules/keyword_engine.py`)
- Roles requiring a specific degree (e.g., "Bachelor's required")
- Roles where the posting text skews far outside your experience bracket
- URLs with editorial path patterns (`/news/`, `/blog/`, `/article/`, etc.)
- User profile pages (paths starting with `/@`)

### Blocking specific domains

Add domains to `blocked_domains` in `config.json` to permanently exclude them without touching code:

```json
"blocked_domains": [
  "managedservicesjournal.com",
  "techcrunch.com"
]
```

Any URL whose hostname contains a listed domain is dropped at the feed parsing stage before any further processing.

### ATS platforms and LinkedIn

The `ats_domains` block maps URL fragments to platform names shown in the UI. The app automatically detects which platform a posting comes from and adjusts its behavior accordingly:

```json
"ats_domains": {
  "boards.greenhouse.io": "Greenhouse",
  "jobs.ashbyhq.com": "Ashby",
  "jobs.lever.co": "Lever",
  "myworkdayjobs.com": "Workday",
  "icims.com": "iCIMS",
  "linkedin.com/jobs": "LinkedIn",
  "indeed.com": "Indeed",
  "ziprecruiter.com": "ZipRecruiter"
}
```

**LinkedIn behavior:** Because LinkedIn requires a login to view full job content, LinkedIn postings are stored without ATS or Fit scores. They appear on your board with a blue **LinkedIn** badge. Expanding the posting shows the message: *"LinkedIn requires you to be logged in. Please navigate directly to LinkedIn."* The URL in the right panel opens the listing directly in your browser.

**Indeed and ZipRecruiter:** These are scraped normally. The app attempts to find a direct ATS link embedded in the page — if found, the URL is upgraded to the original posting and scored in full. If not, the Indeed/ZipRecruiter URL is kept and scored on whatever text was available.

---

## Customizing Quick Search Buttons

The left sidebar has Quick Search buttons that open Google Jobs in your browser. Edit the `QUICK_SEARCHES` array at the top of `static/app.js`:

```javascript
const QUICK_SEARCHES = [
  {
    label: "Senior Product Manager",
    url: "https://www.google.com/search?q=%22senior+product+manager%22+remote&ibp=htl;jobs"
  },
  {
    label: "Customer Success Manager",
    url: "https://www.google.com/search?q=%22customer+success+manager%22+remote&ibp=htl;jobs"
  },
];
```

**URL template:**
```
https://www.google.com/search?q=YOUR+SEARCH+TERMS+HERE&ibp=htl;jobs
```

Replace spaces in your search string with `+`. Use `%22` for quotes. The `ibp=htl;jobs` suffix activates Google's job listing interface.

> **Note:** Google's job interface does not support negative operators like `-intern`. Keep queries simple.

---

## Launching

**macOS — double-click:**
Open **Job Radar.app** from your Desktop (created by `install.sh`).

**macOS / Linux — Terminal:**
```bash
./launch.command
```

**Windows — double-click:**
Open the **Job Radar** shortcut on your Desktop (created by `install.bat`), or double-click `launch.bat` inside the job-radar folder.

The app starts a local server and opens `http://127.0.0.1:5000` in your browser automatically. To stop it, close the terminal/command window or press `Ctrl+C`.

The current version number is shown in the bottom-left corner of the app.

---

## Updating

> **Your personal data is always preserved.** The update scripts never overwrite `config.json` (your settings) or `jobs.json` (your tracked jobs).

### If you installed with Git (cloned the repo)

**macOS / Linux:**
```bash
./update.sh
```

**Windows:** Double-click `update.bat`

The script will back up your personal files, pull the latest code, restore your files, and update any new dependencies automatically. No re-install needed.

### If you downloaded a ZIP

1. Download the latest ZIP from the GitHub releases page
2. Extract it to a new folder
3. Copy these two files from your old folder into the new one:
   - `config.json` — your Google Alert URLs, resume path, and all settings
   - `jobs.json` — your tracked jobs and notes (if it exists)
4. Run `install.sh` (macOS/Linux) or `install.bat` (Windows) once in the new folder

That's it — your job data and settings carry over completely.

### Checking your current version

The version number is displayed in the bottom-left corner of the app while it's running. You can also check it at any time by opening `VERSION` in a text editor.

---

## Troubleshooting

**"No module named flask" or similar error on launch**
Run the setup script again: `./install.sh` (macOS/Linux) or double-click `install.bat` (Windows).

**Windows: "python is not recognized as an internal or external command"**
Python was installed without being added to PATH. Uninstall Python, re-run the installer, and check the **"Add Python to PATH"** box on the first screen.

**Windows: Script blocked by security warning**
Right-click `install.bat` or `launch.bat` → **Run as administrator**, or right-click → **Properties** → check **Unblock** → OK.

**Feeds returning 0 results**
Go to `http://127.0.0.1:5000/api/debug-feeds` to see a per-feed diagnostic report with HTTP status, entry count, and a sample title for each feed.

**ATS score is always 0**
Check that `resume_path` in `config.json` points to a valid `.docx` file. Set `resume_keywords` to `[]` in `config.json` to force re-extraction on next launch.

**Port already in use**
Change `"port"` under `"app"` in `config.json` to any unused port (e.g., `5001`).

**macOS: App won't open (Gatekeeper warning)**
Right-click → **Open** → **Open** to bypass the first-time security prompt. This is expected for apps that aren't code-signed.

---

## Credits

Created by **Cory Harrah** with AI assistance.

Built with: Python · Flask · feedparser · BeautifulSoup · vanilla JavaScript
