import httpx

from disaster_surveillance_reporter.adapters._types import SourceAdapter
from disaster_surveillance_reporter.types import RawRecord


class WHOAdapter(SourceAdapter):
    source_name = "WHO"

    def fetch(self, client: httpx.Client) -> list[RawRecord]:
        raise NotImplementedError
