from disaster_surveillance_reporter.types import IncidentBundle


class ExtractorAgent:
    def extract(self, bundles: list[IncidentBundle]) -> list[IncidentBundle]:
        raise NotImplementedError
