"""Deterministic mock agent — behaves like a tool-using system orchestrator.

Enforces the same rules as SYSTEM_PROMPT in prompts.py:
- entity-first extraction
- fetch_logs is priority 1, query_db priority 2, retrieve_context priority 3
- RAG is a fallback, not a default
- explicit "insufficient data" messaging when no signal is found

Response shape (identical to GeminiAgentExecutor):
    {answer, reasoning, sources, trace, suggested_action, executed}
(plus `metrics` injected by _TimedAgent in agent.py)
"""

import re
from typing import Any, Optional

from app.agent._format import db_sources, logs_source, rag_source, trace_entry

_USER_ID_RE = re.compile(r"\bU\d{3,}\b", re.IGNORECASE)
_JOB_ID_RE = re.compile(r"\bJ\d{3,}\b", re.IGNORECASE)
_ROLES = ("admin", "manager", "engineer", "support", "auditor", "intern",
          "devops", "security_admin", "analyst", "viewer")

# Keyword groups used by the classifier + service detector.
_NOTIFICATION_KWS = (
    "update", "updates", "notification", "notifications",
    "receiving", "receive", "email", "alert", "digest",
)
_AUTH_KWS = ("login", "log in", "sign in", "signin", "auth", "session", "sso")
_ETL_KWS = ("etl", "pipeline", "sync", "backup")
_REPORT_KWS = ("report", "dashboard", "slow query", "query plan")
_SECURITY_KWS = ("scan", "anomaly", "intrusion", "security")
_BILLING_KWS = ("invoice", "billing", "payment", "charge")

_USER_KWS = ("user", "access", "role", "suspended", "unsuspend", "login",
             "lose access", "lost access", "denied", "locked out",
             "update", "updates", "notification", "notifications",
             "receiving", "receive", "email", "alert")
_JOB_KWS = ("job", "etl", "pipeline", "batch", "backup", "sync",
            "failed", "fail", "failure")
_ACTION_KWS = ("restart", "retry", "reassign", "reset password", "unsuspend")
_DOC_KWS = ("permission", "policy", "access control", "runbook",
            "how do i", "how does")


def _has_any(q: str, kws: tuple[str, ...]) -> bool:
    return any(kw in q for kw in kws)


def _extract_user_id(query: str) -> Optional[str]:
    m = _USER_ID_RE.search(query)
    return m.group(0).upper() if m else None


def _extract_job_id(query: str) -> Optional[str]:
    m = _JOB_ID_RE.search(query)
    return m.group(0).upper() if m else None


def _extract_role(query: str) -> Optional[str]:
    q = query.lower()
    for r in _ROLES:
        if re.search(rf"\b{r}\b", q):
            return r
    return None


def _detect_service(query: str) -> Optional[str]:
    """Infer which service is implicated from the query text."""
    q = query.lower()
    if _has_any(q, _NOTIFICATION_KWS):
        return "notification-service"
    if _has_any(q, _AUTH_KWS):
        return "auth-service"
    if _has_any(q, _ETL_KWS):
        return "etl-pipeline"
    if _has_any(q, _REPORT_KWS):
        return "reporting-api"
    if _has_any(q, _SECURITY_KWS):
        return "security-scanner"
    if _has_any(q, _BILLING_KWS):
        return "billing-service"
    return None


def _count(obs: Any) -> int:
    return len(obs) if isinstance(obs, list) else 0


def _pretty_action(action: Optional[dict]) -> str:
    if not action:
        return "none"
    name = action.get("action", "unknown")
    params = action.get("params") or {}
    if not params:
        return name
    pairs = ", ".join(f"{k}={v}" for k, v in params.items())
    return f"{name}({pairs})"


def _error_and_warn_logs(logs: Any) -> tuple[list, list]:
    if not isinstance(logs, list):
        return [], []
    errors = [l for l in logs if isinstance(l, dict) and l.get("severity") == "ERROR"]
    warns = [l for l in logs if isinstance(l, dict) and l.get("severity") == "WARN"]
    return errors, warns


class MockAgentExecutor:
    def __init__(self, tools: list) -> None:
        self.tools = {tool.name: tool for tool in tools}

    # ---------- public ----------

    def invoke(self, inputs: dict) -> dict:
        query = inputs["query"]
        intent = self._classify(query)
        return self._route(intent, query)

    # ---------- classification ----------

    def _classify(self, query: str) -> str:
        """Entity-first, then keyword routing.

        Priority order:
          1. action  — explicit mutation verbs
          2. user_issue — has user_id (anchors the query on that user)
          3. job_issue — has job_id
          4. rag — explicit docs phrasing AND no specific entity
          5. system_issue — a service is detected and no user entity is present
          6. user_issue — user/access keywords with no service (e.g. "list suspended users")
          7. job_issue — job/etl/failed keywords
          8. unknown — fallback
        """
        q = query.lower()
        user_id = _extract_user_id(query)
        job_id = _extract_job_id(query)

        # 1. Action verbs always win.
        if _has_any(q, _ACTION_KWS) or ("fix" in q and _has_any(q, _ETL_KWS + ("job",))):
            return "action"

        # 2. Entity-first: a user id anchors the query on that user.
        if user_id:
            return "user_issue"

        # 3. Job id anchors on that job.
        if job_id:
            return "job_issue"

        # 4. Pure documentation / policy questions.
        if _has_any(q, _DOC_KWS):
            return "rag"

        # 5. Job keywords (etl/pipeline/failed/etc.) — route to job_issue BEFORE
        #    service detection so "ETL fail" doesn't get downgraded to system_issue.
        if _has_any(q, _JOB_KWS):
            return "job_issue"

        # 6. A service is implicated with no user/job id → system issue.
        if _detect_service(query):
            return "system_issue"

        # 7. User keywords with no service and no entity (e.g. "suspended users").
        if _has_any(q, _USER_KWS):
            return "user_issue"

        return "unknown"

    def _route(self, intent: str, query: str) -> dict:
        handlers = {
            "user_issue": self._handle_user_issue,
            "job_issue": self._handle_job_issue,
            "rag": self._handle_rag,
            "action": self._handle_action,
            "system_issue": self._handle_system_issue,
        }
        return handlers.get(intent, self._handle_unknown)(query)

    # ---------- tool invocation + trace ----------

    def _call(self, trace: list, name: str, args: dict) -> Any:
        result = self.tools[name].invoke(args)
        trace.append(trace_entry(name, args, result))
        return result

    # ---------- handlers ----------

    def _handle_user_issue(self, query: str) -> dict:
        trace: list[dict] = []
        user_id = _extract_user_id(query)
        service_hint = _detect_service(query)

        # Priority 1: fetch_logs FIRST.
        logs_args = (
            {"user_id": user_id, "limit": 10}
            if user_id
            else {"service": "auth-service", "severity": "ERROR", "limit": 10}
        )
        logs = self._call(trace, "fetch_logs", logs_args)

        # Priority 2: query_db for user state.
        user_args = (
            {"table": "users", "filters": {"id": user_id}, "limit": 1}
            if user_id
            else {"table": "users", "filters": {"status": "suspended"}, "limit": 10}
        )
        users = self._call(trace, "query_db", user_args)

        # Extended signal: if a service is implicated, also grab service logs.
        service_logs: list = []
        service_logs_args: Optional[dict] = None
        if service_hint:
            service_logs_args = {"service": service_hint, "limit": 10}
            service_logs = self._call(trace, "fetch_logs", service_logs_args)

        # --- Signal assessment ---
        user_row = users[0] if isinstance(users, list) and users else None
        user_errors, user_warns = _error_and_warn_logs(logs)
        svc_errors, svc_warns = _error_and_warn_logs(service_logs)

        has_useful_signal = (
            (user_row is not None and user_row.get("status") == "suspended")
            or bool(user_errors)
            or bool(user_warns)
            or bool(svc_errors)
            or bool(svc_warns)
        )

        # Priority 3 (fallback): retrieve_context ONLY if the earlier tools were uninformative.
        rag: list = []
        rag_args: Optional[dict] = None
        if not has_useful_signal:
            rag_args = {"query": query, "k": 3}
            rag = self._call(trace, "retrieve_context", rag_args)

        # --- Answer composition ---
        parts: list[str] = []
        suggested: Optional[dict] = None

        if user_id and user_row:
            parts.append(
                f"User {user_row['id']} ({user_row['name']}) has status='{user_row['status']}' "
                f"and role='{user_row['role']}'."
            )
            if user_row["status"] == "suspended":
                parts.append("Account is currently suspended — this is why access was lost.")
                suggested = {"action": "unsuspend_user", "params": {"user_id": user_id}}
        elif user_id:
            parts.append(f"No user record found for {user_id}.")
        elif user_row:  # list of suspended users
            names = ", ".join(u["name"] for u in users if isinstance(u, dict))
            parts.append(f"Currently suspended users: {names}.")

        if user_warns:
            parts.append(
                f"Audit event: \"{user_warns[0]['message']}\" at {user_warns[0]['timestamp']}."
            )
        if user_errors:
            parts.append(
                f"Recent denial: \"{user_errors[0]['message']}\" at {user_errors[0]['timestamp']}."
            )

        if service_hint and service_logs:
            if svc_errors:
                parts.append(
                    f"{service_hint} recent issue: \"{svc_errors[0]['message']}\" "
                    f"at {svc_errors[0]['timestamp']}."
                )
            elif svc_warns:
                parts.append(
                    f"{service_hint} warning: \"{svc_warns[0]['message']}\" "
                    f"at {svc_warns[0]['timestamp']}."
                )
            else:
                parts.append(f"{service_hint} logs show no recent errors or warnings.")

        # Insufficient-data messaging when nothing in logs or db, and no service signal.
        if not has_useful_signal:
            attempted = "logs, users table"
            if service_hint:
                attempted += f", {service_hint} logs"
            target = user_id or "the query"
            parts.append(
                f"No direct logs or audit events found for {target} after checking {attempted}. "
                f"Insufficient data to diagnose."
            )
            if rag:
                first = rag[0].get("content", "").strip().splitlines() if isinstance(rag[0], dict) else []
                if first:
                    parts.append(f"Closest documentation: {first[0]}")

        answer = " ".join(parts) if parts else "Insufficient data to diagnose."

        # Reasoning (step-numbered, explicit about priority ordering).
        reasoning_lines = [
            "Intent classified as: user_issue.",
            f"Step 1 (priority 1, fetch_logs): {logs_args} -> {_count(logs)} log entries.",
            f"Step 2 (priority 2, query_db): filters={user_args['filters']} -> {_count(users)} row(s).",
        ]
        if service_logs_args:
            reasoning_lines.append(
                f"Step 3 (service hint='{service_hint}'): "
                f"fetch_logs(service='{service_hint}') -> {_count(service_logs)} entries."
            )
        if rag_args:
            reasoning_lines.append(
                f"Step {len(reasoning_lines)} (fallback RAG, logs+db insufficient): "
                f"retrieve_context -> {_count(rag)} docs."
            )
        reasoning_lines.append(
            f"Step {len(reasoning_lines)}: "
            f"{'Composed grounded answer.' if has_useful_signal else 'Returned insufficient-data notice.'}"
        )
        reasoning = "\n".join(reasoning_lines)

        # Sources
        sources: list[str] = [logs_source(logs_args)]
        sources.extend(db_sources("users", user_args["filters"], users))
        if service_logs_args:
            sources.append(logs_source(service_logs_args))
        if rag:
            sources.extend(rag_source(d) for d in rag)
        sources = list(dict.fromkeys(sources))

        return {
            "answer": answer,
            "reasoning": reasoning,
            "sources": sources,
            "trace": trace,
            "suggested_action": suggested,
            "executed": False,
        }

    def _handle_job_issue(self, query: str) -> dict:
        trace: list[dict] = []
        job_id = _extract_job_id(query)
        service_hint = _detect_service(query) or "etl-pipeline"

        # Priority 1: fetch_logs FIRST (system-issue rule).
        logs_args = {"service": service_hint, "severity": "ERROR", "limit": 10}
        logs = self._call(trace, "fetch_logs", logs_args)

        # Priority 2: query_db for job state.
        job_args = (
            {"table": "jobs", "filters": {"job_id": job_id}, "limit": 1}
            if job_id
            else {"table": "jobs", "filters": {"status": "failed"}, "limit": 10}
        )
        jobs = self._call(trace, "query_db", job_args)

        # --- Signal assessment ---
        failed = (
            [j for j in jobs if isinstance(j, dict) and j.get("status") == "failed"]
            if isinstance(jobs, list)
            else []
        )
        log_errors, _ = _error_and_warn_logs(logs)
        has_useful_signal = bool(failed) or bool(log_errors) or (
            isinstance(jobs, list) and bool(jobs)
        )

        # Priority 3 (fallback): retrieve_context for runbook only when we have signal OR when truly empty.
        # For job_issue, the runbook IS useful even when we have signal (to recommend next step),
        # so we fetch it unless the job was a simple success query.
        rag: list = []
        rag_args: Optional[dict] = None
        if failed or log_errors or not has_useful_signal:
            rag_args = {"query": query, "k": 2}
            rag = self._call(trace, "retrieve_context", rag_args)

        # --- Answer ---
        parts: list[str] = []
        suggested: Optional[dict] = None

        if failed:
            desc = ", ".join(f"{j['job_id']} ({j['name']})" for j in failed)
            parts.append(f"Failed jobs: {desc}.")
            first_err = failed[0].get("error_message")
            if first_err:
                parts.append(f"Primary error: \"{first_err}\".")
            err_l = (first_err or "").lower()
            if any(sig in err_l for sig in ("connection", "timeout", "refused", "unreachable")):
                suggested = {"action": "restart_job", "params": {"job_id": failed[0]["job_id"]}}
        elif isinstance(jobs, list) and jobs:
            j = jobs[0]
            parts.append(f"Job {j['job_id']} ({j['name']}): status={j['status']}.")
        else:
            parts.append("No matching jobs found.")

        if log_errors:
            parts.append(
                f"Correlated log: \"{log_errors[0]['message']}\" at {log_errors[0]['timestamp']}."
            )

        if rag and isinstance(rag, list) and rag[0].get("content"):
            runbook = rag[0]["content"].strip().splitlines()
            if runbook:
                parts.append(f"Runbook: {runbook[-1]}")
        if suggested:
            parts.append(f"Recommendation: {_pretty_action(suggested)} (pending operator confirmation).")

        if not has_useful_signal:
            parts.append("No failing jobs or error logs in the recent window. Insufficient data to diagnose.")

        answer = " ".join(parts)

        # Reasoning
        reasoning_lines = [
            "Intent classified as: job_issue.",
            f"Step 1 (priority 1, fetch_logs): {logs_args} -> {_count(logs)} log entries.",
            f"Step 2 (priority 2, query_db): filters={job_args['filters']} -> {_count(jobs)} row(s) "
            f"({len(failed)} failed).",
        ]
        if rag_args:
            reasoning_lines.append(
                f"Step 3 (runbook lookup): retrieve_context(k=2) -> {_count(rag)} docs."
            )
        reasoning_lines.append(f"Step {len(reasoning_lines)}: Combined findings; suggested={_pretty_action(suggested)}.")
        reasoning = "\n".join(reasoning_lines)

        # Sources
        sources: list[str] = [logs_source(logs_args)]
        sources.extend(db_sources("jobs", job_args["filters"], jobs))
        if rag:
            sources.extend(rag_source(d) for d in rag)
        sources = list(dict.fromkeys(sources))

        return {
            "answer": answer,
            "reasoning": reasoning,
            "sources": sources,
            "trace": trace,
            "suggested_action": suggested,
            "executed": False,
        }

    def _handle_rag(self, query: str) -> dict:
        """Pure documentation / policy queries. Only route that calls RAG first —
        matches rule 6: 'Never answer using only RAG unless explicitly asked for
        documentation.'"""
        trace: list[dict] = []
        role = _extract_role(query)

        rag_args = {"query": query, "k": 3}
        context = self._call(trace, "retrieve_context", rag_args)

        users: Optional[list] = None
        user_args: dict = {}
        if role:
            user_args = {"table": "users", "filters": {"role": role}, "limit": 10}
            users = self._call(trace, "query_db", user_args)

        parts = ["Based on policy docs:"]
        if isinstance(context, list) and context:
            for doc in context[:2]:
                content = doc.get("content", "").strip() if isinstance(doc, dict) else ""
                if content:
                    parts.append(f"- {content}")
        else:
            parts.append("- (no matching policy docs found)")
        if isinstance(users, list) and users:
            names = ", ".join(u["name"] for u in users if isinstance(u, dict))
            parts.append(f"Users currently with role={role}: {names}.")

        answer = "\n".join(parts)

        reasoning_lines = [
            "Intent classified as: rag (explicit documentation query).",
            f"Step 1: retrieve_context({rag_args}) -> {_count(context)} docs.",
        ]
        if users is not None:
            reasoning_lines.append(
                f"Step 2: query_db(table='users', filters={user_args['filters']}) "
                f"-> {_count(users)} row(s)."
            )
        reasoning_lines.append(f"Step {len(reasoning_lines) + 1}: Composed answer from RAG snippets + user list.")
        reasoning = "\n".join(reasoning_lines)

        sources: list[str] = []
        if isinstance(context, list):
            sources.extend(rag_source(d) for d in context)
        if users is not None:
            sources.extend(db_sources("users", user_args["filters"], users))
        sources = list(dict.fromkeys(sources))

        return {
            "answer": answer,
            "reasoning": reasoning,
            "sources": sources,
            "trace": trace,
            "suggested_action": None,
            "executed": False,
        }

    def _handle_action(self, query: str) -> dict:
        trace: list[dict] = []
        q = query.lower()
        user_id = _extract_user_id(query)
        job_id = _extract_job_id(query)
        is_job_action = (
            "restart" in q
            or "retry" in q
            or ("fix" in q and any(x in q for x in ("job", "etl", "pipeline")))
        )

        if is_job_action:
            # Logs first (priority 1), then DB to resolve job id.
            logs_args = {"service": "etl-pipeline", "severity": "ERROR", "limit": 10}
            logs = self._call(trace, "fetch_logs", logs_args)

            job_args = (
                {"table": "jobs", "filters": {"job_id": job_id}, "limit": 1}
                if job_id
                else {"table": "jobs", "filters": {"status": "failed"}, "limit": 10}
            )
            jobs = self._call(trace, "query_db", job_args)

            rag_args = {"query": query, "k": 2}
            context = self._call(trace, "retrieve_context", rag_args)

            failed = (
                [j for j in jobs if isinstance(j, dict) and j.get("status") == "failed"]
                if isinstance(jobs, list) else []
            )
            target = failed[0] if failed else (jobs[0] if isinstance(jobs, list) and jobs else None)

            parts: list[str] = []
            suggested: Optional[dict] = None

            if target and target.get("status") == "failed":
                parts.append(f"Job {target['job_id']} ({target['name']}) is failed.")
                if target.get("error_message"):
                    parts.append(f"Error: \"{target['error_message']}\".")
                parts.append("Restart is available via the /action endpoint — pending operator confirmation.")
                suggested = {"action": "restart_job", "params": {"job_id": target["job_id"]}}
            elif target:
                parts.append(
                    f"Job {target['job_id']} ({target['name']}) has status={target['status']} — no restart needed."
                )
            else:
                parts.append("No failed jobs found to restart. Insufficient data.")

            if isinstance(context, list) and context:
                runbook = context[0].get("content", "").strip().splitlines()
                if runbook:
                    parts.append(f"Runbook: {runbook[-1]}")

            answer = " ".join(parts)
            reasoning = (
                f"Intent classified as: action (job-target).\n"
                f"Step 1 (priority 1, fetch_logs): {logs_args} -> {_count(logs)} log entries.\n"
                f"Step 2 (priority 2, query_db): filters={job_args['filters']} -> {_count(jobs)} row(s).\n"
                f"Step 3 (runbook): retrieve_context(k=2) -> {_count(context)} doc(s).\n"
                f"Step 4: target={target['job_id'] if target else 'none'}; "
                f"suggested={_pretty_action(suggested)}. "
                f"Did NOT call trigger_action — execution is /action's responsibility."
            )

            sources = [logs_source(logs_args)] + db_sources("jobs", job_args["filters"], jobs)
            if isinstance(context, list):
                sources.extend(rag_source(d) for d in context)
            sources = list(dict.fromkeys(sources))

            return {
                "answer": answer,
                "reasoning": reasoning,
                "sources": sources,
                "trace": trace,
                "suggested_action": suggested,
                "executed": False,
            }

        # User-targeted actions (reset password / unsuspend / reassign).
        if user_id and ("reset password" in q):
            return self._action_user_simple(query, user_id, "reset_password",
                                            "Password reset for {name} ({uid}) is available via /action.")

        if user_id and "unsuspend" in q:
            return self._action_unsuspend(query, user_id)

        if user_id and "reassign" in q:
            return self._action_reassign(query, user_id)

        # No specific target.
        return {
            "answer": (
                "Action intent detected but no specific target identified. "
                "Include a job_id (e.g., J001) or user_id (e.g., U002) and the desired action "
                "(restart, reset password, unsuspend, reassign). Insufficient data to propose an action."
            ),
            "reasoning": (
                "Intent classified as: action.\n"
                "Step 1: No entity extracted, no handler matched. "
                "Did NOT guess; returned guidance."
            ),
            "sources": [],
            "trace": [],
            "suggested_action": None,
            "executed": False,
        }

    def _action_user_simple(self, query: str, user_id: str, action: str, success_tmpl: str) -> dict:
        trace: list[dict] = []
        user_args = {"table": "users", "filters": {"id": user_id}, "limit": 1}
        users = self._call(trace, "query_db", user_args)
        target = users[0] if isinstance(users, list) and users else None

        if target:
            answer = success_tmpl.format(name=target["name"], uid=user_id)
            suggested = {"action": action, "params": {"user_id": user_id}}
        else:
            answer = f"No user record found for {user_id}. Insufficient data to propose {action}."
            suggested = None

        return {
            "answer": answer,
            "reasoning": (
                f"Intent classified as: action ({action}).\n"
                f"Step 1 (priority 2, query_db): filters={{'id': '{user_id}'}} -> {_count(users)} row(s).\n"
                f"Step 2: Proposed {_pretty_action(suggested)}."
            ),
            "sources": db_sources("users", user_args["filters"], users),
            "trace": trace,
            "suggested_action": suggested,
            "executed": False,
        }

    def _action_unsuspend(self, query: str, user_id: str) -> dict:
        trace: list[dict] = []
        user_args = {"table": "users", "filters": {"id": user_id}, "limit": 1}
        users = self._call(trace, "query_db", user_args)
        target = users[0] if isinstance(users, list) and users else None

        if target and target.get("status") == "suspended":
            answer = (
                f"{target['name']} ({user_id}) is currently suspended. "
                f"Unsuspend is available via /action."
            )
            suggested: Optional[dict] = {"action": "unsuspend_user", "params": {"user_id": user_id}}
        elif target:
            answer = (
                f"{target['name']} ({user_id}) is already {target['status']} — no unsuspend needed."
            )
            suggested = None
        else:
            answer = f"No user record found for {user_id}. Insufficient data to propose unsuspend."
            suggested = None

        return {
            "answer": answer,
            "reasoning": (
                f"Intent classified as: action (unsuspend_user).\n"
                f"Step 1 (priority 2, query_db): filters={{'id': '{user_id}'}} -> {_count(users)} row(s).\n"
                f"Step 2: Proposed {_pretty_action(suggested)}."
            ),
            "sources": db_sources("users", user_args["filters"], users),
            "trace": trace,
            "suggested_action": suggested,
            "executed": False,
        }

    def _action_reassign(self, query: str, user_id: str) -> dict:
        trace: list[dict] = []
        new_role = _extract_role(query)
        user_args = {"table": "users", "filters": {"id": user_id}, "limit": 1}
        users = self._call(trace, "query_db", user_args)
        target = users[0] if isinstance(users, list) and users else None

        if target and new_role:
            answer = (
                f"Proposed: reassign {target['name']} from '{target['role']}' to '{new_role}'. "
                f"Available via /action."
            )
            suggested: Optional[dict] = {
                "action": "reassign_role",
                "params": {"user_id": user_id, "new_role": new_role},
            }
        elif target:
            answer = (
                f"User {user_id} found but no target role specified — include a role "
                f"(e.g., 'reassign U002 to support')."
            )
            suggested = {"action": "reassign_role", "params": {"user_id": user_id}}
        else:
            answer = f"No user record found for {user_id}. Insufficient data to propose reassign_role."
            suggested = None

        return {
            "answer": answer,
            "reasoning": (
                f"Intent classified as: action (reassign_role).\n"
                f"Step 1 (priority 2, query_db): filters={{'id': '{user_id}'}} -> {_count(users)} row(s).\n"
                f"Step 2: new_role={new_role or 'unspecified'}. Proposed {_pretty_action(suggested)}."
            ),
            "sources": db_sources("users", user_args["filters"], users),
            "trace": trace,
            "suggested_action": suggested,
            "executed": False,
        }

    def _handle_system_issue(self, query: str) -> dict:
        """Service-level issue with no specific user/job id — logs-first per rule 3."""
        trace: list[dict] = []
        service = _detect_service(query) or "auth-service"

        logs_args = {"service": service, "limit": 15}
        logs = self._call(trace, "fetch_logs", logs_args)

        errors, warns = _error_and_warn_logs(logs)
        has_useful_signal = bool(errors) or bool(warns)

        rag: list = []
        rag_args: Optional[dict] = None
        if not has_useful_signal:
            rag_args = {"query": query, "k": 3}
            rag = self._call(trace, "retrieve_context", rag_args)

        parts: list[str] = []
        if errors:
            parts.append(f"{service} errors ({len(errors)}): \"{errors[0]['message']}\" at {errors[0]['timestamp']}.")
        if warns:
            parts.append(f"{service} warnings ({len(warns)}): \"{warns[0]['message']}\" at {warns[0]['timestamp']}.")
        if not has_useful_signal:
            parts.append(
                f"No recent errors or warnings found for {service}. Insufficient data to diagnose."
            )
            if rag:
                first = rag[0].get("content", "").strip().splitlines() if isinstance(rag[0], dict) else []
                if first:
                    parts.append(f"Closest runbook: {first[0]}")

        answer = " ".join(parts)

        reasoning_lines = [
            "Intent classified as: system_issue.",
            f"Step 1 (priority 1, fetch_logs): {logs_args} -> {_count(logs)} log entries "
            f"({len(errors)} ERROR, {len(warns)} WARN).",
        ]
        if rag_args:
            reasoning_lines.append(
                f"Step 2 (fallback RAG, logs insufficient): retrieve_context -> {_count(rag)} docs."
            )
        reasoning = "\n".join(reasoning_lines)

        sources = [logs_source(logs_args)]
        if rag:
            sources.extend(rag_source(d) for d in rag)

        return {
            "answer": answer,
            "reasoning": reasoning,
            "sources": sources,
            "trace": trace,
            "suggested_action": None,
            "executed": False,
        }

    def _handle_unknown(self, query: str) -> dict:
        """Last-resort fallback when no entity and no keyword matched."""
        trace: list[dict] = []
        rag_args = {"query": query, "k": 3}
        context = self._call(trace, "retrieve_context", rag_args)

        if isinstance(context, list) and context:
            lines = ["Closest matching docs:"]
            for doc in context[:3]:
                first = (doc.get("content", "") or "").strip().splitlines()
                if first:
                    lines.append(f"- {first[0]}")
            answer = "\n".join(lines)
        else:
            answer = "No relevant information found. Insufficient data to diagnose."

        reasoning = (
            f"Intent classified as: unknown.\n"
            f"Step 1 (fallback RAG, no entity or keyword matched): "
            f"retrieve_context({rag_args}) -> {_count(context)} doc(s)."
        )

        sources: list[str] = []
        if isinstance(context, list):
            sources.extend(rag_source(d) for d in context)

        return {
            "answer": answer,
            "reasoning": reasoning,
            "sources": sources,
            "trace": trace,
            "suggested_action": None,
            "executed": False,
        }
