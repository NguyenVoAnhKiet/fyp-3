# Plan 0016: Re-enroll Feature for Already-Enrolled Users

## Status

**Draft** — Oracle reviewed, concerns addressed.

## Context

Currently, enrollment is a one-time process. Users with `face_registered = 1` are completely invisible in the enrollment dropdown (`enrollment_widget.py:267-279`). The only way to re-enroll is to delete the user and create them again.

This is problematic because:
1. **Appearance changes** — weight gain/loss, glasses, surgery, aging — degrade recognition accuracy over time
2. **Enrollment mistakes** — admin captures poor quality embeddings on first enrollment

The backend (`save_enrollment()`) already supports atomic replacement of all 5 pose embeddings. Only the UI lacks a trigger.

## Goals

1. Admin can see already-enrolled users in the enrollment dropdown via a toggle
2. Admin can re-enroll any user (first-time or already enrolled) using the same 5-pose camera flow
3. Confirmation dialog prevents accidental re-enrollment
4. Success message clearly distinguishes re-enroll from first-time enroll
5. Cancel mid-flow preserves existing face data

## Non-Goals

- No backup/rollback mechanism for old embeddings
- No audit trail for re-enrollment count or history
- No change to the 5-pose camera flow or enrollment AI pipeline
- No change to recognition logic or face matching
- No re-enroll from user-facing mode (admin-only feature)

## Design Decisions

| # | Question | Options Considered | Decision | Rationale |
|---|----------|-------------------|----------|-----------|
| 1 | Problem scope | (A) Appearance only (B) Mistakes only (C) Both | **(C) Both** | Both are valid use cases; same code handles both |
| 2 | UI access point | (A) Button in user mgmt (B) Toggle in enrollment tab (C) Separate tab | **(B) Toggle in enrollment tab** | Minimal UI change, keeps enrollment logic centralized |
| 3 | Old data handling | (A) Replace atomically (B) Backup to history table (C) Keep center only | **(A) Replace atomically** | Simplest; re-enroll again if mistake; no backup complexity |
| 4 | Pose count | (A) Same 5 poses (B) Variable 1-5 (C) Center only | **(A) Same 5 poses** | Consistent flow, no first-time vs re-enroll branching |
| 5 | Confirmation | (A) Simple Yes/No (B) With enrollment date (C) No confirm | **(A) Simple Yes/No** | Enough protection against accidental clicks |
| 6 | Toggle behavior | (A) Checkbox with label (B) Radio buttons (C) Separate button | **(A) Checkbox with label** | Minimal UI change; "(Đã đăng ký)" label provides context |
| 7 | Success message | (A) "Cập nhật face thành công" (B) "Đăng ký face thành công" (C) "Re-enroll thành công" | **(A) "Cập nhật face thành công"** | User-friendly, clearly distinguishes from first-time |
| 8 | Cancel mid-flow | (A) Keep old poses (B) Delete old poses (C) Confirm cancel | **(A) Keep old poses** | `save_enrollment()` only called on completion; no extra logic |

## Tasks

### Phase 1: UI — Add Toggle and Update Dropdown

| Task | Agent | Description |
|------|-------|-------------|
| 1.1 | @fixer | Add QCheckBox "Hiển thị users đã enroll" to `EnrollmentWidget._build_ui()` after user dropdown |
| 1.2 | @fixer | Update `refresh_users()`: checkbox unchecked → `list_unregistered()`, checked → `list_active()` (existing method) with "(Đã đăng ký)" suffix |
| 1.3 | @fixer | Connect checkbox `toggled` signal to `refresh_users()` |
| 1.4 | @fixer | Disable checkbox during enrollment (`_start_enrollment()` → `setEnabled(False)`, `_stop_enrollment()` → `setEnabled(True)`) |
| 1.5 | @fixer | Fix placeholder text: "Không có người dùng nào" (generic) vs "Không có người dùng nào cần đăng ký" (unregistered only) |

**Depends on:** Nothing

**Key detail:** `UserRepository.list_active()` (`user_repository.py:34-35`) already returns all active users regardless of `face_registered`. No new backend method needed.

### Phase 2: UI — Confirmation Dialog + Dropdown Data

| Task | Agent | Description |
|------|-------|-------------|
| 2.1 | @fixer | Store `(user_id, face_registered)` tuple in `QComboBox.addItem()` itemData |
| 2.2 | @fixer | In `_start_enrollment()`, unpack `itemData` → if `face_registered=1`, show `QMessageBox.question()` confirmation |
| 2.3 | @fixer | If user clicks "No", return early without starting camera |

**Depends on:** Phase 1 (dropdown must include enrolled users)

**Key detail:** No DB fetch needed for confirmation check — `face_registered` flag comes from dropdown itemData, which was set during `refresh_users()`.

### Phase 3: UI — Success Message Update

| Task | Agent | Description |
|------|-------|-------------|
| 3.1 | @fixer | In `_handle_complete()`, unpack `itemData` → pass `is_reenroll` to `_finalize_enrollment()` via closure |
| 3.2 | @fixer | In `_finalize_enrollment()`, accept `is_reenroll: bool` parameter |
| 3.3 | @fixer | Success message: `is_reenroll=True` → "Cập nhật face thành công cho [tên]!", else → "Đăng ký khuôn mặt thành công!" |

**Depends on:** Phase 2 (needs `face_registered` in dropdown data)

**Key detail:** Do NOT re-fetch user from DB after `save_enrollment()` — `face_registered` will always be `1` at that point. Pass the flag from dropdown data before save.

### Phase 4: Testing & Validation

| Task | Agent | Description |
|------|-------|-------------|
| 4.1 | @fixer | Add unit tests for toggle behavior (checkbox checked/unchecked → correct user list) |
| 4.2 | @fixer | Add unit tests for confirmation dialog (enrolled user triggers confirm, unregistered does not) |
| 4.3 | @fixer | Add unit tests for success message distinction |
| 4.4 | Orchestrator | Run full test suite: `pytest tests/ -v` |
| 4.5 | Orchestrator | Run lint: `ruff check src/` |

**Depends on:** Phases 1-3

## Implementation

### Files to change

| File | Change |
|------|--------|
| `src/attendance_system/ui/enrollment_widget.py` | Add checkbox toggle, update `refresh_users()`, add confirmation dialog, update success message, disable checkbox during enrollment |
| `tests/unit/test_enrollment_widget.py` | Add tests for toggle, confirmation, success message |

### Detailed changes

#### `enrollment_widget.py` — `_build_ui()`

Add checkbox after user dropdown (after line ~250):

```python
from PyQt5.QtWidgets import QCheckBox  # Add to imports

# In _build_ui(), after user_dropdown:
self._show_enrolled_cb = QCheckBox("Hiển thị users đã enroll")
self._show_enrolled_cb.toggled.connect(self._on_show_enrolled_toggled)
```

#### `enrollment_widget.py` — `refresh_users()`

```python
def refresh_users(self) -> None:
    """Load users based on toggle state."""
    self._user_dropdown.clear()
    if self._show_enrolled_cb.isChecked():
        users = self._user_repo.list_active()  # Existing method — returns all active users
    else:
        users = self._user_repo.list_unregistered()
    for user in users:
        display_text = f"{user['student_id']} - {user['full_name']}"
        is_enrolled = bool(user["face_registered"])
        if is_enrolled:
            display_text += " (Đã đăng ký)"
        # Store (user_id, is_enrolled) tuple as itemData
        self._user_dropdown.addItem(display_text, (user["id"], is_enrolled))

    if not users:
        if self._show_enrolled_cb.isChecked():
            self._user_dropdown.addItem("Không có người dùng nào", (-1, False))
        else:
            self._user_dropdown.addItem("Không có người dùng nào cần đăng ký", (-1, False))
        self._start_btn.setEnabled(False)
    else:
        self._start_btn.setEnabled(True)
```

#### `enrollment_widget.py` — `_on_show_enrolled_toggled()`

```python
def _on_show_enrolled_toggled(self, checked: bool) -> None:
    """Refresh user list when toggle changes."""
    self.refresh_users()
```

#### `enrollment_widget.py` — `_start_enrollment()`

```python
def _start_enrollment(self) -> None:
    item_data = self._user_dropdown.currentData()
    if item_data is None or item_data[0] == -1:
        return
    user_id, is_reenroll = item_data

    # Confirmation for re-enroll
    if is_reenroll:
        display_text = self._user_dropdown.currentText()
        # Extract name from "student_id - full_name (Đã đăng ký)"
        full_name = display_text.split(" - ", 1)[1].rsplit(" (", 1)[0] if " - " in display_text else display_text
        reply = QMessageBox.question(
            self, "Xác Nhận",
            f"Bạn có chắc muốn re-enroll {full_name}?\n"
            "Dữ liệu face cũ sẽ bị thay thế.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.No:
            return

    # ... existing camera setup code unchanged ...
    # Store is_reenroll for later use
    self._is_reenroll = is_reenroll

    # Disable toggle during enrollment
    self._show_enrolled_cb.setEnabled(False)
    # ... rest of method unchanged ...
```

#### `enrollment_widget.py` — `_stop_enrollment()`

```python
def _stop_enrollment(self) -> None:
    # ... existing cleanup code ...
    # Re-enable toggle
    self._show_enrolled_cb.setEnabled(True)
```

#### `enrollment_widget.py` — `_handle_complete()` + `_finalize_enrollment()`

```python
@pyqtSlot(dict)
def _handle_complete(self, pose_embeddings: dict[str, np.ndarray]) -> None:
    """Finalize enrollment after success effect plays."""
    user_id = self._user_dropdown.currentData()[0]
    is_reenroll = self._is_reenroll
    QTimer.singleShot(
        _SUCCESS_EFFECT_DELAY_MS,
        lambda: self._finalize_enrollment(user_id, pose_embeddings, is_reenroll),
    )

def _finalize_enrollment(self, user_id: int, pose_embeddings: dict[str, np.ndarray], is_reenroll: bool) -> None:
    """Save five pose embeddings and show result (called after success effect)."""
    try:
        pose_bytes = {
            pose: emb.tobytes() for pose, emb in pose_embeddings.items()
        }
        first_emb = next(iter(pose_embeddings.values()))
        self._enroll_service.save_face_references(
            user_id=user_id,
            pose_embeddings=pose_bytes,
            model_name="SFace",
            vector_length=len(first_emb),
        )
        # Get user name for success message
        user = self._user_repo.get_by_id(user_id)
        if is_reenroll:
            msg = f"Cập nhật face thành công cho {user['full_name']}!"
        else:
            msg = "Đăng ký khuôn mặt thành công!"
        QMessageBox.information(self, "Thành Công", msg)
    except Exception as e:
        QMessageBox.critical(self, "Lỗi", f"Không thể lưu dữ liệu: {str(e)}")

    self._stop_enrollment()
    self.refresh_users()
```

## Testing

### Unit tests to add

1. `test_enrollment_widget_toggle_shows_all_users` — checkbox checked → dropdown includes enrolled users with "(Đã đăng ký)" label
2. `test_enrollment_widget_toggle_hides_enrolled` — checkbox unchecked → dropdown only unregistered users
3. `test_enrollment_widget_confirm_reenroll` — enrolled user triggers confirmation dialog
4. `test_enrollment_widget_no_confirm_first_time` — unregistered user skips confirmation
5. `test_enrollment_widget_success_message_reenroll` — re-enroll shows "Cập nhật face thành công"
6. `test_enrollment_widget_success_message_first_time` — first-time shows "Đăng ký khuôn mặt thành công"
7. `test_enrollment_widget_checkbox_disabled_during_enrollment` — checkbox disabled when camera running

### Manual smoke checklist

1. Open enrollment tab → checkbox unchecked → only unregistered users shown
2. Check checkbox → all active users shown, enrolled ones have "(Đã đăng ký)" label
3. Select enrolled user → click "Bắt Đầu" → confirmation dialog appears
4. Click "No" → enrollment cancelled, nothing happens
5. Click "Yes" → camera starts, 5-pose flow proceeds
6. Complete 5 poses → success message: "Cập nhật face thành công cho [tên]!"
7. Select unregistered user → no confirmation → complete enrollment → "Đăng ký khuôn mặt thành công!"
8. Cancel mid-re-enroll → old face data preserved in DB
9. Toggle checkbox while enrollment running → should be disabled
10. Run full test suite → all pass

### Verification commands

```bash
pytest tests/unit/test_enrollment_widget.py -v
pytest tests/ -v
ruff check src/attendance_system/ui/enrollment_widget.py
```

## Dependency Graph

```
Phase 1 (UI Toggle):
  1.1 Add checkbox ─────────┐
  1.2 Update refresh_users() ┤
  1.3 Connect signal ────────┤
  1.4 Disable during enroll ─┤
  1.5 Fix placeholder ───────┘
                              │
                              ├──▶ Phase 2 (Confirmation)
                              │
Phase 2 (Confirmation):       │
  2.1 Store tuple in data ────┤
  2.2 Add confirm dialog ─────┤
  2.3 Handle "No" click ──────┘
                              │
                              ├──▶ Phase 3 (Success Message)
                              │
Phase 3 (Success Message):    │
  3.1 Pass is_reenroll ───────┤
  3.2 Accept parameter ───────┤
  3.3 Conditional message ────┘
                              │
                              ├──▶ Phase 4 (Testing)
                              │
Phase 4 (Testing):            │
  4.1-4.3 Unit tests ─────────┤
  4.4 Full test suite ────────┤
  4.5 Lint ───────────────────┘
```

## Sub-Agent Task Breakdown

```
┌─────────────────────────────────────────────────────────────┐
│                    TASK DISTRIBUTION                         │
│                                                             │
│  @fixer (10 tasks):                                        │
│  ├─ 1.1 Add checkbox to UI                                 │
│  ├─ 1.2 Update refresh_users()                             │
│  ├─ 1.3 Connect checkbox signal                            │
│  ├─ 1.4 Disable checkbox during enrollment                 │
│  ├─ 1.5 Fix placeholder text                               │
│  ├─ 2.1 Store tuple in dropdown data                       │
│  ├─ 2.2 Add confirmation dialog                            │
│  ├─ 2.3 Handle "No" click                                  │
│  ├─ 3.1-3.3 Update success message                         │
│  └─ 4.1-4.3 Unit tests                                     │
│                                                             │
│  Orchestrator (2 tasks):                                   │
│  ├─ 4.4 Run full test suite                                │
│  └─ 4.5 Run linting                                        │
│                                                             │
│  @oracle (1 task):                                         │
│  └─ Phase reviews (after each phase)                       │
│                                                             │
│  Total: 13 tasks                                           │
│  @fixer: 77% | @oracle: 8% | Orchestrator: 15%            │
└─────────────────────────────────────────────────────────────┘
```
