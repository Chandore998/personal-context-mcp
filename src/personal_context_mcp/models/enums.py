from enum import StrEnum


class MemoryType(StrEnum):
    TASK_SUMMARY = "task_summary"
    PROJECT_SUMMARY = "project_summary"
    MISTAKE = "mistake"
    CORRECTION = "correction"
    PREFERENCE = "preference"
    DECISION = "decision"
    NOTE = "note"
