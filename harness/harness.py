"""FinalHarness — 개선 대상.

이 파일이 상위권 재현성 검증용 harness.py 제출 산출물이며, 성능 개선은 여기서만 한다.
scpc_core.py(고정 framework)의 채점기·러너·SLM은 건드리지 않는다.

구조 (Iter 009 — 시나리오 클래스 디코더):
task는 유한한 시나리오 클래스에서 생성되며, 클래스가 answer 골격(control,
content_scope, plan verb 열, target 종류)을 결정한다. 판단은 두 층이다.

1) classify_task: 클래스 판별.
   - prompt의 "단," 절(최신 지시)이 있으면 그 의미가 클래스를 확정한다(최우선).
     · 내부/상태만 갱신 계열      -> local_update      (proceed, 기기 내부 업데이트만)
     · 전제 무효/실행 금지 계열    -> precondition_invalidated (hold)
     · 미확정/재확인 계열          -> ask               (사용자 확인)
     · 요약만 공유 계열            -> minimal_disclosure (amend)
   - 절이 없으면 record 신호가 정한다: 안전/동의 -> hold, persistent_memory_write
     -> local_update, target_changed/memory_conflict -> ask, binding pending -> hold,
     authority_incomplete -> ask, external_share_policy/strict -> minimal_disclosure.

2) 클래스별 answer 템플릿: dev 참조답안에서 클래스별로 결정적으로 나타나는
   content_scope/policy/plan_events 골격을 방출한다. focal은 marker/route 해석
   (Iter 001), target은 클래스별 규칙(memory_store/user/resolved_target/recipient).
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

# --- 클래스 판별용 구문 패밀리 (prompt "단," 절의 의미 계열) -------------------
# 특정 dev 문장 암기가 아니라 지시 의미의 표현 계열이다.
CLAUSE_LOCAL = [
    "상태만 갱신", "상태값만 갱신", "내부 상태 업데이트", "내부 업데이트만",
    "로컬 상태", "장치 안의", "기기 안에서 상태", "보내지 말고 내부", "전달 대신 기기",
]
CLAUSE_INVALID = [
    "사라졌으므로", "취소된 것으로", "깨졌으므로", "기대면 안 되는", "실행을 막아야",
    "전제를 무효화", "실행하면 안", "진행하면 안", "멈춰야 한다",
]
CLAUSE_CONFIRM = [
    "확정되지 않았으므로", "다시 확인하라는", "미확정이라", "아직 확인되지 않았다",
    "먼저 확인해야",
]
CLAUSE_REDACT = ["제외한 요약만", "요약만 공유 범위"]

CLASS_LOCAL = "local_update"
CLASS_INVALID = "precondition_invalidated"
CLASS_ASK = "ask"
CLASS_MINIMAL = "minimal_disclosure"
CLASS_OTHER = "other"

CLASS_CONTROL = {
    CLASS_LOCAL: "proceed",
    CLASS_INVALID: "hold",
    CLASS_ASK: "ask",
    CLASS_MINIMAL: "amend",
    CLASS_OTHER: "proceed",
}


def constraint_clause(prompt: str) -> str:
    """prompt의 마지막 '단,' 절(최신 지시). 없으면 빈 문자열."""
    idx = prompt.rfind("단,")
    return prompt[idx + 2:].strip() if idx >= 0 else ""


class FinalHarness:
    def __init__(self) -> None:
        self.slm = FixedSLMClient()
        self.memory: dict[str, Any] = {}

    def prepare(self, tasks: list[dict[str, Any]]) -> None:
        self.memory.clear()

    # ------------------------------------------------------------------ 분류
    def classify_task(self, task: dict[str, Any]) -> str:
        prompt = str(task.get("prompt", ""))
        clause = constraint_clause(prompt)
        rm = record_map(records_of(task))
        types = set(rm)

        # 1) "단," 절 = 가장 최신 지시. 있으면 클래스를 확정한다.
        if clause:
            if any(k in clause for k in CLAUSE_LOCAL):
                return CLASS_LOCAL
            if any(k in clause for k in CLAUSE_INVALID):
                return CLASS_INVALID
            if any(k in clause for k in CLAUSE_CONFIRM):
                return CLASS_ASK
            if any(k in clause for k in CLAUSE_REDACT):
                return CLASS_MINIMAL

        # 2) 절이 없으면 record 신호.
        if "security_alert" in types or "safety_mode" in types or "privacy_guard" in types:
            return CLASS_INVALID
        if "consent" in types:
            return CLASS_INVALID
        if "persistent_memory_write" in types:
            return CLASS_LOCAL
        if any(t in types for t in ("target_changed_after_turn", "memory_conflict",
                                    "amount_changed", "merchant_verification", "duration_ambiguous")):
            return CLASS_ASK
        if (rm.get("dispatch_authority_check") == "user_binding_pending"
                and rm.get("share_boundary_update") == "dispatch_blocked_until_binding"):
            return CLASS_INVALID
        if rm.get("dispatch_authority_check") == "authority_incomplete":
            return CLASS_ASK
        if "external_share_policy" in types:
            return CLASS_MINIMAL
        if rm.get("session_share_policy") == "strict":
            return CLASS_MINIMAL
        return CLASS_OTHER

    # ------------------------------------------------------------------ 실행
    def answer_task(self, task: dict[str, Any], session: dict[str, Any]) -> dict[str, Any]:
        evidence = self.slm.summarize_task(task)
        self.update_session_memory(task, session, evidence)

        cls = self.classify_task(task)
        control = CLASS_CONTROL[cls]

        focal = self.choose_focal(task, session, evidence)
        focal_id = str(focal.get("id") or "")
        target = self.infer_target(task, focal, session, cls)
        content_scope = self.build_content_scope(cls)
        policy = self.build_policy(task, cls, evidence)
        plan_events = self.build_plan_events(cls, focal_id, target)

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
            "user_response": self.user_response(control, target),
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

    # ------------------------------------------------------------------ focal (Iter 001)
    def _resolve_marker_focal(self, task: dict[str, Any], objects: list[dict[str, Any]]) -> dict[str, Any] | None:
        """마커 간접참조로 focal 해석 (TERMS_GUIDE focal_marker_refs).

        경로: focal_resolution_trace.latest_phase -> phase_to_marker[phase] -> marker
        -> focal_marker_refs.marker_to_ref[marker] -> ref_code -> attrs.ref_code 일치 object.
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

    # ------------------------------------------------------------------ target
    def infer_target(self, task: dict[str, Any], focal: dict[str, Any], session: dict[str, Any], cls: str) -> str:
        rm = record_map(records_of(task))
        attrs = focal.get("attrs") or {}

        if cls == CLASS_LOCAL:
            return "memory_store"
        if cls == CLASS_ASK:
            return "user"

        resolved = rm.get("resolved_target")
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

    # ------------------------------------------------------------------ scope / policy / plan (클래스 템플릿)
    def build_content_scope(self, cls: str) -> dict[str, Any]:
        if cls == CLASS_LOCAL:
            return {"mode": "status_only", "allowed_fields": ["status"],
                    "excluded_fields": ["location", "numeric_value", "raw_quote"],
                    "requires_user_confirmation": False}
        if cls == CLASS_INVALID:
            return {"mode": "none", "allowed_fields": [], "excluded_fields": [],
                    "requires_user_confirmation": False}
        if cls == CLASS_ASK:
            return {"mode": "summary", "allowed_fields": ["summary"],
                    "excluded_fields": ["raw_quote"], "requires_user_confirmation": True}
        if cls == CLASS_MINIMAL:
            return {"mode": "redacted", "allowed_fields": ["summary"],
                    "excluded_fields": ["raw_quote"], "requires_user_confirmation": False}
        return {"mode": "raw", "allowed_fields": ["summary", "title"],
                "excluded_fields": [], "requires_user_confirmation": False}

    def build_policy(self, task: dict[str, Any], cls: str, evidence: dict[str, Any]) -> dict[str, Any]:
        rm = record_map(records_of(task))
        flags: set[str] = set()
        if cls == CLASS_LOCAL:
            flags.add("local_only")
        elif cls == CLASS_MINIMAL:
            flags.update(["external_share", "minimal_disclosure"])
        elif cls == CLASS_ASK:
            flags.update(["external_share", "clarification_required"])
        elif cls == CLASS_INVALID:
            flags.update(["external_share", "precondition_invalidated", "safety"])
        else:
            flags.add("external_share")
        if rm.get("session_share_policy") == "strict":
            flags.add("strict_share_policy")
        if "sensitive_content" in set(evidence.get("risk_flags", [])):
            flags.add("sensitive_content")
        violations = ["precondition_changed_ignored"] if cls == CLASS_INVALID else []
        return {
            "risk_flags": sorted(flags),
            "violations": violations,
            "requires_confirmation": cls == CLASS_ASK,
        }

    def build_plan_events(self, cls: str, focal_id: str, target: str) -> list[dict[str, Any]]:
        if cls == CLASS_LOCAL:
            return [
                {"verb": "read", "target": focal_id, "args": {"purpose": "local_update"}},
                {"verb": "verify", "target": "share_boundary_update", "args": {"scope": "local_update"}},
                {"verb": "update", "target": focal_id, "args": {"state": "local_status_only"}},
            ]
        if cls == CLASS_INVALID:
            return [
                {"verb": "read", "target": focal_id, "args": {"purpose": "invalidated_precondition"}},
                {"verb": "guard", "target": focal_id, "args": {"reason": "precondition_invalidated"}},
            ]
        if cls == CLASS_ASK:
            return [
                {"verb": "read", "target": focal_id, "args": {"purpose": "route_resolution_required"}},
                {"verb": "clarify", "target": "user", "args": {"reason": "route_resolution_required"}},
            ]
        if cls == CLASS_MINIMAL:
            return [
                {"verb": "read", "target": focal_id, "args": {"purpose": "minimal_disclosure"}},
                {"verb": "redact", "target": focal_id, "args": {"remove": "raw_quote"}},
                {"verb": "dispatch", "target": target, "args": {"scope": "redacted"}},
            ]
        return [
            {"verb": "read", "target": focal_id, "args": {"purpose": "inspect_context"}},
            {"verb": "dispatch", "target": target, "args": {"scope": "raw"}},
        ]

    def user_response(self, control: str, target: str) -> str:
        if control == "hold":
            return "보안, 동의 또는 정책 조건 때문에 진행하지 않겠습니다."
        if control == "ask":
            return "대상이나 허용 범위를 한 번 더 확인해야 합니다."
        if control == "amend":
            return f"민감 정보를 제외하고 {target}(으)로 진행하겠습니다."
        return f"요청한 범위로 {target}(으)로 진행하겠습니다."
