"""DR (Digital Resident) packages.

Hosts the DR Validation Gate (v2). This is a PURE declarative validation layer:
it reads a DR document and emits findings + a static pseudo-DAG. It never
executes, schedules, or orchestrates anything, and never touches the Runtime.
"""
