"""FinalHarness — 개선 대상.

이 파일이 상위권 재현성 검증용 harness.py 제출 산출물이며, 성능 개선은 여기서만 한다.
scpc_core.py(고정 framework)의 채점기·러너·SLM은 건드리지 않는다.

현재 로직은 주최측 baseline 노트북(셀 7)과 동일하다.
"""
from __future__ import annotations

import re
from typing import Any

from scpc_core import (
    FixedSLMClient,
    object_text,
    objects_of,
    record_map,
    records_of,
    text_of,
)


class FinalHarness:
    def __init__(self) -> None:
        self.slm = FixedSLMClient()
        self.memory: dict[str, Any] = {}

    def prepare(self, tasks: list[dict[str, Any]]) -> None:
        self.memory.clear()

    def answer_task(self, task: dict[str, Any], session: dict[str, Any]) -> dict[str, Any]:
        evidence = self.slm.summarize_task(task)
        self.update_session_memory(task, session, evidence)

        focal = self.choose_focal(task, session, evidence)
        focal_id = str(focal.get("id") or "")
        target = self.infer_target(task, focal, session, evidence)
        control = self.decide_control(task, focal, target, evidence)
        content_scope = self.build_content_scope(task, focal, control, evidence)
        policy = self.build_policy(task, focal, control, evidence)
        plan_events = self.build_plan_events(task, focal_id, target, control, content_scope, policy)

        session["last_focal_id"] = focal_id
        session["last_target"] = target
        session["last_control"] = control

        return {
            "focal_id": focal_id,
            "target": target,
            "control": control,
            "content_scope": content_scope,
            "policy": policy,
            "plan_events": plan_events,
            "user_response": self.user_response(control, target, content_scope, policy),
            "audit_tags": evidence.get("audit_tags", []),
            "counterfactual": "최신 기록, 동의 상태, 공유 범위, 보안 신호가 바뀌면 판단이 달라질 수 있습니다.",
        }

    def update_session_memory(self, task: dict[str, Any], session: dict[str, Any], evidence: dict[str, Any]) -> None:
        for record in records_of(task):
            if record.get("type") == "persistent_memory_write" and isinstance(record.get("value"), dict):
                value = record["value"]
                key = str(value.get("memory_key") or value.get("person") or "")
                if key:
                    self.memory[key] = value
        session["last_evidence"] = evidence

    def _resolve_marker_focal(self, task: dict[str, Any], objects: list[dict[str, Any]]) -> dict[str, Any] | None:
        """마커 간접참조로 focal 해석 (TERMS_GUIDE focal_marker_refs).

        경로: focal_resolution_trace.latest_phase -> phase_to_marker[phase] -> marker
        -> focal_marker_refs.marker_to_ref[marker] -> ref_code -> attrs.ref_code 일치 object.
        일반화 규칙(특정 task 하드코딩 아님). 마커 신호가 없으면 None.
        """
        rec = record_map(records_of(task))
        refs = rec.get("focal_marker_refs")
        trace = rec.get("focal_resolution_trace")
        if not isinstance(refs, dict) or not isinstance(trace, dict):
            return None
        marker_to_ref = refs.get("marker_to_ref")
        phase_to_marker = trace.get("phase_to_marker")
        if not isinstance(marker_to_ref, dict) or not isinstance(phase_to_marker, dict):
            return None
        phase = trace.get("latest_phase")
        marker = phase_to_marker.get(phase) if phase is not None else None
        ref_code = marker_to_ref.get(marker) if marker is not None else None
        if not ref_code:
            return None
        for obj in objects:
            if str((obj.get("attrs") or {}).get("ref_code")) == str(ref_code):
                return obj
        return None

    def choose_focal(self, task: dict[str, Any], session: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
        objects = objects_of(task)
        records = records_of(task)
        if not objects:
            return {}

        # 0) 마커 간접참조가 있으면 그것이 focal의 권위 있는 신호다.
        marker_focal = self._resolve_marker_focal(task, objects)
        if marker_focal is not None:
            return marker_focal

        object_by_id = {str(o.get("id")): o for o in objects}
        for record in reversed(records):
            value = record.get("value")
            candidates: list[str] = []
            if isinstance(value, str):
                candidates.append(value)
            elif isinstance(value, dict):
                candidates.extend(str(v) for v in value.values() if isinstance(v, str))
            for candidate in candidates:
                if candidate in object_by_id:
                    return object_by_id[candidate]

        history_text = " ".join(text_of(item) for item in task.get("visible_history", [])).lower()
        for obj in objects:
            ref_code = str((obj.get("attrs") or {}).get("ref_code") or "").lower()
            if ref_code and ref_code in history_text:
                return obj

        prompt_tokens = {tok for tok in re.findall(r"[A-Za-z0-9가-힣_]+", str(task.get("prompt", "")).lower()) if len(tok) >= 2}
        best = objects[0]
        best_score = -1
        for obj in objects:
            obj_text = object_text(obj)
            score = sum(1 for tok in prompt_tokens if tok in obj_text)
            if score > best_score:
                best = obj
                best_score = score
        return best

    def infer_target(self, task: dict[str, Any], focal: dict[str, Any], session: dict[str, Any], evidence: dict[str, Any]) -> str:
        rec = record_map(records_of(task))
        attrs = focal.get("attrs") or {}

        if "persistent_memory_write" in rec:
            return "memory_store"

        resolved = rec.get("resolved_target")
        if isinstance(resolved, dict):
            for key in ("target", "route", "value", "name", "recipient"):
                if resolved.get(key):
                    return str(resolved[key])
        if isinstance(resolved, str) and resolved:
            return resolved

        for key in ("recipient", "target", "channel", "app", "merchant", "name"):
            if attrs.get(key):
                return str(attrs[key])
        return str(session.get("last_target") or "user")

    def decide_control(self, task: dict[str, Any], focal: dict[str, Any], target: str, evidence: dict[str, Any]) -> str:
        records = records_of(task)
        types = {str(r.get("type")) for r in records}
        values = " ".join(text_of(r.get("value")) for r in records).lower()
        flags = set(evidence.get("risk_flags", []))

        if "security_alert" in types or "phishing" in flags or "safety_mode" in types or "privacy_guard" in types:
            return "hold"
        if "consent" in types and any(word in values for word in ["revoked", "withdraw", "denied", "철회", "거부"]):
            return "hold"
        # ask는 "진짜 미해소" 신호에만. Iter 002: ambiguous_target/ambiguous_focal 라벨과
        # SLM requires_confirmation(키워드 기반)은 ask/비-ask에 거의 무작위로 나타나 판별력이 없어
        # ask를 남발시켰다(실측). 이들을 트리거에서 빼고, target_changed_after_turn을 추가한다.
        if any(t in types for t in ["amount_changed", "merchant_verification", "duration_ambiguous", "memory_conflict", "target_changed_after_turn"]):
            return "ask"
        if evidence.get("requires_redaction") or any(t in types for t in ["external_share_policy", "share_scope", "payment_policy", "enterprise_policy_recall"]):
            return "amend"
        return "proceed"

    def build_content_scope(self, task: dict[str, Any], focal: dict[str, Any], control: str, evidence: dict[str, Any]) -> dict[str, Any]:
        attrs = focal.get("attrs") or {}
        contains = {str(x) for x in attrs.get("contains", [])} if isinstance(attrs.get("contains"), list) else set()

        if control == "hold":
            return {"mode": "none", "allowed_fields": [], "excluded_fields": [], "requires_user_confirmation": False}
        if control == "ask":
            return {"mode": "summary", "allowed_fields": ["status"], "excluded_fields": sorted(contains & {"raw_quote", "rrn", "location", "numeric_value", "doctor_note", "card_number"}), "requires_user_confirmation": True}
        if control == "amend" or evidence.get("requires_redaction"):
            excluded = sorted(contains & {"raw_quote", "rrn", "location", "numeric_value", "doctor_note", "card_number", "name"})
            return {"mode": "redacted", "allowed_fields": ["summary", "title", "status"], "excluded_fields": excluded or ["raw_quote"], "requires_user_confirmation": False}
        return {"mode": "summary", "allowed_fields": ["summary", "title", "status"], "excluded_fields": ["raw_quote"], "requires_user_confirmation": False}

    def build_policy(self, task: dict[str, Any], focal: dict[str, Any], control: str, evidence: dict[str, Any]) -> dict[str, Any]:
        flags = set(evidence.get("risk_flags", []))
        violations: set[str] = set()
        values = " ".join(text_of(r.get("value")) for r in records_of(task)).lower()
        if "revoked" in values or "철회" in values:
            violations.add("consent_revoked")
        if "phishing" in values or "피싱" in values:
            violations.add("security_alert_ignored")
        return {
            "risk_flags": sorted(flags),
            "violations": sorted(violations),
            "requires_confirmation": control == "ask",
        }

    def build_plan_events(self, task: dict[str, Any], focal_id: str, target: str, control: str, scope: dict[str, Any], policy: dict[str, Any]) -> list[dict[str, Any]]:
        events = [{"verb": "read", "target": focal_id, "args": {"purpose": "inspect_task_context"}}]
        if control == "hold":
            reason = policy.get("violations", ["safety_or_policy"])[0] if policy.get("violations") else "safety_or_policy"
            events.append({"verb": "guard", "target": focal_id, "args": {"reason": reason}})
        elif control == "ask":
            events.append({"verb": "clarify", "target": "user", "args": {"reason": "confirmation_required"}})
        else:
            if scope.get("mode") == "redacted":
                events.append({"verb": "redact", "target": focal_id, "args": {"remove": "sensitive_fields"}})
            elif scope.get("mode") in {"summary", "status_only"}:
                events.append({"verb": "summarize", "target": focal_id, "args": {"mode": scope.get("mode")}})
            events.append({"verb": "dispatch", "target": target, "args": {"scope": scope.get("mode")}})
        return events

    def user_response(self, control: str, target: str, scope: dict[str, Any], policy: dict[str, Any]) -> str:
        if control == "hold":
            return "보안, 동의 또는 정책 조건 때문에 진행하지 않겠습니다."
        if control == "ask":
            return "대상이나 허용 범위를 한 번 더 확인해야 합니다."
        if control == "amend":
            return f"민감 정보를 제외하고 {target}(으)로 진행하겠습니다."
        return f"요청한 범위로 {target}(으)로 진행하겠습니다."
