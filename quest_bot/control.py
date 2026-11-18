"""Safe program shutdown control across multiple threads."""
import threading

stop_event = threading.Event()


def stopped() -> bool:
    return stop_event.is_set()


def sleep(seconds: float) -> bool:
    """Interruptible sleep. Returns True if a stop was requested."""
    return stop_event.wait(max(0, seconds))
