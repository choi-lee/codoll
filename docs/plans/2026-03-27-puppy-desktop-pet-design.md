# Puppy - macOS Desktop Pet App Design

## Overview

macOS 바탕화면에서 돌아다니는 데스크톱 펫 앱. 강아지 '츄' 스타일의 흑백 포메라니안 캐릭터가 화면 위를 돌아다니며, 스케줄/리마인더를 말풍선으로 알려준다.

## Tech Stack

- Swift + AppKit (네이티브)
- CoreGraphics 벡터 드로잉
- LSUIElement (메뉴바 상주, Dock 아이콘 없음)

## Character Design

- 츄 스타일 심플 벡터 일러스트
- 흑백 포메라니안: 머리 위 검정, 얼굴/가슴 하양
- 삼각 귀(검정), 까만 코, 동그란 눈, 입 벌리고 혀 내민 웃는 표정
- 풍성한 목 주변 흰색 러프, 위로 말린 꼬리

## Animation States

| State    | Description                          | Trigger            |
| -------- | ------------------------------------ | ------------------ |
| idle     | 헥헥거림 (혀 위아래, 몸 살짝 바운스) | 기본 상태          |
| walking  | 좌우 이동 (다리 교차, 바운스)        | 랜덤 타이머        |
| running  | 빠르게 이동 (큰 바운스)              | 랜덤 (낮은 확률)   |
| sitting  | 앉아서 주위 둘러봄                   | idle에서 랜덤 전환 |
| sleeping | 눈 감고 ZZZ                          | 장시간 미인터랙션  |
| alert    | 귀 쫑긋 + 말풍선                     | 스케줄 트리거      |
| happy    | 꼬리 흔들기 + 점프                   | 클릭               |

## Schedule System

- Schedule model: id, title, time, repeatType, customDays, isEnabled, category
- Categories: water, medicine, task, custom
- Presets: 물마시기(2h간격), 약먹기(매일), 주간보고(매주), 커스텀
- JSON file storage + UserDefaults

## Alert Flow

1. ScheduleManager 매 분 체크
2. 강아지 alert 상태 전환 + 화면 중앙 이동
3. 말풍선 표시
4. 클릭 시 완료 → happy 상태 / 무시 시 30초 후 복귀

## Settings Window

- 스케줄 탭: 할 일 CRUD + 토글
- 강아지 탭: 활동 범위 모드 (하단만/전체화면), 이동 속도
- 일반 탭: 자동 시작, 알림 사운드

## Interaction (MVP)

- 클릭: 반응 (짖기, 꼬리흔들기)
- 드래그: 위치 이동

## File Structure

```
Puppy/
├── App/          - PuppyApp.swift, AppDelegate.swift
├── Window/       - PuppyWindow.swift, PuppyContentView.swift
├── Character/    - PuppyRenderer.swift, PuppyAnimator.swift, PuppyState.swift
├── Schedule/     - Schedule.swift, ScheduleManager.swift, ScheduleStore.swift
├── Views/        - BubbleView.swift, SettingsWindow.swift, ScheduleListView.swift, ScheduleEditView.swift
├── StatusBar/    - StatusBarController.swift
└── Info.plist
```

## Implementation Order

1. 프로젝트 셋업 + 투명 윈도우 + 메뉴바 아이콘
2. 강아지 벡터 드로잉
3. 애니메이션 상태 머신
4. 마우스 인터랙션
5. 스케줄 데이터 모델 + 저장/로드
6. 설정 윈도우
7. 알림 시스템 (말풍선)
