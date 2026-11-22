import time
import pytest

pygame = pytest.importorskip("pygame")


def make_ui():
    import os
    os.environ["HUB_WINDOW"] = "1280x800"
    import hub.ui as H
    return H.UI()


def run(u, n=3):
    for _ in range(n):
        u.frame()
        time.sleep(0.01)


def pump_until(u, pred, timeout=10):
    end = time.time() + timeout
    while time.time() < end:
        run(u, 2)
        if pred():
            return True
    return bool(pred())
