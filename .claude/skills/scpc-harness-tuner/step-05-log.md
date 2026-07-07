---
---

# Step 5: Log — 개선 기록 · 상태 갱신 · 다음 반복

진짜 상태는 `{coverage}`·`{attempts}`·`{ratchet}`·`{backlog}`가 쥔다(step-02/04에서 갱신됨). LOG는 사람이 읽는 서사 요약이다. 여기서 "무엇을 바꿨고 점수가 어떻게 달라졌는지"를 사람 친화적으로 남긴다.

## RULES

- 출력 언어는 항상 `{communication_language}`.
- KEEP이든 REVERT든 **모든 시도를 기록**한다. 실패 기록이 다음 진단을 똑똑하게 만든다.

## INSTRUCTIONS

### 1. LOG 항목 추가

`{log_file}`에 `./templates/log-entry.md` 형식으로 새 Iter 항목을 **append**한다. 반드시 포함:

- Iter 번호 · 날짜 · [KEEP|REVERT]
- **가설** / **지문**(신규성 근거) / **catalog 항목 id**
- **변경 내용**: 어떤 규칙 모듈(`{rules_dir}/…`)을 추가·수정했고 어떤 신호→판단 규칙인지
- **점수 변화**: overall before→after (전체 / CV 일반화 평균) + 각 axes
- **task 영향**: 고침 +N / 깨짐 −M (순 ±K)
- **회귀 / 테스트**: 축적 테스트 결과, 래칫 통과 여부
- **결정** + 이유(특히 CV 일반화·래칫이 어떻게 움직였는지)
- **다음 후보**: backlog 최우선(있으면)

### 2. LOG 헤더 지표 갱신

LOG 상단 표를 갱신: 현재 overall(전체)·CV 일반화 평균, **coverage %(handled/전체)**, 활성 규칙 수, 누적 반복 수, 최고 기록.

### 3. 백로그 정리

`{backlog}`에서 처리한 후보를 제거하고, 이번에 새로 관찰된 catalog 항목/회귀를 반영한다(상태는 이미 step-02/04에서 갱신됨 — 여기선 서사적 정리).

### 4. 사람에게 요약 보고

한 줄 결론(예: "consent_revoked 규칙 추가 → overall +0.045, CV +0.03, coverage 24%→27%, KEEP") + 델타 표(overall 전체·CV 일반화, 주요 axes) + 누적 진척(Iter 000 대비 현재, coverage % 추이).

### 5. Consolidation 시점 판단 (⑧ — `{compose_every}`반복마다 자동)

`{attempts}`의 누적 KEEP 반복 수를 센다. **`{compose_every}`(=3)의 배수에 도달했으면** 다음은 일반 반복이 아니라 **consolidation**이다: 사람에게 "3반복 경과 → 강점 재조합(step-06)을 돌립니다"라고 알리고, 이어가면 read fully and follow `./step-06-consolidate.md`.

### 6. 다음 반복 안내

- consolidation 시점이 아니면: 계속하려면 다시 step-01부터. 사람이 "다음/계속" 등으로 이어가면 read fully and follow `./step-01-measure.md`.
- 제출: `python {code_dir}/run_local.py --submission` → `submission.csv`(1일 5회, meta.seed=42).
- 여기서 **HALT**.

## 지속성 참고

이 루프는 catalog가 소진되고 래칫이 더 안 오를 때까지 계속된다. coverage %와 ratchet high-water가 매 KEEP마다 오르므로 **진척은 단조 증가**하고, attempts 게이트가 **반복을 원천 차단**한다. focal이 끝나면 진단이 target→control→scope→policy→plan→구조 개선으로 자연히 이동한다.
