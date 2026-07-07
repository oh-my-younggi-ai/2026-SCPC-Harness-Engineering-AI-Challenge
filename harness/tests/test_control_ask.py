"""Iter 002 회귀 잠금: decide_control ask 트리거 정제.

합성 입력. ambiguous_target/ambiguous_focal 라벨과 SLM requires_confirmation은
ask 신호가 아니다(실측상 판별력 없음). 진짜 미해소 신호(amount_changed 등)만 ask.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness import FinalHarness


def _task(record_types: list[str]) -> dict:
    return {
        "id": "syn_ctl",
        "prompt": "share it",
        "device_state": {
            "objects": [{"id": "obj_A", "type": "message", "attrs": {"recipient": "hana"}}],
            "records": [{"id": f"r{i}", "type": t, "value": {}} for i, t in enumerate(record_types)],
        },
    }


def test_ambiguous_label_alone_does_not_force_ask():
    h = FinalHarness()
    # ambiguous_target 라벨만 있고 진짜 미해소 신호 없음 -> ask 아님
    ans = h.answer_task(_task(["ambiguous_target"]), {})
    assert ans["control"] != "ask", ans["control"]


def test_genuine_signal_triggers_ask():
    h = FinalHarness()
    ans = h.answer_task(_task(["amount_changed"]), {})
    assert ans["control"] == "ask", ans["control"]
    ans = h.answer_task(_task(["target_changed_after_turn"]), {})
    assert ans["control"] == "ask", ans["control"]


def test_security_still_holds():
    h = FinalHarness()
    ans = h.answer_task(_task(["security_alert"]), {})
    assert ans["control"] == "hold", ans["control"]


if __name__ == "__main__":
    test_ambiguous_label_alone_does_not_force_ask()
    test_genuine_signal_triggers_ask()
    test_security_still_holds()
    print("ok: control ask tests passed")
