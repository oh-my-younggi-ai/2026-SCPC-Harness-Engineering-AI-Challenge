"""Iter 011 회귀 잠금: visible_history 선택 서사 focal 해석 (합성 입력)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness import FinalHarness


def _task(vh_lines: list[str]) -> dict:
    return {
        "id": "syn",
        "prompt": "그 자료를 처리해줘.",
        "visible_history": [{"turn": i, "summary": s} for i, s in enumerate(vh_lines)],
        "device_state": {
            "objects": [
                {"id": "obj_A", "type": "message", "attrs": {"ref_code": "WM-1000"}},
                {"id": "obj_B", "type": "message", "attrs": {"ref_code": "WM-2000"}},
                {"id": "obj_C", "type": "file", "attrs": {"ref_code": "WM-3000"}},
            ],
            "records": [],
        },
    }


def test_bound_ordinal_not_fooled_by_excluded_ordinals():
    """배제 서수(첫 번째와 세 번째)가 함께 나와도 '~만 확정'에 결합된 서수를 고른다."""
    h = FinalHarness()
    t = _task(["후보 참조는 순서대로 WM-1000, WM-2000, WM-3000이다. "
               "첫 번째와 세 번째 후보는 보류 후보로 남겼고, 두 번째 후보만 현재 처리 대상으로 확정했다."])
    assert h.answer_task(t, {})["focal_id"] == "obj_B"


def test_designation_variants():
    h = FinalHarness()
    for line, want in [
        ("작업 메모리에는 후보 WM-1000와 최종 승인 후보 WM-3000가 함께 남아 있다.", "obj_C"),
        ("최근 작업 메모리에서 실제 처리할 ref는 WM-2000로 고정됐다.", "obj_B"),
        ("메모리 검토 결과 WM-3000만 통과 항목이고 WM-1000, WM-2000는 배제됐다.", "obj_C"),
        ("WM-1000와 WM-2000, WM-3000가 언급됐지만 승인 상태가 유지된 참조는 WM-1000이다.", "obj_A"),
    ]:
        assert h.answer_task(_task([line]), {})["focal_id"] == want, line


def test_valid_item_ordinal():
    h = FinalHarness()
    t = _task(["나열된 참조 WM-1000, WM-2000, WM-3000 중 정정 이후 유효한 항목은 두 번째다."])
    assert h.answer_task(t, {})["focal_id"] == "obj_B"


if __name__ == "__main__":
    test_bound_ordinal_not_fooled_by_excluded_ordinals()
    test_designation_variants()
    test_valid_item_ordinal()
    print("ok: history focal tests passed")
