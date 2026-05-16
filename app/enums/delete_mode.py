from enum import StrEnum


class DeleteMode(StrEnum):
    CASCADE = "cascade"
    REASSIGN = "reassign"
