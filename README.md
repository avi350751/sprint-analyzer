# Sprint Tracker

An intelligent JIRA sprint analysis tool that fetches sprint data, detects blockers, and generates AI-powered weekly sprint reports using LangGraph and OpenAI.

## Overview

Sprint Tracker automates sprint reporting by:
- Fetching sprint issues from JIRA (stories, defects, tasks, etc.)
- Analyzing item status and detecting blockers
- Tracking sprint history to identify stuck items
- Generating comprehensive AI-powered sprint reports
- Providing a clean web dashboard for easy access

## Features

✅ **JIRA Integration** - Fetches active sprint items via JIRA REST API v3  
✅ **Blocker Detection** - Automatically identifies blocked and at-risk items  
✅ **Historical Tracking** - Maintains memory of previous sprints to detect stuck items  
✅ **AI-Powered Reports** - Uses OpenAI's GPT to generate intelligent sprint summaries  
✅ **Risk Flagging** - Automatically flags items as HIGH/MEDIUM risk based on blocker history  
✅ **Web Dashboard** - Clean, simple UI to fetch and view sprint reports  
✅ **Auto-Organization Detection** - Extracts organization from JIRA URL automatically  
✅ **LangGraph Workflow** - Multi-step state machine for reliable sprint analysis  

## Architecture

The system uses a **LangGraph StateGraph** with 5 processing nodes:

```
fetch_items → normalize_items → detect_blockers → generate_report → save_snapshot
```

### Data Flow

1. **fetch_items** - Connects to JIRA API and retrieves sprint issues using JQL
2. **normalize_items** - Standardizes item data structure and metadata
3. **detect_blockers** - Identifies blocked items and compares with historical memory
4. **generate_report** - Uses ChatOpenAI to generate intelligent sprint analysis
5. **save_snapshot** - Stores sprint data in memory.json for historical tracking

### Components

- **Backend**: Flask Python web server (app.py)
- **Core Logic**: LangGraph workflow orchestration (sprint_agent.py)
- **Frontend**: Vanilla HTML/CSS/JavaScript dashboard
- **LLM**: OpenAI ChatGPT for report generation
- **Storage**: JSON-based memory system for sprint history

## Prerequisites

- Python 3.12+
- JIRA Cloud account with API token
- OpenAI API key
- UV package manager (or pip)

## Setup

### 1. Clone and Install Dependencies

```bash
# Using UV (recommended)
uv sync

# Or using pip
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```env
# JIRA Configuration
JIRA_BASE_URL=https://your-org.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-api-token-here

# OpenAI Configuration
OPENAI_MODEL=gpt-4

# Sprint Configuration (optional for CLI)
ORG=your-org-name
SPRINT=PSS1
```

### 3. Get JIRA API Token

1. Visit [Atlassian API Tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Create a new API token
3. Copy the token to `.env` as `JIRA_API_TOKEN`

## Usage

### Option 1: Web Dashboard (Recommended)

```bash
# Start the Flask server
uv run -m flask --app app run
```

Then open `http://localhost:5000` in your browser.

**Usage:**
1. The organization is auto-populated from your JIRA URL
2. Enter a Sprint ID (e.g., `PSS1`)
3. Click "Fetch" to generate the report
4. View:
   - Total Items & Blockers count
   - List of blocked items
   - Executive Summary (bulleted points)
   - Observations & Trends
   - Status Overview (Done/In Progress/At Risk)

### Option 2: Command Line

```bash
# Run the sprint analysis directly
uv run sprint_agent.py
```

This will:
1. Fetch items from the sprint specified in `.env`
2. Generate a report
3. Save the snapshot to `sprint_memory.json`

### Option 3: Python Script

```python
from sprint_agent import run_weekly_report

report = run_weekly_report(org="your-org", sprint_id="PSS1")
print(report)
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `JIRA_BASE_URL` | Yes | Your JIRA instance URL (e.g., `https://org.atlassian.net`) |
| `JIRA_EMAIL` | Yes | Email associated with JIRA account |
| `JIRA_API_TOKEN` | Yes | API token from Atlassian API Tokens page |
| `OPENAI_MODEL` | Yes | OpenAI model name (e.g., `gpt-4`, `gpt-4-turbo`) |
| `ORG` | Optional | Organization name (for CLI) |
| `SPRINT` | Optional | Sprint ID (for CLI) |

## Report Output

The generated report includes:

```json
{
  "executive_summary": [
    "Sprint is on track",
    "3 blockers identified",
    "2 items at risk"
  ],
  "status": {
    "done": "5 items completed",
    "in_progress": "8 items in progress",
    "at_risk": "2 items blocked"
  },
  "blockers": "Description of current blockers...",
  "trends": "Week-over-week trends...",
  "observations": "Risk flags and recommendations..."
}
```

## Data Storage

Sprint data is stored in `sprint_memory.json` with the following structure:

```json
{
  "org-name": {
    "weeks": [
      {
        "date": "2026-06-20",
        "sprint_id": "PSS1",
        "open_items": [...],
        "blockers": [...],
        "report": "..."
      }
    ]
  }
}
```

The system keeps the last 12 weeks of sprint history for trend analysis.

## Dependencies

- **langgraph** - Multi-step workflow orchestration
- **langchain-openai** - OpenAI LLM integration
- **requests** - JIRA API communication
- **flask** - Web server
- **python-dotenv** - Environment variable management
- **pydantic** - Data validation

## JIRA Query Details

The tool uses the following JQL (JIRA Query Language) to fetch sprint items:

```
sprint = "{sprint_id}" AND status NOT IN (Done, Closed, Completed)
```

This fetches all items in the sprint that haven't been completed, including:
- Stories
- Defects
- Tasks
- Subtasks
- Any custom issue types

## Troubleshooting

### "JIRA API Error 401"
- Verify `JIRA_EMAIL` and `JIRA_API_TOKEN` are correct
- Check that the API token hasn't expired

### "Unbounded JQL queries are not allowed"
- This error is automatically handled; ensure you're using a valid Sprint ID

### "Report shows as JSON string"
- The HTML frontend automatically parses JSON strings and formats them
- Check browser console for any JavaScript errors

### Organization not detected
- Ensure `JIRA_BASE_URL` is set correctly in `.env`
- Format should be: `https://org-name.atlassian.net`

## Development

### Running Tests

```bash
# Run sprint analysis with debug output
uv run sprint_agent.py
```

### Modifying the Workflow

Edit [sprint_agent.py](sprint_agent.py) to customize:
- Item normalization logic
- Blocker detection rules
- Report generation prompt
- Memory storage behavior

### Customizing the UI

Edit [templates/index.html](templates/index.html) to modify:
- Dashboard layout and styling
- Report section formatting
- Input fields and validation

## Project Structure

```
sprint-tracker/
├── main.py                 # Entry point (placeholder)
├── app.py                  # Flask web server
├── sprint_agent.py         # LangGraph workflow & JIRA integration
├── templates/
│   └── index.html         # Web dashboard
├── sprint_memory.json     # Sprint history storage
├── pyproject.toml         # Project dependencies
├── requirements.txt       # pip dependencies
└── .env                   # Environment variables (not in git)
```

## How It Works

### 1. Item Fetching
Connects to JIRA using REST API v3 with Basic Auth and fetches all non-completed sprint items.

### 2. Normalization
Standardizes item data including owner, status, priority, and blocker information.

### 3. Blocker Detection
- Checks for JIRA issue links ("is blocked by")
- Compares current items against historical memory
- Flags items stuck for multiple sprints as HIGH risk
- New blockers marked as MEDIUM risk

### 4. AI Report Generation
Uses OpenAI's GPT model with a detailed prompt to generate:
- Executive summary (key points)
- Status breakdown (Done/In Progress/At Risk)
- Blocker analysis
- Trend analysis
- Risk assessment
- Recommended actions

### 5. Memory Management
Stores sprint snapshots in JSON for:
- Historical trend analysis
- Detecting stuck items
- Building context for future reports

## License

Private project

