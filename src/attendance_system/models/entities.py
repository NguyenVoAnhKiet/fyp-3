from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class UserAccount:
    student_id: str
    full_name: str
    is_active: bool = True


@dataclass(slots=True)
class FaceReference:
    user_id: int
    embedding: bytes
    model_name: str
    vector_length: int
    pose_label: str = "center"


@dataclass(slots=True)
class AttendanceSession:
    subject_name: str
    class_name: str
    status: str
    liveness_threshold_snapshot: float
    similarity_threshold_snapshot: float


@dataclass(slots=True)
class RecognitionEvent:
    session_id: int
    user_id: int | None
    event_time: str
    result: str
    liveness_score: float | None = None
    similarity_score: float | None = None
    details: str | None = None


@dataclass(slots=True)
class AttendanceRecord:
    session_id: int
    user_id: int
    status: str
    recorded_at: str


@dataclass(slots=True)
class SystemSetting:
    setting_key: str
    setting_value: str
    value_type: str | None = None


@dataclass(slots=True)
class AdminCredential:
    username: str
    password_hash: str

