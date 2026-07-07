"""Iter 001 회귀 잠금: 마커 간접참조 focal 해석.

합성(synthetic) 입력으로 규칙 동작을 검증한다. dev 원본을 복사하지 않는다(과적합 방지).
경로: latest_phase -> phase_to_marker -> marker -> marker_to_ref -> ref_code -> object.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness import FinalHarness


def _task_with_markers(latest_phase: str) -> dict:
    return {
        "id": "synthetic_1",
        "prompt": "요청을 최신 route-binding으로 판단해줘.",
        "device_state": {
            "objects": [
                {"id": "obj_A", "type": "message", "attrs": {"ref_code": "WM-1000"}},
                {"id": "obj_B", "type": "message", "attrs": {"ref_code": "WM-2000"}},
                {"id": "obj_C", "type": "file", "attrs": {"ref_code": "WM-3000"}},
            ],
            "records": [
                {"id": "r1", "type": "focal_marker_refs", "value": {
                    "marker_to_ref": {"marker_alpha": "WM-1000", "marker_beta": "WM-2000", "marker_gamma": "WM-3000"}}},
                {"id": "r2", "type": "focal_resolution_trace", "value": {
                    "latest_phase": latest_phase,
                    "phase_to_marker": {"authority": "marker_alpha", "boundary": "marker_beta", "draft": "marker_gamma"}}},
            ],
        },
    }


def test_marker_resolution_follows_latest_phase():
    h = FinalHarness()
    # boundary -> marker_beta -> WM-2000 -> obj_B
    ans = h.answer_task(_task_with_markers("boundary"), {})
    assert ans["focal_id"] == "obj_B", ans["focal_id"]
    # authority -> marker_alpha -> WM-1000 -> obj_A
    ans = h.answer_task(_task_with_markers("authority"), {})
    assert ans["focal_id"] == "obj_A", ans["focal_id"]


def test_no_marker_falls_back_without_error():
    """마커 신호가 없으면 규칙이 개입하지 않고 기존 로직으로 fallback."""
    h = FinalHarness()
    task = {
        "id": "synthetic_2",
        "prompt": "hello world message",
        "device_state": {"objects": [{"id": "obj_X", "type": "message", "attrs": {"body": "hello world"}}], "records": []},
    }
    ans = h.answer_task(task, {})
    assert ans["focal_id"] == "obj_X", ans["focal_id"]


if __name__ == "__main__":
    test_marker_resolution_follows_latest_phase()
    test_no_marker_falls_back_without_error()
    print("ok: marker focal tests passed")
