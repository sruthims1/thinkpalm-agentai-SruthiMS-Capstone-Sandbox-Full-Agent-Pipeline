"""
JIRA Cloud integration service.
Fetches issue details (summary, description, acceptance criteria) via JIRA REST API v3
and converts Atlassian Document Format (ADF) to plain text for pipeline ingestion.

Required env vars: JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN
"""

from __future__ import annotations
import os, logging
import requests
from requests.auth import HTTPBasicAuth

log = logging.getLogger(__name__)

# Common custom field IDs for acceptance criteria across JIRA Cloud instances
_AC_FIELDS = [
    "customfield_10016",  # Acceptance Criteria (most common)
    "customfield_10014",  # Story Points alt / AC on some configs
    "customfield_10028",  # Used by some Atlassian templates
]


class JiraService:
    """Fetches JIRA Cloud issues and converts them to pipeline-ready text."""

    def __init__(self) -> None:
        self.url   = os.getenv("JIRA_URL", "").rstrip("/")
        self.email = os.getenv("JIRA_EMAIL", "")
        self.token = os.getenv("JIRA_API_TOKEN", "")

    def _check_config(self) -> None:
        missing = [k for k, v in {
            "JIRA_URL": self.url,
            "JIRA_EMAIL": self.email,
            "JIRA_API_TOKEN": self.token,
        }.items() if not v]
        if missing:
            raise ValueError(f"Missing JIRA config in .env: {', '.join(missing)}")

    @property
    def _auth(self) -> HTTPBasicAuth:
        return HTTPBasicAuth(self.email, self.token)

    def fetch_issue(self, issue_key: str) -> dict:
        """
        Fetch a JIRA Cloud issue and return a dict ready for the pipeline.

        Returns:
            issue_key, summary, description, acceptance_criteria,
            priority, labels, issue_type, status, url,
            feature_name (= summary),
            feature_description (= merged text for pipeline input)
        """
        self._check_config()

        resp = requests.get(
            f"{self.url}/rest/api/3/issue/{issue_key}",
            auth=self._auth,
            headers={"Accept": "application/json"},
            timeout=15,
        )
        resp.raise_for_status()
        data   = resp.json()
        fields = data.get("fields", {})

        summary     = fields.get("summary", issue_key)
        desc_adf    = fields.get("description")
        description = self._adf_to_text(desc_adf) if isinstance(desc_adf, dict) else (desc_adf or "")

        # Try common acceptance criteria custom fields
        ac = ""
        for cf in _AC_FIELDS:
            val = fields.get(cf)
            if not val:
                continue
            if isinstance(val, str):
                ac = val.strip()
            elif isinstance(val, dict):
                ac = self._adf_to_text(val).strip()
            if ac:
                break

        priority   = (fields.get("priority")   or {}).get("name", "Medium")
        labels     = fields.get("labels", [])
        issue_type = (fields.get("issuetype")  or {}).get("name", "Story")
        status     = (fields.get("status")     or {}).get("name", "")
        assignee   = ((fields.get("assignee")  or {}).get("displayName") or "Unassigned")

        # Build the feature description that gets fed into the pipeline
        feature_description = summary
        if description:
            feature_description += f"\n\n{description}"
        if ac:
            feature_description += f"\n\nAcceptance Criteria:\n{ac}"

        log.info(f"[JiraService] Fetched {issue_key} — '{summary}' ({issue_type}, {priority})")

        return {
            "issue_key":           issue_key,
            "summary":             summary,
            "description":         description,
            "acceptance_criteria": ac,
            "priority":            priority,
            "labels":              labels,
            "issue_type":          issue_type,
            "status":              status,
            "assignee":            assignee,
            "url":                 f"{self.url}/browse/{issue_key}",
            "feature_name":        summary,
            "feature_description": feature_description,
        }

    # ── Atlassian Document Format → plain text ──────────────────────────────────

    @classmethod
    def _adf_to_text(cls, node: dict | None, _depth: int = 0) -> str:
        """Recursively convert an ADF node tree to readable plain text."""
        if not node or not isinstance(node, dict):
            return ""

        ntype   = node.get("type", "")
        content = node.get("content", [])
        text    = node.get("text", "")

        if ntype == "text":
            return text

        if ntype in ("doc", "blockquote"):
            parts = [cls._adf_to_text(c, _depth) for c in content]
            return "\n\n".join(p for p in parts if p.strip())

        if ntype == "paragraph":
            parts = [cls._adf_to_text(c, _depth) for c in content]
            return "".join(parts)

        if ntype == "heading":
            level = node.get("attrs", {}).get("level", 2)
            parts = [cls._adf_to_text(c, _depth) for c in content]
            return "#" * level + " " + "".join(parts)

        if ntype == "bulletList":
            items = []
            for item in content:
                item_text = "\n".join(
                    cls._adf_to_text(c, _depth + 1)
                    for c in item.get("content", [])
                    if cls._adf_to_text(c, _depth + 1).strip()
                )
                items.append("- " + item_text.replace("\n", "\n  "))
            return "\n".join(items)

        if ntype == "orderedList":
            items = []
            for i, item in enumerate(content, 1):
                item_text = "\n".join(
                    cls._adf_to_text(c, _depth + 1)
                    for c in item.get("content", [])
                    if cls._adf_to_text(c, _depth + 1).strip()
                )
                items.append(f"{i}. " + item_text.replace("\n", "\n   "))
            return "\n".join(items)

        if ntype == "listItem":
            parts = [cls._adf_to_text(c, _depth) for c in content]
            return "\n".join(p for p in parts if p.strip())

        if ntype == "codeBlock":
            parts = [cls._adf_to_text(c, _depth) for c in content]
            lang  = node.get("attrs", {}).get("language", "")
            return f"```{lang}\n" + "".join(parts) + "\n```"

        if ntype == "inlineCard":
            return node.get("attrs", {}).get("url", "")

        if ntype == "hardBreak":
            return "\n"

        if ntype == "rule":
            return "---"

        if ntype == "mention":
            return "@" + node.get("attrs", {}).get("text", "user")

        if ntype == "emoji":
            return node.get("attrs", {}).get("text", "")

        if ntype == "table":
            rows = []
            for row in content:
                cells = [
                    cls._adf_to_text(c, _depth).strip()
                    for c in row.get("content", [])
                ]
                rows.append(" | ".join(cells))
            return "\n".join(rows)

        # Fallback: recurse into children
        if content:
            parts = [cls._adf_to_text(c, _depth) for c in content]
            return "\n".join(p for p in parts if p.strip())

        return text
