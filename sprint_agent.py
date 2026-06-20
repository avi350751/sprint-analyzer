# sprint_agent.py
from typing import TypedDict, List, Dict, Any
from datetime import date
import json, os
import requests
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
load_dotenv()

llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL"), temperature=0)

class State(TypedDict):
    org: str
    sprint_id: str
    raw_items: List[Dict[str, Any]]
    items: List[Dict[str, Any]]
    blockers: List[Dict[str, Any]]
    previous: Dict[str, Any]
    report: str
    snapshot: Dict[str, Any]

MEMORY_FILE = "sprint_memory.json"

def load_memory(org: str):
    if not os.path.exists(MEMORY_FILE):
        return {}
    return json.load(open(MEMORY_FILE)).get(org, {})

def save_memory(org: str, snapshot: dict):
    data = json.load(open(MEMORY_FILE)) if os.path.exists(MEMORY_FILE) else {}
    data.setdefault(org, {"weeks": []})
    data[org]["weeks"].append(snapshot)
    data[org]["weeks"] = data[org]["weeks"][-12:]
    json.dump(data, open(MEMORY_FILE, "w"), indent=2)

def detect_blocker_from_links(issuelinks: List[Dict[str, Any]], status_name: str):
    """Determine if an issue is blocked from its JIRA issue links or status.

    An issue is considered blocked when it has an inward "is blocked by" link
    pointing to an issue that is not yet resolved, or when its status mentions
    "blocked". Returns (blocked: bool, blocker_reason: str | None).
    """
    reasons = []

    for link in issuelinks or []:
        link_type = (link.get("type") or {}).get("inward", "").lower()
        inward_issue = link.get("inwardIssue")
        # "is blocked by" is the inward side of the standard "Blocks" link type.
        if inward_issue and "blocked by" in link_type:
            blocker_fields = inward_issue.get("fields", {})
            blocker_status = blocker_fields.get("status", {}).get("name", "")
            # Only count it as a live blocker if the blocking issue isn't done.
            if blocker_status.lower() not in ["done", "closed", "completed", "resolved"]:
                key = inward_issue.get("key", "unknown")
                summary = blocker_fields.get("summary", "")
                reasons.append(f"Blocked by {key} ({blocker_status}): {summary}".strip())

    if "blocked" in str(status_name).lower():
        reasons.append(f"Status is '{status_name}'")

    if reasons:
        return True, "; ".join(reasons)
    return False, None


def fetch_jira_items(sprint_id: str):
    """Fetch sprint issues from JIRA via the /rest/api/3/search/jql endpoint."""
    jira_url = os.getenv("JIRA_BASE_URL")
    jira_email = os.getenv("JIRA_EMAIL")
    jira_api_token = os.getenv("JIRA_API_TOKEN")

    if not all([jira_url, jira_email, jira_api_token]):
        raise ValueError("Missing JIRA credentials (JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN)")

    # JQL: all issues in the sprint that aren't finished yet.
    jql = f'sprint = "{sprint_id}" AND status NOT IN (Done, Closed, Completed)'

    url = f"{jira_url.rstrip('/')}/rest/api/3/search/jql"
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    auth = (jira_email, jira_api_token)
    params = {
        "jql": jql,
        "maxResults": 100,
        "fields": "key,summary,status,assignee,priority,issuetype,updated,issuelinks",
    }

    items = []
    next_page_token = None

    try:
        while True:
            if next_page_token:
                params["nextPageToken"] = next_page_token

            response = requests.get(url, params=params, headers=headers, auth=auth)
            if response.status_code != 200:
                print(f"JIRA API Error {response.status_code}: {response.text}")
            response.raise_for_status()

            data = response.json()
            for issue in data.get("issues", []):
                fields = issue.get("fields", {})
                assignee = fields.get("assignee")
                status_name = fields.get("status", {}).get("name", "Unknown")
                blocked, blocker_reason = detect_blocker_from_links(
                    fields.get("issuelinks", []), status_name
                )
                items.append({
                    "id": issue.get("key"),
                    "source": "jira",
                    "title": fields.get("summary", ""),
                    "owner": assignee.get("displayName") if assignee else "Unassigned",
                    "status": status_name,
                    "priority": (fields.get("priority") or {}).get("name", "Medium"),
                    "issue_type": fields.get("issuetype", {}).get("name", ""),
                    "blocked": blocked,
                    "blocker_reason": blocker_reason,
                    "updated_at": fields.get("updated", ""),
                })

            next_page_token = data.get("nextPageToken")
            if data.get("isLast", True) or not next_page_token:
                break

        return items

    except requests.exceptions.RequestException as e:
        print(f"Error fetching JIRA items: {e}")
        return []


def fetch_items(state: State):
    raw = (
        fetch_jira_items(state["sprint_id"])

    )
    return {"raw_items": raw}

def normalize_items(state: State):
    items = []
    for x in state["raw_items"]:
        items.append({
            "id": x.get("id"),
            "source": x.get("source"),
            "title": x.get("title"),
            "owner": x.get("owner"),
            "status": x.get("status"),
            "priority": x.get("priority"),
            "blocked": x.get("blocked", False),
            "blocker_reason": x.get("blocker_reason"),
            "updated_at": x.get("updated_at"),
            "sprint": state["sprint_id"],
        })
    return {"items": items}

def detect_blockers(state: State):
    blocked = [
        i for i in state["items"]
        if i["blocked"]
        or "blocked" in str(i.get("status", "")).lower()
        or i.get("blocker_reason")
    ]

    previous = load_memory(state["org"])
    stuck_ids = set()
    for week in previous.get("weeks", []):
        for item in week.get("open_items", []):
            if item["id"] in [i["id"] for i in state["items"]]:
                if item["status"] == next(i["status"] for i in state["items"] if i["id"] == item["id"]):
                    stuck_ids.add(item["id"])

    blockers = []
    for i in blocked:
        i["risk_flag"] = "HIGH" if i["id"] in stuck_ids else "MEDIUM"
        i["trend"] = "stuck_more_than_one_sprint" if i["id"] in stuck_ids else "new_or_current_blocker"
        blockers.append(i)

    return {"blockers": blockers, "previous": previous}

def generate_report(state: State):
    prompt = f"""
Create a concise weekly sprint status report.

Sprint: {state['sprint_id']}

Items:
{json.dumps(state['items'], indent=2)}

Blockers and risks:
{json.dumps(state['blockers'], indent=2)}

Previous memory:
{json.dumps(state['previous'], indent=2)}

Include:
1. Executive summary
2. Done / in progress / at risk
3. Blockers
4. Week-over-week trend
5. Risk flags
6. Recommended actions
"""
    report = llm.invoke(prompt).content
    return {"report": report}

def save_snapshot(state: State):
    snapshot = {
        "date": str(date.today()),
        "sprint_id": state["sprint_id"],
        "open_items": [
            i for i in state["items"]
            if str(i.get("status", "")).lower() not in ["done", "closed", "complete"]
        ],
        "blockers": state["blockers"],
        "report": state["report"],
    }
    save_memory(state["org"], snapshot)
    return {"snapshot": snapshot}

graph = StateGraph(State)
graph.add_node("fetch_items", fetch_items)
graph.add_node("normalize_items", normalize_items)
graph.add_node("detect_blockers", detect_blockers)
graph.add_node("generate_report", generate_report)
graph.add_node("save_snapshot", save_snapshot)

graph.set_entry_point("fetch_items")
graph.add_edge("fetch_items", "normalize_items")
graph.add_edge("normalize_items", "detect_blockers")
graph.add_edge("detect_blockers", "generate_report")
graph.add_edge("generate_report", "save_snapshot")
graph.add_edge("save_snapshot", END)

app = graph.compile(checkpointer=MemorySaver())

def run_weekly_report(org: str, sprint_id: str):
    result = app.invoke(
        {
            "org": org,
            "sprint_id": sprint_id,
            "raw_items": [],
            "items": [],
            "blockers": [],
            "previous": {},
            "report": "",
            "snapshot": {},
        },
        config={"configurable": {"thread_id": f"{org}:{sprint_id}"}},
    )
    return result["report"]

if __name__ == "__main__":
    print(run_weekly_report(os.getenv("ORG"), os.getenv("SPRINT")))