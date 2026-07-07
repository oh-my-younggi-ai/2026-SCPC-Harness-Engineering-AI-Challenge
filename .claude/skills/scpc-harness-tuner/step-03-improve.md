---
---

# Step 3: Improve — 규칙 모듈 + 단위 테스트로 구현

개선은 "FinalHarness를 대충 손보기"가 아니라 **규칙 모듈 1개 + 단위 테스트 1개**를 만드는 것이다(③). 이래야 고도화가 누적 코드 자산이 된다.

## RULES

- 출력 언어는 항상 `{communication_language}`.
- **승인된 후보 하나만** 구현한다. 다른 개선을 끼워넣지 않는다.
- **하드코딩 금지 게이트**: 특정 task_id/session_id 리터럴, 공개 예시 문장·record 값 암기, dev 전용 lookup table이 있으면 **중단하고 일반화된 규칙으로 다시 짠다**.
- `slm.py`, `runner.py`, `scorer.py`, `io_utils.py`는 건드리지 않는다(주최 framework 정본). 개선은 `{rules_dir}/`와 `harness.py`의 얇은 엔진, `{tests_dir}/`에만.

## INSTRUCTIONS

1. **스냅샷 보존**: 변경 전 `harness.py`(및 관련 rules)를 `{track_dir}/snapshots/preNNN/`로 복사(NNN=다음 iter). revert용.

2. **규칙 모듈 작성/수정** — 점진적 전환:
   - 이 신호를 다루는 모듈이 없으면 `{rules_dir}/<signal>.py`를 새로 만든다. 순수 함수 형태 권장: 입력 task/record/session/evidence → 판단 조각 반환(예: control 후보, scope 조정, plan 이벤트 조각). **immutable**: 입력을 제자리 변경하지 말고 새 값 반환.
   - 해당 영역 로직이 아직 FinalHarness 본문에 있으면, **이번에 건드리는 부분만** 규칙 모듈로 추출하고 FinalHarness는 그 모듈을 호출하도록 바꾼다. 한 번에 전체를 쪼개지 않는다.
   - 규칙은 **신호→판단**으로 표현: "record에 `consent.status=='revoked'`면 control=hold, plan에서 guard를 dispatch보다 앞에 둔다".
   - FinalHarness 엔진에 이 규칙을 **정해진 순서 위치**에 등록한다(순서가 plan 채점에 영향).

3. **단위 테스트 작성** (④의 축적): `{tests_dir}/test_<signal>.py`에 이 규칙의 동작을 **합성(synthetic) 입력**으로 검증하는 테스트를 추가한다. dev 원본을 그대로 복붙하지 말고(과적합), 규칙이 반응해야 할 **최소 신호를 담은 인공 task**로 작성한다. 이 테스트는 앞으로 회귀를 막는 잠금장치가 된다.

4. **구문/단위 확인**: `python -c "import harness"` 와 새 테스트 `pytest {tests_dir}/test_<signal>.py`(또는 unittest)가 통과하는지 본다.

## NEXT

Read fully and follow `./step-04-evaluate.md`
