"""Backward-compatibility re-export shim.

The canonical location is now ``attendance_system.services.liveness_tracker``.
This module re-exports all public names so existing ``from attendance_system.core.liveness_tracker import ...``
continues to work.

.. deprecated:: 0.0.4
    Import from ``attendance_system.services.liveness_tracker`` instead.
"""

from attendance_system.services.liveness_tracker import (  # noqa: F401
    ALPHA,
    IOU_THRESHOLD,
    MAX_MISSES,
    T_HIGH,
    T_LOW,
    LivenessTracker,
    TrackedFace,
    compute_iou,
)
