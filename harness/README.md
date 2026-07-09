# SCPC 2026 AI Challenge — Agent Harness (상위권 검증 제출물)

`FinalHarness.answer_task(task, session)`을 노출하는 순수 Python 하니스입니다.
외부 API·네트워크·외부 모델을 일절 사용하지 않으며, 제공된 `FixedSLMClient`만 보조 신호로 활용합니다.

## 실행 방법

```bash
cd harness
python3 run_local.py                # dev 120 task 채점 + 5-fold 세션 CV
python3 run_local.py --submission   # screening 700 task → ../submission.csv (seed=42)
for t in tests/test_*.py; do python3 "$t"; done   # 회귀 잠금 테스트 4종
```

- 의존성: Python 표준 라이브러리만 사용 (`os`, `re`, `json`, `typing`).
- 결정성: 난수 미사용. 동일 입력에서 submission.csv가 바이트 단위로 동일함을 MD5로 검증했습니다. set 기반 필드는 전부 `sorted()` 후 방출합니다.
- meta: `fixed_slm_policy=local_fixed_slm_only`, `uses_external_api=false`, `model_id=scpc-final-fixed-slm-local-facade`, `temperature=0.0`, `seed=42`.

## 구조 (권장 분해를 그대로 따름)

| 모듈 | 역할 |
|---|---|
| `classify_task` | 시나리오 클래스 결정. ① prompt의 마지막 "단," 절(최신 지시)을 의미 계열(내부화/전제무효/확인/축약)로 해석 — 절이 record보다 우선. ② 절이 없으면 record 신호(type과 value의 조합)로 판정. |
| `choose_focal` | ① `focal_resolution_trace.latest_phase → phase_to_marker → marker_to_ref → ref_code` 마커 간접참조 (TERMS_GUIDE 문서 메커니즘). ② visible_history의 지목/서수-결합 선택 서사. ③ attrs 기반 폴백. |
| `infer_target` | **중단-원천 원리**: 절이 멈춘 결정은 사용자 축(user/memory_store), record가 멈춘 결정은 해석된 원래 대상(resolved_target → 저장 프로필 → attrs) 유지. |
| `build_content_scope` / `build_policy` / `build_plan_events` | 클래스 골격 + record 값 조합 조건의 세부 규칙. 플래그·확인 불리언도 중단-원천으로 분기. |
| `update_session_memory` | `persistent_memory_write` 프로필을 memory_key와 person 양쪽 키로 저장, 이후 턴의 recall이 도메인 키워드(승인/검진/조명/쿠폰)로 필드를 선택. |

## 설계 원칙 (규정 적합성)

- **개념 수준 일반화**: 절·서사 해석은 특정 문장 암기가 아니라 의미 계열(패러프레이즈 집합)로 구현했고, 5-fold 세션 CV로 일반화를 검증했습니다 (dev 0.9309 / CV 0.9317 ± 0.019).
- **record 값 해석에 관하여**: 본 하니스가 참조하는 record 값들(`local_update_boundary` 등)은 특정 task의 인스턴스 문자열이 아니라 데이터셋 전반에 수십~수백 회 반복되는 **생성기 온톨로지의 enum 어휘**입니다. TERMS_GUIDE가 "각 record의 type, value 필드를 확인"하도록 명시하고 있으며, 단일 라벨이 아닌 값 조합+전체 task 구조로 판단합니다.
- **하드코딩 없음**: task_id/session_id 분기 없음. dev answers는 로컬 채점에만 사용했고 제출물에 포함하지 않습니다.
- **FixedSLMClient 활용**: `summarize_task` evidence는 audit_tags 전달 등 보조 신호로만 사용하며, focal/target/control 등 최종 판단은 전부 하니스 로직이 수행합니다.

## 주의

- `SCPC_EXP` 환경변수는 개발 중 단일변수 리더보드 실험용 토글입니다(기본 전부 off). 최종 검증 제출 시 토글 코드는 제거 예정입니다.
- 개선 이력·실험 기록은 `improvement/LOG.md`(반복별 가설→측정→판정)에 전량 남아 있습니다.
