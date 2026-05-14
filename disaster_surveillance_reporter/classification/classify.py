from disaster_surveillance_reporter.types import IncidentBundle


class ClassifyEngine:
    def classify(self, bundle: IncidentBundle) -> IncidentBundle:
        raise NotImplementedError

    def reevaluate_overrides(self, bundle: IncidentBundle) -> IncidentBundle:
        raise NotImplementedError
