import unittest
import threading
import time
import socket
from pathlib import Path
from core.ipc import (
    acquire_single_instance_mutex,
    send_files_to_running_instance,
    send_files_with_retry,
    IPCServer
)

TEST_PORT = 49299
TEST_MUTEX = "Local\\SizeWiz_Unit_Test_Mutex"

class TestSingleInstanceAndIPC(unittest.TestCase):

    def test_mutex_primary_and_secondary(self):
        h1, is_p1 = acquire_single_instance_mutex(TEST_MUTEX)
        self.assertTrue(is_p1, "First caller must be primary")
        self.assertIsNotNone(h1)

        # Second caller while h1 is held
        h2, is_p2 = acquire_single_instance_mutex(TEST_MUTEX)
        self.assertFalse(is_p2, "Second caller must be secondary")

        # Cleanup handles
        import ctypes
        if h1:
            ctypes.windll.kernel32.CloseHandle(h1)
        if h2:
            ctypes.windll.kernel32.CloseHandle(h2)

    def test_ipc_concurrent_explorer_launches(self):
        """Simulates 5 concurrent secondary processes sending files to primary IPCServer."""
        server = IPCServer(port=TEST_PORT)
        started = server.start()
        self.assertTrue(started, "IPCServer must start successfully")

        # Simulate 5 concurrent processes
        results = [False] * 5
        def worker(idx):
            results[idx] = send_files_with_retry(
                [f"C:\\test_image_{idx}.png"],
                port=TEST_PORT,
                max_attempts=20,
                delay=0.02
            )

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertTrue(all(results), f"All 5 processes must successfully send files: {results}")

        pending = server.get_and_clear_pending_files()
        self.assertEqual(len(pending), 5, f"Expected 5 files accumulated, got {len(pending)}")
        expected_files = {f"C:\\test_image_{i}.png" for i in range(5)}
        self.assertEqual(set(pending), expected_files)

        server.stop()

    def test_ipc_callback_dispatch(self):
        """Tests live callback dispatch after server is already running."""
        received = []
        def on_files(files):
            received.extend(files)

        server = IPCServer(callback=on_files, port=TEST_PORT)
        server.start()

        ok = send_files_to_running_instance(["C:\\live_photo.jpg"], port=TEST_PORT)
        self.assertTrue(ok)

        # Allow quick thread context switch
        time.sleep(0.05)
        self.assertIn("C:\\live_photo.jpg", received)

        server.stop()

    def test_ipc_focus_action(self):
        """Tests sending empty file list triggers focus action."""
        focus_triggered = []
        def on_focus():
            focus_triggered.append(True)

        server = IPCServer(focus_callback=on_focus, port=TEST_PORT)
        server.start()

        ok = send_files_to_running_instance([], port=TEST_PORT)
        self.assertTrue(ok)

        time.sleep(0.05)
        self.assertTrue(len(focus_triggered) > 0, "Focus callback must be triggered")

        server.stop()


if __name__ == "__main__":
    unittest.main()
