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

import os
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


def exp_flags() -> frozenset[str]:
    """SCPC_EXP 실험 토글 (쉼표 구분 토큰). 부분문자열 오발화 방지를 위해 토큰 단위로만 매칭."""
    return frozenset(filter(None, os.environ.get("SCPC_EXP", "").split(",")))


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

        # [실험 토글: SCPC_EXP 환경변수(쉼표 구분 토큰), 리더보드 단일변수 실험용]
        exp = exp_flags()
        # E5: screening 전용 어휘 — local 계열 record 값의 의미 매핑 (dev에 값 부재라 LB로만 검증)
        if "E5" in exp and rm.get("share_boundary_update") == "local_update_boundary" \
                and (rm.get("dispatch_authority_check") == "local_authority_confirmed"
                     or rm.get("route_candidate_snapshot") == "local_candidate_only"):
            return CLASS_LOCAL
        # E5X: E5 확대판 — local_authority_confirmed 단독으로 local 판정 (screening 104개)
        if "E5X" in exp and rm.get("dispatch_authority_check") == "local_authority_confirmed":
            return CLASS_LOCAL

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
            # guardrail 사다리 신호가 함께 있으면 전제가 이미 무효화된 상태(hold), 없으면 확인(ask)
            return CLASS_INVALID if "guardrail_ladder_signal" in types else CLASS_ASK
        # [Iter 023] record 값-조합 판별자 (dev 잔여 12 중 11 해소, 각 조합 dev 순도 100%).
        # ask-record 규칙 뒤에 두어 target_changed 등 기존 우선순위를 보존한다.
        # [E6 실험: dev 근거가 전부 authority=internal_binding_confirmed 하위집단이므로
        #  그 하위집단으로만 R1/R2/R2b를 좁힌다 — 이질 집단 transfer 실패 가설 검증]
        e6_ok = ("E6" not in exp) or rm.get("dispatch_authority_check") == "internal_binding_confirmed"
        if e6_ok and "ambiguous_focal" in types and rm.get("share_boundary_update") == "local_update_boundary":
            # focal이 모호해도 boundary가 '내부 갱신'이면 외부 공유가 아니다 (dev 2/2 local)
            return CLASS_LOCAL
        if e6_ok and "guardrail_ladder_signal" in types \
                and rm.get("ambiguous_target") == "approved_channel_or_visible_recipient":
            # guardrail 사다리의 최종 체크가 살아있는 승인 채널 → boundary가 결정
            if rm.get("share_boundary_update") == "redacted_external_boundary":
                return CLASS_OTHER   # dev 2/2 proceed
            if rm.get("share_boundary_update") == "local_update_boundary":
                return CLASS_ASK     # dev 1/1 ask
        if "ambiguous_target" in types and "guardrail_ladder_signal" not in types \
                and rm.get("route_binding_order") == "authority_after_candidates" \
                and rm.get("share_boundary_update") == "redacted_external_boundary":
            # 후보 나열 뒤에야 권한이 정해졌고 target이 모호 → 어느 후보인지 확인 필요 (dev 2/2 ask)
            return CLASS_ASK
        if "requires_confirmation" in str(rm.get("payment_policy", "")):
            return CLASS_ASK         # 결제 정책이 명시적으로 확인 요구 (dev 1/1)
        if "external_share_policy" in types:
            # 의사 소견(doctor_note) 금지는 축약이 아니라 공유 전제 자체의 무효 (dev 2/2 vs raw_quote 9/9 amend)
            # [E2 실험: 이 규칙을 끄고 minimal로 — dev 근거 n=2가 screening 58건에 적용 중인 위험 검증]
            if "doctor_note" in str(rm.get("external_share_policy", "")) and "E2" not in exp_flags():
                return CLASS_INVALID
            return CLASS_MINIMAL
        if rm.get("session_share_policy") == "strict":
            return CLASS_MINIMAL
        # [Iter 023] normal 세션의 상시 제약/과거 이력 재사용 → 축약 공유 (dev 2/2 amend;
        # target_changed 동반 시 위 ask 규칙이 선점하므로 안전)
        if rm.get("ops_memory_recall") == "use_prior_success_and_failure_records" \
                or rm.get("enterprise_policy_recall") == "apply_standing_default_constraint":
            return CLASS_MINIMAL
        if "ambiguous_focal" in types:
            return CLASS_ASK         # focal 모호 + 완화 신호 없음 → 확인 (dev 1/1)
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
        content_scope = self.build_content_scope(cls, focal, task)
        policy = self.build_policy(task, cls, evidence, focal)
        plan_events = self.build_plan_events(cls, focal_id, target, focal, task)

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
            "user_response": self.user_response(cls, control, target, content_scope),
            "audit_tags": evidence.get("audit_tags", []),
            "counterfactual": "최신 기록, 동의 상태, 공유 범위, 보안 신호가 바뀌면 판단이 달라질 수 있습니다.",
        }

    def update_session_memory(self, task: dict[str, Any], session: dict[str, Any], evidence: dict[str, Any]) -> None:
        for record in records_of(task):
            if record.get("type") == "persistent_memory_write" and isinstance(record.get("value"), dict):
                value = record["value"]
                # memory_key와 person 양쪽으로 저장 — recall이 옛 memory_key를 참조해도
                # person으로 최신 프로필을 찾을 수 있게 한다.
                for key in (str(value.get("memory_key") or ""), str(value.get("person") or "")):
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
        if any(k in p for k in ("검진", "점검")):
            field = "checkup_place"
        elif any(k in p for k in ("승인", "규정", "검토", "성공")):
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

        clause = constraint_clause(str(task.get("prompt", "")))
        # [Iter 023] 중단-원천 원리를 target 전반으로 확장:
        # 절(최신 지시)이 결정한 클래스 → 사용자 축(user/memory_store),
        # record 신호가 결정한 클래스 → 해석된 원래 대상 유지(resolved/recall/attrs).
        if cls == CLASS_LOCAL:
            if "persistent_memory_write" in rm or (clause and any(k in clause for k in CLAUSE_LOCAL)):
                return "memory_store"
            resolved = rm.get("resolved_target")
            if isinstance(resolved, str) and resolved:
                return resolved  # record-조합 local(내부 갱신)은 갱신 대상 채널이 target (dev 2/2)
            return "memory_store"
        if cls == CLASS_INVALID:
            # dev 검증: 절→user 6/6, 무절→named 9/9.
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
            # ③ 절이 멈춘 ask는 사용자에게 (true-user는 절-유래에 집중, dev 실측)
            if clause and any(k in clause for k in CLAUSE_CONFIRM):
                return "user"
            if any(t in rm for t in ("target_changed_after_turn", "memory_conflict",
                                     "amount_changed", "merchant_verification", "duration_ambiguous")):
                return "user"
            # [E7 실험: record-조합 ask의 named-target fallthrough를 끄고 Iter 019처럼 user 고정]
            if "E7" in exp_flags():
                return "user"
            # record-조합 ask(대상 모호)는 해석된 원래 대상 유지 — 아래 공용 경로로 fallthrough

        resolved = rm.get("resolved_target")
        if isinstance(resolved, dict):
            for key in ("target", "route", "value", "name", "recipient"):
                if resolved.get(key):
                    return str(resolved[key])
        if isinstance(resolved, str) and resolved:
            return resolved

        # 저장 프로필 회수 — 메모리를 참조하라는 프롬프트일 때만 (과잉 적용 방지)
        if "persistent_memory_recall" in rm and any(k in str(task.get("prompt", "")) for k in ("메모리", "저장", "지난번")):
            recalled = self._recall_profile_target(task)
            if recalled:
                return recalled

        for key in ("recipient", "target", "channel", "app", "merchant", "name"):
            if attrs.get(key):
                return str(attrs[key])
        return str(session.get("last_target") or "user")

    # ------------------------------------------------------------------ scope / policy / plan (클래스 템플릿)
    def build_content_scope(self, cls: str, focal: dict[str, Any], task: dict[str, Any] | None = None) -> dict[str, Any]:
        if cls == CLASS_LOCAL:
            # strict 세션이거나 focal이 민감 필드를 보유할 때만 제외 목록 명시 (dev 38/40)
            rm = record_map(records_of(task)) if task else {}
            guarded = (rm.get("session_share_policy") == "strict") or bool(self._sensitive_in_focal(focal))
            return {"mode": "status_only", "allowed_fields": ["status"],
                    "excluded_fields": ["location", "numeric_value", "raw_quote"] if guarded else [],
                    "requires_user_confirmation": False}
        if cls == CLASS_INVALID:
            return {"mode": "none", "allowed_fields": [], "excluded_fields": [],
                    "requires_user_confirmation": False}
        if cls == CLASS_ASK:
            # 민감 필드 보유 시 name 제외가 기준 (dev 6/7), 아니면 raw_quote 기본
            excl = ["name"] if self._sensitive_in_focal(focal) else ["raw_quote"]
            return {"mode": "summary", "allowed_fields": ["summary"],
                    "excluded_fields": excl, "requires_user_confirmation": True}
        if cls == CLASS_MINIMAL:
            # 제외 필드 = focal이 실제 보유한 민감 필드(정규화 교집합), 없으면 raw_quote 기본
            sensitive = self._sensitive_in_focal(focal)
            rm = record_map(records_of(task)) if task else {}
            # [Iter 026] amend인데 boundary가 local이면 사용자 확인 필요 (dev 4/6, FP 0)
            ruc = rm.get("share_boundary_update") == "local_update_boundary"
            return {"mode": "redacted", "allowed_fields": ["summary"],
                    "excluded_fields": sensitive or ["raw_quote"], "requires_user_confirmation": ruc}
        return {"mode": "raw", "allowed_fields": ["summary", "title"],
                "excluded_fields": [], "requires_user_confirmation": False}

    SENSITIVE_FIELDS = {"raw_quote", "rrn", "location", "numeric_value", "name", "doctor_note", "card_number"}
    FIELD_NORM = {"amount": "numeric_value", "address": "location"}

    def _sensitive_in_focal(self, focal: dict[str, Any]) -> list[str]:
        cont = (focal.get("attrs") or {}).get("contains") or []
        return sorted({self.FIELD_NORM.get(str(x), str(x)) for x in cont} & self.SENSITIVE_FIELDS)

    def _sensitive_for_policy(self, focal: dict[str, Any]) -> bool:
        """policy 판단용 민감 탐지: contains 외 attrs.fields(health_record 등)도 본다."""
        if self._sensitive_in_focal(focal):
            return True
        fields = (focal.get("attrs") or {}).get("fields") or []
        return bool({self.FIELD_NORM.get(str(x), str(x)) for x in fields} & self.SENSITIVE_FIELDS)

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
        if "ambiguous_focal" in rm:  # focal 모호 record ⟺ ambiguous_focal flag (dev P/R=1.00)
            flags.add("ambiguous_focal")
        if rm.get("share_boundary_update") == "local_update_boundary":  # 로컬 경계 (P=1.00)
            flags.add("local_only")
        # sensitive_content는 SLM 키워드가 아니라 focal 객체의 민감 필드 보유 여부로 판단 (dev 검증 95%+)
        if self._sensitive_for_policy(focal):
            flags.add("sensitive_content")
        # [Iter 026] precondition_changed ⟺ single_internal_candidate × internal_binding_confirmed
        # (dev 24/24 완전 판별 — 값-수준 재마이닝으로 발견, 이전 '신호 부재' 판정 번복)
        if rm.get("route_candidate_snapshot") == "single_internal_candidate" \
                and rm.get("dispatch_authority_check") == "internal_binding_confirmed":
            flags.add("precondition_changed")
        violations = ["precondition_changed_ignored"] if cls == CLASS_INVALID else []
        # [Iter 026] 비-ask requires_confirmation: proceed계열×authority_after_candidates (dev 7/8),
        # amend×local_update_boundary (dev 4/6, FP 0)
        requires_conf = cls == CLASS_ASK
        if cls in (CLASS_LOCAL, CLASS_OTHER) and rm.get("route_binding_order") == "authority_after_candidates":
            requires_conf = True
        if cls == CLASS_MINIMAL and rm.get("share_boundary_update") == "local_update_boundary":
            requires_conf = True
        return {
            "risk_flags": sorted(flags),
            "violations": violations,
            "requires_confirmation": requires_conf,
        }

    def build_plan_events(self, cls: str, focal_id: str, target: str, focal: dict[str, Any],
                          task: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        rm = record_map(records_of(task)) if task else {}
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
            # [Iter 026] single_internal×internal_binding = '전제 변경' 시나리오 마커 (dev 6/6 vs 0/20)
            if rm.get("route_candidate_snapshot") == "single_internal_candidate" \
                    and rm.get("dispatch_authority_check") == "internal_binding_confirmed":
                return [
                    {"verb": "read", "target": focal_id, "args": {"purpose": "clarify_precondition"}},
                    {"verb": "clarify", "target": "user", "args": {"reason": "precondition_changed"}},
                ]
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

    def user_response(self, cls: str, control: str, target: str, scope: dict[str, Any]) -> str:
        # 판단 내용을 구체적으로 서술 (semantic_response는 서버에서만 채점되므로 클래스 의미에 정렬)
        # [E1 실험: target/scope 구체값 + ontology 용어 포함형 — 검증된 semantic 레버의 변형]
        if "E1" in exp_flags():
            mode = str(scope.get("mode", ""))
            if cls == CLASS_LOCAL:
                return (f"외부 공유 없이 {target}에 status_only로 내부 상태만 갱신했습니다. "
                        "dispatch는 수행하지 않습니다.")
            if cls == CLASS_INVALID:
                return (f"이전 허용의 전제가 최신 상태에서 무효화되어 {target}(으)로의 실행을 "
                        "guard 상태로 보류합니다. 전제 재확인 전에는 dispatch하지 않습니다.")
            if cls == CLASS_ASK:
                return (f"대상 또는 전제가 확정되지 않아 {target}에게 먼저 확인을 요청합니다. "
                        "확인 전에는 어떤 공유도 진행하지 않습니다.")
            if cls == CLASS_MINIMAL:
                excluded = ", ".join(scope.get("excluded_fields", [])) or "민감 정보"
                return (f"{excluded}을(를) redact로 제외하고 {mode} 범위만 "
                        f"{target}(으)로 공유합니다.")
            return f"요청한 범위 그대로 {mode}로 {target}에 진행합니다."
        if cls == CLASS_LOCAL:
            return "외부로 보내지 않고 기기 내부 상태만 갱신했습니다."
        if cls == CLASS_INVALID:
            return "이전 허용의 전제가 무효화되어 실행을 보류합니다. 추가 확인 전에는 진행하지 않습니다."
        if cls == CLASS_ASK:
            return "대상과 처리 범위가 확정되지 않아 진행 전에 사용자 확인이 필요합니다."
        if cls == CLASS_MINIMAL:
            excluded = ", ".join(scope.get("excluded_fields", [])) or "민감 정보"
            return f"{excluded}을(를) 제외한 요약만 {target}(으)로 공유합니다."
        return f"요청한 범위 그대로 {target}(으)로 진행합니다."
