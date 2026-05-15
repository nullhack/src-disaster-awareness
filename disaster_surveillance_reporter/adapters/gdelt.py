import httpx

from disaster_surveillance_reporter.types import RawRecord


class GDELTAdapter:
    source_name = "GDELT"

    def fetch(self, client: httpx.Client) -> list[RawRecord]:
        raise NotImplementedError
