# Puppy Desktop Pet - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** macOS 바탕화면에서 츄(흑백 포메라니안) 캐릭터가 돌아다니며 스케줄 리마인더를 말풍선으로 알려주는 데스크톱 펫 앱

**Architecture:** Swift Package Manager 기반 macOS AppKit 앱. LSUIElement로 메뉴바 상주. 투명 NSWindow 위에 CoreGraphics 벡터 캐릭터를 프레임 애니메이션. 스케줄은 JSON 파일로 저장하고 타이머로 체크.

**Tech Stack:** Swift 6, AppKit, CoreGraphics, Swift Package Manager (no Xcode)

**Build:** `swift build && .build/debug/Puppy`

---

### Task 1: SPM 프로젝트 셋업 + 빈 윈도우 앱 실행

**Files:**
- Create: `Package.swift`
- Create: `Sources/Puppy/main.swift`
- Create: `Sources/Puppy/App/AppDelegate.swift`

**Step 1: Package.swift 생성**

```swift
// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "Puppy",
    platforms: [.macOS(.v13)],
    targets: [
        .executableTarget(
            name: "Puppy",
            path: "Sources/Puppy",
            linkerSettings: [
                .linkedFramework("AppKit"),
                .linkedFramework("CoreGraphics")
            ]
        )
    ]
)
```

**Step 2: main.swift - NSApplication 부트스트랩**

```swift
import AppKit

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.run()
```

**Step 3: AppDelegate.swift - 기본 앱 델리게이트**

```swift
import AppKit

class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory) // LSUIElement 대체 - Dock 아이콘 숨김
        print("Puppy app launched!")
    }
}
```

**Step 4: 빌드 & 실행 확인**

Run: `swift build 2>&1`
Expected: Build Succeeded

Run: `swift build && timeout 2 .build/debug/Puppy 2>&1 || true`
Expected: "Puppy app launched!" 출력

**Step 5: Commit**

```bash
git add Package.swift Sources/
git commit -m "feat: initial SPM project setup with AppKit app bootstrap"
```

---

### Task 2: 투명 플로팅 윈도우

**Files:**
- Create: `Sources/Puppy/Window/PuppyWindow.swift`
- Modify: `Sources/Puppy/App/AppDelegate.swift`

**Step 1: PuppyWindow.swift - 투명 항상-위 윈도우**

```swift
import AppKit

class PuppyWindow: NSWindow {
    init() {
        let screenFrame = NSScreen.main?.frame ?? NSRect(x: 0, y: 0, width: 1920, height: 1080)
        super.init(
            contentRect: screenFrame,
            styleMask: .borderless,
            backing: .buffered,
            defer: false
        )

        self.isOpaque = false
        self.backgroundColor = .clear
        self.hasShadow = false
        self.level = .floating
        self.collectionBehavior = [.canJoinAllSpaces, .stationary]
        self.ignoresMouseEvents = false
    }
}
```

**Step 2: AppDelegate에서 윈도우 표시**

AppDelegate에 PuppyWindow 생성 및 표시 코드 추가.

**Step 3: 빌드 확인**

Run: `swift build 2>&1`
Expected: Build Succeeded

**Step 4: Commit**

```bash
git add Sources/
git commit -m "feat: add transparent floating window"
```

---

### Task 3: 메뉴바 아이콘

**Files:**
- Create: `Sources/Puppy/StatusBar/StatusBarController.swift`
- Modify: `Sources/Puppy/App/AppDelegate.swift`

**Step 1: StatusBarController.swift**

```swift
import AppKit

class StatusBarController {
    private var statusItem: NSStatusItem

    init() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        if let button = statusItem.button {
            button.title = "🐾"
        }
        setupMenu()
    }

    private func setupMenu() {
        let menu = NSMenu()
        menu.addItem(NSMenuItem(title: "Settings...", action: #selector(openSettings), keyEquivalent: ","))
        menu.addItem(NSMenuItem.separator())
        menu.addItem(NSMenuItem(title: "Quit Puppy", action: #selector(quit), keyEquivalent: "q"))
        statusItem.menu = menu
    }

    @objc func openSettings() {
        // TODO: open settings window
    }

    @objc func quit() {
        NSApp.terminate(nil)
    }
}
```

**Step 2: AppDelegate에 StatusBarController 연결**

**Step 3: 빌드 확인 - 메뉴바에 🐾 아이콘 표시, Quit으로 종료 가능**

**Step 4: Commit**

```bash
git add Sources/
git commit -m "feat: add menu bar icon with quit option"
```

---

### Task 4: 강아지 상태 머신

**Files:**
- Create: `Sources/Puppy/Character/PuppyState.swift`

**Step 1: PuppyState.swift - 애니메이션 상태 enum + 상태 머신**

```swift
import Foundation

enum PuppyState: String, CaseIterable {
    case idle
    case walking
    case running
    case sitting
    case sleeping
    case alert
    case happy
}

enum FacingDirection {
    case left, right
}

class PuppyStateMachine {
    var currentState: PuppyState = .idle
    var facingDirection: FacingDirection = .right
    var stateTimer: TimeInterval = 0
    var stateDuration: TimeInterval = 0

    func update(deltaTime: TimeInterval) -> Bool {
        stateTimer += deltaTime
        if stateTimer >= stateDuration {
            return true // state expired
        }
        return false
    }

    func transitionToRandom() {
        let rand = Double.random(in: 0...1)
        switch rand {
        case 0..<0.35: transition(to: .idle)
        case 0.35..<0.6: transition(to: .walking)
        case 0.6..<0.75: transition(to: .running)
        case 0.75..<0.9: transition(to: .sitting)
        default: transition(to: .sleeping)
        }
    }

    func transition(to state: PuppyState) {
        currentState = state
        stateTimer = 0
        switch state {
        case .idle: stateDuration = Double.random(in: 3...6)
        case .walking: stateDuration = Double.random(in: 3...8)
        case .running: stateDuration = Double.random(in: 2...4)
        case .sitting: stateDuration = Double.random(in: 4...8)
        case .sleeping: stateDuration = Double.random(in: 8...15)
        case .alert: stateDuration = 30
        case .happy: stateDuration = 2
        }
        if state == .walking || state == .running {
            facingDirection = Bool.random() ? .left : .right
        }
    }
}
```

**Step 2: 빌드 확인**

**Step 3: Commit**

```bash
git add Sources/
git commit -m "feat: add puppy state machine with animation states"
```

---

### Task 5: 강아지 벡터 렌더러 (CoreGraphics)

**Files:**
- Create: `Sources/Puppy/Character/PuppyRenderer.swift`

**Step 1: PuppyRenderer.swift - 츄 스타일 벡터 드로잉**

CoreGraphics를 사용해 츄(흑백 포메라니안)를 벡터로 그리는 렌더러.
상태별로 다른 포즈를 그림. 캐릭터 크기는 약 80x80pt.

주요 파트:
- `drawBody(context:state:frame:)` - 둥근 몸체 (흰색 하단, 검은색 상단)
- `drawHead(context:state:frame:)` - 둥근 머리 + 귀 + 얼굴
- `drawLegs(context:state:frame:)` - 상태별 다리 위치
- `drawTail(context:state:frame:)` - 위로 말린 꼬리
- `drawFace(context:state:frame:)` - 눈, 코, 입, 혀

각 상태별 프레임 카운터에 따라 위치/회전값 변경으로 애니메이션 표현.

**Step 2: 빌드 확인**

**Step 3: Commit**

```bash
git add Sources/
git commit -m "feat: add CoreGraphics puppy renderer with Chu-style design"
```

---

### Task 6: 강아지 애니메이터 + 메인 뷰

**Files:**
- Create: `Sources/Puppy/Character/PuppyAnimator.swift`
- Create: `Sources/Puppy/Window/PuppyContentView.swift`
- Modify: `Sources/Puppy/App/AppDelegate.swift`

**Step 1: PuppyAnimator.swift - 위치 이동 + 프레임 업데이트 로직**

프레임마다:
1. 상태 머신 업데이트
2. walking/running 시 x좌표 이동 (walking: 30pt/s, running: 80pt/s)
3. 화면 경계 도달 시 방향 전환
4. 상태 만료 시 랜덤 전환
5. 활동 범위 모드에 따른 y좌표 제한

**Step 2: PuppyContentView.swift - NSView 서브클래스**

- `CVDisplayLink` 또는 `Timer`로 60fps 업데이트
- 매 프레임 PuppyAnimator 업데이트 → PuppyRenderer로 그리기
- `setNeedsDisplay` 호출로 화면 갱신
- 강아지 영역만 hitTest 통과

**Step 3: AppDelegate에서 PuppyContentView를 PuppyWindow에 연결**

**Step 4: 빌드 & 실행 - 화면 하단에서 강아지가 돌아다니는 것 확인**

**Step 5: Commit**

```bash
git add Sources/
git commit -m "feat: add animator and content view - puppy walks on screen"
```

---

### Task 7: 마우스 인터랙션

**Files:**
- Modify: `Sources/Puppy/Window/PuppyContentView.swift`
- Modify: `Sources/Puppy/Window/PuppyWindow.swift`

**Step 1: 클릭 감지 + happy 상태 전환**

PuppyContentView에서:
- `hitTest`: 마우스 위치가 강아지 영역 안인지 체크, 밖이면 nil 반환 (클릭 통과)
- `mouseDown`: 강아지 클릭 시 happy 상태 전환
- `mouseDragged`: 강아지 드래그로 위치 이동

PuppyWindow에서:
- `ignoresMouseEvents = false` 유지하되, 투명 영역은 클릭 통과하도록 처리

**Step 2: 빌드 & 확인 - 강아지 클릭 시 반응, 드래그로 이동**

**Step 3: Commit**

```bash
git add Sources/
git commit -m "feat: add click reaction and drag interaction"
```

---

### Task 8: 스케줄 데이터 모델 + 저장/로드

**Files:**
- Create: `Sources/Puppy/Schedule/Schedule.swift`
- Create: `Sources/Puppy/Schedule/ScheduleStore.swift`

**Step 1: Schedule.swift - Codable 데이터 모델**

```swift
import Foundation

enum RepeatType: String, Codable, CaseIterable {
    case once, daily, weekdays, weekly, custom, interval
}

enum ScheduleCategory: String, Codable, CaseIterable {
    case water, medicine, task, custom
}

struct Schedule: Codable, Identifiable {
    var id: UUID
    var title: String
    var hour: Int
    var minute: Int
    var repeatType: RepeatType
    var customDays: [Int] // 1=Sun, 2=Mon, ...7=Sat
    var intervalMinutes: Int? // for .interval type (e.g. water every 120 min)
    var isEnabled: Bool
    var category: ScheduleCategory
}
```

**Step 2: ScheduleStore.swift - JSON 파일 기반 CRUD**

- 저장 경로: `~/Library/Application Support/Puppy/schedules.json`
- `load() -> [Schedule]`
- `save(_ schedules: [Schedule])`
- 기본 프리셋 생성 (첫 실행 시)

**Step 3: 빌드 확인**

**Step 4: Commit**

```bash
git add Sources/
git commit -m "feat: add schedule data model and JSON file store"
```

---

### Task 9: 스케줄 매니저 (알림 트리거)

**Files:**
- Create: `Sources/Puppy/Schedule/ScheduleManager.swift`

**Step 1: ScheduleManager.swift - 타이머 기반 스케줄 체크**

- 60초 간격 Timer로 현재 시간과 스케줄 매칭
- 매칭 시 콜백(클로저)으로 알림 트리거
- 오늘 이미 트리거된 스케줄 추적 (중복 알림 방지)
- interval 타입: 마지막 알림 시간 기준 계산

**Step 2: 빌드 확인**

**Step 3: Commit**

```bash
git add Sources/
git commit -m "feat: add schedule manager with timer-based trigger"
```

---

### Task 10: 말풍선 뷰

**Files:**
- Create: `Sources/Puppy/Views/BubbleView.swift`
- Modify: `Sources/Puppy/Window/PuppyContentView.swift`
- Modify: `Sources/Puppy/Character/PuppyAnimator.swift`

**Step 1: BubbleView.swift - 말풍선 CoreGraphics 드로잉**

- 둥근 사각형 배경 (흰색, 그림자)
- 아래 삼각형 꼬리 (강아지를 가리킴)
- 텍스트 렌더링 (NSAttributedString)
- 카테고리별 아이콘 (💧💊📝✏️)

**Step 2: PuppyContentView + PuppyAnimator 연동**

- 알림 트리거 시: 강아지 alert 상태 + 말풍선 표시
- 말풍선 클릭 시: 완료 처리 + happy 상태
- 30초 후 자동 사라짐

**Step 3: 빌드 & 확인 - 스케줄 시간에 말풍선 등장**

**Step 4: Commit**

```bash
git add Sources/
git commit -m "feat: add speech bubble view with schedule alerts"
```

---

### Task 11: 설정 윈도우

**Files:**
- Create: `Sources/Puppy/Views/SettingsWindow.swift`
- Create: `Sources/Puppy/Views/ScheduleListView.swift`
- Create: `Sources/Puppy/Views/ScheduleEditView.swift`
- Modify: `Sources/Puppy/StatusBar/StatusBarController.swift`
- Modify: `Sources/Puppy/App/AppDelegate.swift`

**Step 1: SettingsWindow.swift - NSWindow + NSTabView**

탭 3개:
- 스케줄: ScheduleListView (테이블 + 추가/편집/삭제)
- 강아지: 활동 범위 모드, 이동 속도 슬라이더
- 일반: 로그인 시 자동 시작, 알림 사운드

**Step 2: ScheduleListView.swift - NSTableView 기반 스케줄 목록**

- 컬럼: 활성화 토글, 카테고리 아이콘, 제목, 시간, 반복 타입
- 하단 +/- 버튼으로 추가/삭제

**Step 3: ScheduleEditView.swift - 스케줄 추가/편집 시트**

- 제목, 시간(시/분 피커), 반복 타입, 카테고리 선택
- 저장/취소 버튼

**Step 4: StatusBarController에서 Settings 메뉴 연결**

**Step 5: 빌드 & 확인 - 설정 윈도우 열고 스케줄 추가/편집/삭제**

**Step 6: Commit**

```bash
git add Sources/
git commit -m "feat: add settings window with schedule management"
```

---

### Task 12: 전체 연동 + 마무리

**Files:**
- Modify: `Sources/Puppy/App/AppDelegate.swift` (전체 연동)
- Modify: various files for integration

**Step 1: AppDelegate에서 모든 컴포넌트 연결**

- PuppyWindow + PuppyContentView + PuppyAnimator
- ScheduleManager + ScheduleStore 연결
- ScheduleManager 알림 → PuppyAnimator alert 트리거
- StatusBarController → SettingsWindow 연결
- UserDefaults로 설정값 (활동 범위, 속도) 저장/로드

**Step 2: 활동 범위 모드 구현**

- 하단만 모드: y좌표를 화면 하단 100pt 이내로 제한
- 전체화면 모드: 화면 전체에서 자유 이동

**Step 3: 전체 빌드 & 실행 테스트**

- 강아지가 돌아다니는지
- 메뉴바 아이콘 동작하는지
- 설정 윈도우에서 스케줄 추가하면 제시간에 말풍선 뜨는지
- 클릭/드래그 동작하는지

**Step 4: Commit**

```bash
git add .
git commit -m "feat: integrate all components - Puppy desktop pet complete"
```
