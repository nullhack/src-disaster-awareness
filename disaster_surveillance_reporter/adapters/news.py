from disaster_surveillance_reporter.types import RawRecord


class NewsSearcher:
    source_name = "DDG-NEWS"

    def search(self, query, *, region, timelimit, max_results):
        raise NotImplementedError
