"""
Task queue and checklist manager parsing standard Markdown checklists (TASKS.md).
"""

import re
from pathlib import Path
from typing import Optional, Tuple, List


class TaskQueue:
    """
    Manages sequential task execution from a markdown checklist file.
    Supports - [ ] (pending) and - [x] (completed).
    """

    def __init__(self, filepath: str = "TASKS.md"):
        self.filepath = Path(filepath)

    def exists(self) -> bool:
        return self.filepath.exists()

    def get_next_task(self) -> Optional[str]:
        """Finds the first unchecked task in the file."""
        if not self.exists():
            return None

        with open(self.filepath, "r", encoding="utf-8") as f:
            for line in f:
                match = re.match(r"^\s*-\s*\[\s*\]\s+(.+)$", line)
                if match:
                    return match.group(1).strip()
        return None

    def mark_completed(self, task_text: str) -> bool:
        """Finds the given task and marks it as - [x]."""
        if not self.exists():
            return False

        lines: List[str] = []
        found = False

        with open(self.filepath, "r", encoding="utf-8") as f:
            for line in f:
                # If unchecked and matches task text
                if not found and re.match(r"^\s*-\s*\[\s*\]\s+" + re.escape(task_text), line):
                    # Replace [ ] with [x]
                    modified_line = re.sub(r"\[\s*\]", "[x]", line, count=1)
                    lines.append(modified_line)
                    found = True
                else:
                    lines.append(line)

        if found:
            with open(self.filepath, "w", encoding="utf-8") as f:
                f.writelines(lines)

        return found

    def get_progress(self) -> Tuple[int, int]:
        """Returns (completed_count, total_count)."""
        if not self.exists():
            return 0, 0

        completed = 0
        total = 0

        with open(self.filepath, "r", encoding="utf-8") as f:
            for line in f:
                if re.match(r"^\s*-\s*\[[xX]\]\s+", line):
                    completed += 1
                    total += 1
                elif re.match(r"^\s*-\s*\[\s*\]\s+", line):
                    total += 1

        return completed, total
