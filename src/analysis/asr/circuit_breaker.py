"""
Circuit Breaker for ASR
-----------------------
Tracks local ASR failures and switches to cloud API when needed.

Three states:
  CLOSED   -> normal, all requests go to local model
  OPEN     -> local model failed too many times, all requests go to cloud
  HALF_OPEN -> testing if local model recovered (one canary request)

Why do we need this?
  Without it, if the local model crashes or runs out of GPU memory,
  every request will hang or fail. The circuit breaker detects this
  and instantly routes to the cloud API, keeping the system alive.
"""

import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional

from src.core.config import settings
from src.core.logger import logger


class CircuitState(Enum):
    CLOSED = "closed"       # Normal operation - use local model
    OPEN = "open"           # Local model failed - use cloud API
    HALF_OPEN = "half_open" # Testing recovery - send one canary request


@dataclass
class CircuitBreaker:
    """
    Circuit breaker for the ASR module.
    Thread-safe for use in Celery workers.
    """
    failure_count: int = 0
    last_failure_time: float = 0.0
    state: CircuitState = CircuitState.CLOSED
    success_count_in_half_open: int = 0

    # Config thresholds
    max_failures: int = field(default_factory=lambda: settings.circuit_breaker_failure_count)
    cooldown_seconds: int = field(default_factory=lambda: settings.circuit_breaker_cooldown_seconds)
    confidence_threshold: float = field(default_factory=lambda: settings.asr_confidence_threshold)

    def should_use_fallback(self) -> bool:
        """
        Returns True if we should route to cloud API instead of local model.
        Also handles the OPEN -> HALF_OPEN transition after cooldown.
        """
        if self.state == CircuitState.CLOSED:
            return False

        if self.state == CircuitState.OPEN:
            # Check if cooldown period has passed
            time_since_failure = time.time() - self.last_failure_time
            if time_since_failure >= self.cooldown_seconds:
                logger.info(
                    f"Circuit breaker cooldown elapsed ({time_since_failure:.0f}s) "
                    f"- entering HALF_OPEN state"
                )
                self.state = CircuitState.HALF_OPEN
                return False  # Allow one canary request through
            return True  # Still in cooldown - use cloud

        if self.state == CircuitState.HALF_OPEN:
            return False  # Allow the canary request through

        return False

    def record_success(self, confidence: float) -> None:
        """
        Called when local ASR succeeds.
        Resets failure count. If in HALF_OPEN, closes the circuit.
        """
        if confidence < self.confidence_threshold:
            # Low confidence = soft failure
            logger.warning(
                f"ASR confidence {confidence:.2f} below threshold "
                f"{self.confidence_threshold} - recording soft failure"
            )
            self.record_failure(reason=f"low_confidence:{confidence:.2f}")
            return

        if self.state == CircuitState.HALF_OPEN:
            logger.success("Circuit breaker canary succeeded - returning to CLOSED state")

        self.failure_count = 0
        self.state = CircuitState.CLOSED
        logger.debug(f"Circuit breaker: success recorded (confidence: {confidence:.2f})")

    def record_failure(self, reason: str = "unknown") -> None:
        """
        Called when local ASR fails (OOM, timeout, low confidence).
        Opens the circuit after max_failures consecutive failures.
        """
        self.failure_count += 1
        self.last_failure_time = time.time()

        logger.warning(
            f"Circuit breaker failure #{self.failure_count}/{self.max_failures} "
            f"- reason: {reason}"
        )

        if self.failure_count >= self.max_failures:
            if self.state != CircuitState.OPEN:
                logger.error(
                    f"Circuit breaker OPENED after {self.failure_count} failures. "
                    f"Routing all requests to cloud API for {self.cooldown_seconds}s"
                )
            self.state = CircuitState.OPEN

    def get_status(self) -> dict:
        """Return current circuit breaker status for health checks."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "max_failures": self.max_failures,
            "seconds_until_retry": max(
                0,
                self.cooldown_seconds - (time.time() - self.last_failure_time)
            ) if self.state == CircuitState.OPEN else 0,
        }


# Global singleton circuit breaker instance
# Shared across all ASR calls in a worker process
_circuit_breaker = CircuitBreaker()


def get_circuit_breaker() -> CircuitBreaker:
    """Get the global circuit breaker instance."""
    return _circuit_breaker