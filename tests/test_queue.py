"""
Unit tests for Markdown checklist manager (queue.py).
Compatible with both unittest and pytest.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from desk_resumer.core.queue import TaskQueue


class TestTaskQueue(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_queue_file_not_found(self):
        missing_file = os.path.join(self.test_dir, "NON_EXISTENT.md")
        queue = TaskQueue(missing_file)
        self.assertFalse(queue.exists())
        self.assertIsNone(queue.get_next_task())
        self.assertEqual(queue.get_progress(), (0, 0))
        self.assertFalse(queue.mark_completed("Non-existent"))

    def test_queue_reading_and_progress(self):
        task_file = os.path.join(self.test_dir, "TASKS.md")
        content = """# Project Plan

- [x] Initial setup and architecture review
- [ ] Implement mobile and desktop preview product mockups on hover
- [ ] Add smooth transition data changes inside product views
- [x] Write initial tests
"""
        with open(task_file, "w", encoding="utf-8") as f:
            f.write(content)

        queue = TaskQueue(task_file)
        self.assertTrue(queue.exists())

        # 2 completed, 4 total
        completed, total = queue.get_progress()
        self.assertEqual(completed, 2)
        self.assertEqual(total, 4)

        # Next unchecked task should be the first [ ] item
        next_task = queue.get_next_task()
        self.assertEqual(next_task, "Implement mobile and desktop preview product mockups on hover")

    def test_queue_mark_completed(self):
        task_file = os.path.join(self.test_dir, "TASKS.md")
        content = """- [ ] Step 1: Design database
- [ ] Step 2: Write API endpoints
"""
        with open(task_file, "w", encoding="utf-8") as f:
            f.write(content)

        queue = TaskQueue(task_file)
        self.assertEqual(queue.get_next_task(), "Step 1: Design database")

        success = queue.mark_completed("Step 1: Design database")
        self.assertTrue(success)

        # After marking step 1 complete, step 2 should be next
        self.assertEqual(queue.get_next_task(), "Step 2: Write API endpoints")
        completed, total = queue.get_progress()
        self.assertEqual(completed, 1)
        self.assertEqual(total, 2)

    def test_queue_all_completed(self):
        task_file = os.path.join(self.test_dir, "TASKS.md")
        content = """- [x] Step 1
- [X] Step 2
"""
        with open(task_file, "w", encoding="utf-8") as f:
            f.write(content)

        queue = TaskQueue(task_file)
        self.assertIsNone(queue.get_next_task())
        self.assertEqual(queue.get_progress(), (2, 2))


if __name__ == "__main__":
    unittest.main()
