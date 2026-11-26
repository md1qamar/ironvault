"""
IronVault Security Manager
Handles:
1. Clipboard Auto-Clear with smart hash check (clears after 30 seconds)
2. Inactivity Auto-Lock watchdog
3. Memory cleanup helpers
"""

import time
import threading


class SecurityManager:
    def __init__(self, app_root, on_auto_lock_callback=None, auto_lock_timeout_secs: int = 300):
        self.root = app_root
        self.on_auto_lock = on_auto_lock_callback
        self.auto_lock_timeout = auto_lock_timeout_secs
        self.last_activity = time.time()
        self.is_running = True

        self._clipboard_timer = None
        self._last_copied_text = None

        # Bind user activity events to reset inactivity timer
        self._bind_events()

        # Start background watchdog for inactivity
        self._watchdog_thread = threading.Thread(target=self._idle_watchdog, daemon=True)
        self._watchdog_thread.start()

    def _bind_events(self):
        try:
            self.root.bind_all("<Key>", self._on_user_interaction, add="+")
            self.root.bind_all("<Button>", self._on_user_interaction, add="+")
            self.root.bind_all("<Motion>", self._on_user_interaction, add="+")
        except Exception:
            pass

    def _on_user_interaction(self, event=None):
        self.last_activity = time.time()

    def copy_sensitive_data(self, text: str, clear_after_secs: int = 30, on_clear_cb=None):
        """
        Copies sensitive text to clipboard and schedules auto-clear.
        """
        if not text:
            return

        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()
        except Exception as e:
            print(f"Clipboard copy error: {e}")

        self._last_copied_text = text

        # Cancel any previous clipboard timer
        if self._clipboard_timer and self._clipboard_timer.is_alive():
            self._clipboard_timer.cancel()

        def _clear_worker():
            time.sleep(clear_after_secs)
            try:
                # Check if clipboard still holds the same text before clearing
                current = self.root.clipboard_get()
                if current == self._last_copied_text:
                    self.root.clipboard_clear()
                    self.root.update()
                    if on_clear_cb:
                        self.root.after(0, on_clear_cb)
            except Exception:
                # Clipboard was already modified or unavailable
                pass
            finally:
                self._last_copied_text = None

        self._clipboard_timer = threading.Timer(clear_after_secs, _clear_worker)
        self._clipboard_timer.daemon = True
        self._clipboard_timer.start()

    def _idle_watchdog(self):
        while self.is_running:
            time.sleep(2)
            if self.auto_lock_timeout > 0:
                elapsed = time.time() - self.last_activity
                if elapsed >= self.auto_lock_timeout:
                    if self.on_auto_lock:
                        # Schedule lock on main GUI thread
                        try:
                            self.root.after(0, self.on_auto_lock)
                        except Exception:
                            pass
                        # Reset to avoid continuous re-triggers
                        self.last_activity = time.time()

    def stop(self):
        self.is_running = False
        if self._clipboard_timer and self._clipboard_timer.is_alive():
            self._clipboard_timer.cancel()
