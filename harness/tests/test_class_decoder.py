"""Iter 009 회귀 잠금: 시나리오 클래스 디코더.

합성 입력. "단," 절(최신 지시)이 클래스를 확정하고, 절이 없으면 record 신호가 정한다.
클래스는 answer 골격(control/scope/plan verbs/target 종류)을 결정한다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness import FinalHarness


def _task(prompt: str, record_types: list[str] | None = None, records: list[dict] | None = None) -> dict:
    recs = records or [{"id": f"r{i}", "type": t, "value": "x"} for i, t in enumerate(record_types or [])]
    return {
        "id": "syn",
        "prompt": prompt,
        "device_state": {
            "objects": [{"id": "obj_A", "type": "message", "attrs": {"recipient": "hana"}}],
            "records": recs,
        },
    }


def test_clause_local_update_full_skeleton():
    h = FinalHarness()
    ans = h.answer_task(_task("자료를 보내줘. 단, 공유하지 말고 상태값만 갱신하라는 수정이 최신이다."), {})
    assert ans["control"] == "proceed"
    assert ans["content_scope"]["mode"] == "status_only"
    assert ans["target"] == "memory_store"
    assert [e["verb"] for e in ans["plan_events"]] == ["read", "verify", "update"]


def test_clause_invalidated_holds():
    h = FinalHarness()
    ans = h.answer_task(_task("공유해줘. 단, 허용 근거가 최신 상태에서 깨졌으므로 이 요청은 멈춰야 한다."), {})
    assert ans["control"] == "hold"
    assert ans["content_scope"]["mode"] == "none"
    assert [e["verb"] for e in ans["plan_events"]] == ["read", "guard"]
    assert "precondition_changed_ignored" in ans["policy"]["violations"]


def test_clause_confirm_asks():
    h = FinalHarness()
    ans = h.answer_task(_task("공유해줘. 단, 새 전제가 확정되지 않았으므로 처리 전에 사용자에게 먼저 확인해야 한다."), {})
    assert ans["control"] == "ask"
    assert ans["content_scope"]["requires_user_confirmation"] is True
    assert [e["verb"] for e in ans["plan_events"]] == ["read", "clarify"]
    assert ans["target"] == "user"


def test_no_clause_records_decide():
    h = FinalHarness()
    # 안전 record -> hold
    assert h.answer_task(_task("처리해줘.", ["safety_mode"]), {})["control"] == "hold"
    # 메모리 쓰기 -> local_update(proceed/memory_store)
    a = h.answer_task(_task("저장해줘.", ["persistent_memory_write"]), {})
    assert a["control"] == "proceed" and a["target"] == "memory_store"
    # target 변경 -> ask
    assert h.answer_task(_task("보내줘.", ["target_changed_after_turn"]), {})["control"] == "ask"
    # 외부 공유 정책 -> amend(redacted)
    a = h.answer_task(_task("보내줘.", ["external_share_policy"]), {})
    assert a["control"] == "amend" and a["content_scope"]["mode"] == "redacted"


def test_clause_overrides_records():
    """절(최신 지시)이 record보다 우선한다."""
    h = FinalHarness()
    t = _task("보내줘. 단, 바깥으로 보내지 말고 내부 상태 업데이트로 끝내라는 수정이 가장 최신이다.",
              ["external_share_policy"])
    assert h.answer_task(t, {})["control"] == "proceed"


if __name__ == "__main__":
    test_clause_local_update_full_skeleton()
    test_clause_invalidated_holds()
    test_clause_confirm_asks()
    test_no_clause_records_decide()
    test_clause_overrides_records()
    print("ok: class decoder tests passed")
