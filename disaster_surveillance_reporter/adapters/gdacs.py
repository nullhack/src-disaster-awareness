import httpx

from disaster_surveillance_reporter.types import RawRecord


class GDACSAdapter:
    source_name = "GDACS"

    def fetch(self, client: httpx.Client) -> list[RawRecord]:
        raise NotImplementedError
