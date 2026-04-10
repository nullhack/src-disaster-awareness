"""Source adapters for disaster incident data.

This module provides pluggable adapters for fetching incident data from various sources.
"""

from disaster_surveillance_reporter.adapters._types import (
    RawIncidentData as RawIncidentData,
)
from disaster_surveillance_reporter.adapters._types import (
    SourceAdapter as SourceAdapter,
)

# Import adapters
from disaster_surveillance_reporter.adapters.gdacs import GDACSAdapter  # noqa: F401
from disaster_surveillance_reporter.adapters.healthmap import (
    HealthMapAdapter,  # noqa: F401
)
from disaster_surveillance_reporter.adapters.promed import ProMEDAdapter  # noqa: F401
from disaster_surveillance_reporter.adapters.reliefweb import (
    ReliefWebAdapter,  # noqa: F401
)
from disaster_surveillance_reporter.adapters.who import WHOAdapter  # noqa: F401
