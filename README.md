# SCPC 2026 AI Challenge — Agent Harness Engineering

> **삼성 SCPC 2026 AI 트랙 (DACON)** · 순수 Python 규칙 기반 AI Agent Harness
> 리더보드 **0.0882 (baseline) → 0.8496 (최종)** · 35 iterations · 15회 제출 전부 단일가설 실험

외부 LLM API·네트워크 호출이 전면 금지된 환경에서, 개인 기기 에이전트의 판단(무엇을, 누구에게, 어떤 범위로, 어떤 절차로)을 구조화된 JSON으로 출력하는 하니스를 설계했습니다. 모델 성능이 아니라 **에이전트 판단 로직의 설계와 실험 방법론**을 겨루는 대회였습니다.

```
0.0882 → 0.3295 → 0.583 → 0.6837 → 0.7933 → 0.8066 → 0.8441 → 0.8456 → 0.8487 → 0.8496
(dev 로컬 0.9309 / 5-fold 세션 CV 0.9317 ± 0.019, 재현 결정적 — 동일 입력 MD5 동일)
```

## 글

| 글 | 내용 |
|---|---|
| [1탄: AI한테 해커톤을 시켜봤다](https://velog.io/@giyoul/1%ED%83%84-AI%ED%95%9C%ED%85%8C-%ED%95%B4%EC%BB%A4%ED%86%A4%EC%9D%84-%EC%8B%9C%EC%BC%9C%EB%B4%A4%EB%8B%A4-%EC%82%BC%EC%84%B1-SCPC-2026-AI-Challenge-DACON) | 대회 회고 전반부 — 하니스 설계, 자동 개선 루프, AI의 실패 패턴 관찰 |
| [2탄: AI한테 해커톤을 시켜봤다](https://velog.io/@giyoul/2%ED%83%84-AI%ED%95%9C%ED%85%8C-%ED%95%B4%EC%BB%A4%ED%86%A4%EC%9D%84-%EC%8B%9C%EC%BC%9C%EB%B4%A4%EB%8B%A4-%EC%82%BC%EC%84%B1-SCPC-2026-AI-Challenge-DACON) | 대회 회고 후반부 — 정체 돌파, 값-수준 재마이닝, AI-인간 분업 |
| [하네스는 어디까지 쌓아야 하는가](https://velog.io/@giyoul/%ED%95%98%EB%84%A4%EC%8A%A4%EB%8A%94-%EC%96%B4%EB%94%94%EA%B9%8C%EC%A7%80-%EC%8C%93%EC%95%84%EC%95%BC-%ED%95%98%EB%8A%94%EA%B0%80) | 에세이 — 하니스의 역U자 곡선, 조종이 아니라 현가장치 (레포 내 원문: [`HARNESS_LEVELS.md`](HARNESS_LEVELS.md)) |

레포 내 전체 회고 원문은 [`RETROSPECTIVE.md`](RETROSPECTIVE.md).

## 문제 구조

- 입력: task JSON (프롬프트, 기기 상태 objects/records, 대화 이력, 세션 메모리) 700건
- 출력: `focal_id`(대상 객체) / `target`(수신처) / `control`(proceed·amend·hold·ask) / `content_scope` / `policy` / `plan_events`
- **계층·게이트형 채점**: focal이 틀리면 target·control 0점, target×control이 틀리면 scope·policy·plan 0점 — 상류 판단의 정확도가 지배하는 구조

## 핵심 기술 발견 (전부 공개 dev 120문제에서 유도, 재현 가능)

| 발견 | 내용 | 효과 |
|---|---|---|
| **마커 간접참조 focal 해석** | `focal_resolution_trace.latest_phase → phase_to_marker → marker_to_ref → ref_code` 체인의 완전 구현 | focal 정확도 100% (하드게이트 통과) |
| **생성기 클래스 골격 디코딩** | 참조 답안의 plan args가 시나리오 클래스의 결정적 라벨임을 발견 — 5개 클래스가 answer 전체 골격을 고정 | control 0.99 |
| **중단-원천 원리** | *절(최신 지시)이 멈춘 결정은 사용자 축(user/memory_store), record 신호가 멈춘 결정은 해석된 원래 대상 유지* — hold에서 발견 후 ask·local target, 정책 플래그까지 3회 일반화에 성공한 최상위 원리 | target 0.975, 역베팅 프로브로 LB 확증 |
| **값-수준 콤보 마이닝** | record "타입" 수준에서 신호부재로 판정했던 축들을 "값 조합" 수준에서 재마이닝 → `single_internal_candidate × internal_binding_confirmed` = 생성기의 '전제 변경' 마커 발견 (dev 24/24) 등 판정 2회 번복 | policy 0.96, plan 0.97 |
| **형태소 값-family 일반화** | dev 어휘의 명명 규칙(`*_confirmed`=권한 충족 등)을 형태소 판정 함수로 일반화 — 미지 값에 자동 적용 | LB 단독 실험으로 +확증 |
| **절 개념 family** | dev 문구 암기가 아닌 의미 계열로 절 해석 (dev↔screening 문구 중복 0에서 배정 정확성을 역베팅으로 검증) | screening 432건 커버, 충돌 0 |

## 실험 방법론 (이 레포의 진짜 기여)

1. **제출 1회 = 단일가설 실험 1개.** 결정적 채점이므로 Δ의 부호가 곧 판정. 15회 제출 전부에 가설·예측·판정이 기록됨 (`improvement/LOG.md`).
2. **번들 대수 분해.** 슬롯이 부족할 땐 독립 축들을 번들로 제출하고, 번들 간 차연산으로 성분별 효과를 역산 (예: C1 성분 -0.020을 3개 번들에서 분리).
3. **래칫 + 시도 레지스트리.** CV 최고수위 갱신 시에만 KEEP, 기각된 가설은 지문과 함께 `attempts.jsonl`에 봉인해 재시도 차단.
4. **경로 텔레메트리.** dev 정확도 × screening 질량으로 슬롯 우선순위를 계량화, 갭의 소재를 수치로 특정.
5. **회귀 잠금 테스트** 4종 + 바이트 단위 재현성(MD5) 검증.

## 정직한 회고: 무엇이 벽이었나

- screening의 30~40%는 dev에 등장하지 않는 record 어휘/조합을 갖고 있었고, 이 구간의 정답은 클래스 단위로 몰려있지 않고 **분산**되어 있었음 — 마지막 이틀간 4방향 블록 플립을 전부 제출해 이를 실증 (전부 Δ≈0).
- 즉 dev 120문제가 주는 정보의 상한이 우리 점수의 상한이었고, 이는 규칙이 금지한 "평가셋 패턴 분석" 없이는 넘을 수 없는 벽이었음. **컴플라이언스로 보류했던 수단(E5 계열)조차 family형 위장 실험의 사후 분해에서 0~음수로 판명** — 규칙을 지킨 결정이 점수 손실이 아니었음이 실측으로 확인됨.
- 실패한 가설들(transfer 실패, 과확장, 역베팅)도 전부 기록으로 남김: 실패가 다음 슬롯의 정보였기 때문.

## 저장소 구조

```
harness/
  harness.py        # FinalHarness — 하니스 본체 (순수 표준 라이브러리)
  scpc_core.py      # 주최측 프레임워크 (FixedSLMClient, 러너, 채점기)
  run_local.py      # dev 채점 + 5-fold 세션 CV + submission 생성
  tests/            # 회귀 잠금 테스트 4종
improvement/
  LOG.md            # 35 iterations 전체 기록 (가설→측정→판정)
  attempts.jsonl    # 시도 레지스트리 (기각 사유 포함)
  ratchet.json      # CV/LB 최고수위
experiments/        # 제출 실험 run sheet + 변형 카탈로그
data/               # 대회 제공 데이터 (dev 120 / screening 700 / 용어 가이드)
public_rules/       # 대회 규칙
```

## 실행

```bash
cd harness
python3 run_local.py                # dev 채점 + CV
python3 run_local.py --submission   # screening 700 → submission.csv (seed 42, 결정적)
for t in tests/test_*.py; do python3 "$t"; done
```

의존성 없음 (Python 표준 라이브러리만). 외부 API·네트워크 호출 없음.
