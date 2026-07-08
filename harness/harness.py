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
# 특정 문장 암기가 아니라 "같은 지시"의 한국어 표현 계열(개념 어휘)이다.
# 절은 템플릿 생성이라 의미 계열이 유한하며, 계열 단위로 잡아야 새 표현에도 일반화된다.

# ① 내부 처리 한정: "밖으로 보내지 말고 기기/장치 내부의 상태·기록만 갱신하라"
CLAUSE_LOCAL = [
    # 상태/기록 갱신 표현
    "상태만 갱신", "상태값만 갱신", "상태 표시만 갱신", "상태 기록만", "처리 상태만",
    "완료 상태만", "내부 상태", "내부 기록", "내부 업데이트", "로컬 상태", "로컬 처리 상태",
    "상태 정리에 한정", "기록을 갱신하는 것으로 끝",
    # 외부 전송 배제 표현
    "보내지 말고 내부", "전달 대신 기기", "기기 안에서", "기기 안의", "장치 안의",
    "장치 내부", "전송을 하지 말", "보내기는 접", "전달 단계는 빼", "넘기는 대신",
    "수신처 처리는 생략", "공유하지 말고 상태",
]
# ② 전제 무효화: "허용 근거가 깨졌/사라졌/뒤집혔으니 실행하지 말라"
CLAUSE_INVALID = [
    "사라졌으므로", "사라진 상태", "취소된 것으로", "깨졌으므로", "깨뜨리므로",
    "기대면 안 되는", "실행을 막아야", "전제를 무효화", "실행하면 안", "진행하면 안",
    "멈춰야 한다", "멈춘다", "근거가 무너", "승인 조건을 깨", "믿을 수 없으므로",
    "근거를 뒤집", "실행을 보류", "요청을 보류", "차단한다", "수행하면 위험",
    "더 진행하지 말",
]
# ③ 확인 필요: "확정되지 않았으니 사용자에게 먼저 확인/질문하라"
CLAUSE_CONFIRM = [
    "확정되지 않았", "다시 확인하라", "미확정", "아직 확인되지 않", "먼저 확인",
    "확인 절차를 먼저", "확인 질문", "사용자 확인을 받아", "clarification",
    "다시 물어봐", "물어봐야", "확정 정보가 없", "유효성이 불분명",
]
# ④ 요약/민감정보 제외 한정: "원문·장소·수치는 빼고 정제된 요약만 공유하라"
CLAUSE_REDACT = [
    "제외한 요약만", "요약만 공유 범위", "제거한 요약", "요약만 허용", "최소 요약",
    "민감 세부값", "민감 필드를 제거", "익명화된 요약", "정제된 요약", "요약 수준으로만",
    "세부는 제외", "포함하지 않는다",
]

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
        content_scope = self.build_content_scope(cls, focal)
        policy = self.build_policy(task, cls, evidence, focal)
        plan_events = self.build_plan_events(cls, focal_id, target, focal)

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

    def _resolve_history_focal(self, task: dict[str, Any], objects: list[dict[str, Any]]) -> dict[str, Any] | None:
        """visible_history 선택 서사로 focal 해석 (마커 없는 다후보 task).

        history가 후보 ref_code(WM-…)들을 나열하고 그중 하나를 지목하는 유형:
        · "최종 승인 후보 WM-X" / "승인 표시가 남은 것은 WM-X" -> 그 코드
        · "두 번째 후보만 확정" / "가운데 항목만 남았다" 등 서수 선택 -> 나열 순서의 해당 코드
        개념 수준(승인·확정·잔존 표현 + 한국어 서수) 규칙이며 특정 문장 암기가 아니다.
        """
        by_ref = {str((o.get("attrs") or {}).get("ref_code")): o for o in objects}
        # ① 지목형: 특정 코드를 직접 지정하는 표현 계열 (고정/지정/통과/승인 유지/최종 승인/잔존)
        designation = [
            r"최종\s*승인\s*후보[^W]{0,10}(WM-\d+)",
            r"(?:승인\s*표시가?\s*남은\s*것은|남은\s*것은)\s*(WM-\d+)",
            r"(?:유지된|승인\s*상태가\s*유지된)\s*참조는\s*(WM-\d+)",
            r"(WM-\d+)\s*(?:로|으로)\s*고정",
            r"(WM-\d+)\s*만\s*통과",
            r"binding[은는]?\s*(WM-\d+)",
            r"(WM-\d+)[을를]\s*현재\s*턴의\s*참조로",
            r"처리할\s*ref[는은]?\s*(WM-\d+)",
        ]
        # ② 서수 선택형: 선택 표지("~만 확정/선택/남았", "유효한 항목은 ~")에 **결합된** 서수만 유효.
        #    (같은 문장에 배제된 서수들이 함께 나올 수 있으므로 단독 등장으로 고르면 안 된다)
        ORD = {"첫 번째": 0, "첫째": 0, "두 번째": 1, "둘째": 1, "세 번째": 2, "셋째": 2,
               "가운데": None, "마지막": -1}
        ord_alt = "|".join(ORD)
        bound_ordinal = [
            rf"({ord_alt})\s*(?:후보|항목)?\s*만",          # "두 번째 후보만 확정", "둘째 항목만 선택"
            rf"유효한\s*항목은\s*({ord_alt})",                # "유효한 항목은 두 번째다"
            rf"({ord_alt})\s*항목만",
        ]
        for item in reversed(task.get("visible_history", []) or []):
            line = text_of(item.get("summary", "") if isinstance(item, dict) else item)
            codes = re.findall(r"WM-\d+", line)
            if not codes:
                continue
            for pat in designation:
                m = re.search(pat, line)
                if m and m.group(1) in by_ref:
                    return by_ref[m.group(1)]
            for pat in bound_ordinal:
                m = re.search(pat, line)
                if not m:
                    continue
                i = ORD[m.group(1)]
                idx = len(codes) // 2 if i is None else (len(codes) - 1 if i == -1 else i)
                if 0 <= idx < len(codes) and codes[idx] in by_ref:
                    return by_ref[codes[idx]]
                break
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

        # 0.5) history 선택 서사(승인/확정/서수 지목)가 있으면 그것을 따른다.
        history_focal = self._resolve_history_focal(task, objects)
        if history_focal is not None:
            return history_focal

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
    def _recall_profile_target(self, task: dict[str, Any]) -> str | None:
        """persistent_memory_recall → 저장 프로필(self.memory)에서 채널 필드 선택.

        저장은 update_session_memory의 persistent_memory_write 처리로 이미 이뤄진다.
        어느 필드가 target인지는 요청 도메인이 정한다(승인/규정→approval_channel,
        조명→dusk_room, 쿠폰 전송→preferred_channel, 그 외 기본 health_channel).
        """
        rm = record_map(records_of(task))
        pr = rm.get("persistent_memory_recall")
        if not isinstance(pr, dict):
            return None
        prof = self.memory.get(str(pr.get("memory_key") or "")) or self.memory.get(str(pr.get("person") or ""))
        if not isinstance(prof, dict):
            return None
        p = str(task.get("prompt", ""))
        if any(k in p for k in ("승인", "규정", "검토", "성공")):
            field = "approval_channel"
        elif any(k in p for k in ("조명", "어두워")):
            field = "dusk_room"
        elif "쿠폰" in p:
            field = "preferred_channel"
        else:
            field = "health_channel"
        val = prof.get(field)
        return str(val) if val else None

    def infer_target(self, task: dict[str, Any], focal: dict[str, Any], session: dict[str, Any], cls: str) -> str:
        rm = record_map(records_of(task))
        attrs = focal.get("attrs") or {}

        if cls == CLASS_LOCAL:
            return "memory_store"
        if cls == CLASS_INVALID:
            # 절(최신 지시)로 중단된 hold는 사용자 보고(user), record 신호로 중단된 hold는
            # 원래 대상 유지(resolved/recipient 경로). dev 검증: 절→user 6/6, 무절→named 9/9.
            clause = constraint_clause(str(task.get("prompt", "")))
            if clause and any(k in clause for k in CLAUSE_INVALID):
                return "user"
        if cls == CLASS_ASK:
            # ① target_changed 값이 새 대상 이름을 직접 담는 경우 (상태 문구는 제외)
            tc = rm.get("target_changed_after_turn")
            if isinstance(tc, str) and re.fullmatch(r"[a-z][a-z0-9_]+", tc) \
                    and not re.search(r"prior|superseded|changed|stale", tc):
                return tc
            # ② 저장 프로필 회수(세션/기기 메모리)
            recalled = self._recall_profile_target(task)
            if recalled:
                return recalled
            # (해석된 라우트로의 fallback은 실측상 true-user를 깨뜨려 제외 — ask의 기본은 user)
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
    def build_content_scope(self, cls: str, focal: dict[str, Any]) -> dict[str, Any]:
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
            # 제외 필드 = focal이 실제 보유한 민감 필드(정규화 교집합), 없으면 raw_quote 기본
            sensitive = self._sensitive_in_focal(focal)
            return {"mode": "redacted", "allowed_fields": ["summary"],
                    "excluded_fields": sensitive or ["raw_quote"], "requires_user_confirmation": False}
        return {"mode": "raw", "allowed_fields": ["summary", "title"],
                "excluded_fields": [], "requires_user_confirmation": False}

    SENSITIVE_FIELDS = {"raw_quote", "rrn", "location", "numeric_value", "name", "doctor_note", "card_number"}
    FIELD_NORM = {"amount": "numeric_value", "address": "location"}

    def _sensitive_in_focal(self, focal: dict[str, Any]) -> list[str]:
        cont = (focal.get("attrs") or {}).get("contains") or []
        return sorted({self.FIELD_NORM.get(str(x), str(x)) for x in cont} & self.SENSITIVE_FIELDS)

    def build_policy(self, task: dict[str, Any], cls: str, evidence: dict[str, Any], focal: dict[str, Any]) -> dict[str, Any]:
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
        if "ambiguous_target" in rm:  # 대상 모호 record ⟺ target_ambiguity flag (dev P=1.00/R=0.93)
            flags.add("target_ambiguity")
        # sensitive_content는 SLM 키워드가 아니라 focal 객체의 민감 필드 보유 여부로 판단 (dev 검증 95%+)
        if self._sensitive_in_focal(focal):
            flags.add("sensitive_content")
        violations = ["precondition_changed_ignored"] if cls == CLASS_INVALID else []
        return {
            "risk_flags": sorted(flags),
            "violations": violations,
            "requires_confirmation": cls == CLASS_ASK,
        }

    def build_plan_events(self, cls: str, focal_id: str, target: str, focal: dict[str, Any]) -> list[dict[str, Any]]:
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
                {"verb": "redact", "target": focal_id,
                 "args": {"remove": "sensitive_fields" if self._sensitive_in_focal(focal) else "raw_quote"}},
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
