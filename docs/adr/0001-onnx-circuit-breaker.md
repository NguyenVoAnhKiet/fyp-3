# ADR-0001: ONNX Inference Circuit-Breaker

After 30 consecutive `session.run()` failures, the camera thread emits `camera_error` (modal dialog) and shuts down instead of spinning silently. Individual failures are caught, logged, and skipped — the thread only dies when the model is persistently dead.

## Considered Options

- **No recovery** — original behavior: uncaught exception kills the thread immediately with no diagnostic.
- **Skip silently** — catch all errors, log, skip the frame, keep going forever. User sits on a dead camera until they notice.
- **Throttled warnings** — log/emit warning at most once per 5 seconds. Avoids log spam but doesn't definitively detect a dead model.
- **Consecutive counter (chosen)** — resets on any successful frame, kills thread at 30 (~1 second). Catches persistent failure fast while tolerating transient glitches.

## Consequences

- A transient burst of 30+ errors (e.g., GPU scheduling contention at cold start) will kill the thread when it might have recovered. This is acceptable because (a) the app can be restarted, and (b) if the GPU is that contended, inference quality is unreliable anyway.
- The counter is shared between liveness and head-pose in the enrollment thread — one broken model kills both. This simplifies the implementation at the cost of not degrading gracefully. Acceptable because AI is the core feature; partial operation without it is not useful.
