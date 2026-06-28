"""DR v0.2 Validation Gate.

==============================  IMPORTANT  ==============================
**DR = Policy Layer, NOT Runtime Layer.**

DR v0.2 is a *schedulable persona model* (a declarative policy spec). This
package only *validates* such a document and produces a static **pseudo-DAG**
(intent -> steps -> tool selection) so a future Orchestration system can decide
whether the DR is schedulable. It performs NO execution, NO scheduling, NO
orchestration, NO concurrency, and never calls a tool / API / MCP. The Stage 6
Runtime Kernel (execution_engine / trace / memory / state) is untouched and
unaware of this package.
========================================================================
"""

from .dr_v0_2_schema import (  # noqa: F401
    DR_LAYER_ROLE,
    DR_VERSION_V0_2,
    DigitalResidentV02Gate,
)
from .validator import DRValidationResult, finding, validate_dr_v0_2  # noqa: F401
