"""Enumerations."""
from enum import IntEnum


class SARType(IntEnum):
    uavsar = 0


class SARDespeckleType(IntEnum):
    median = 0


class SARFunctionType(IntEnum):
    ccd = 0
