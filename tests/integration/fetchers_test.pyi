from disaster_report.models import FetchedArticle


def fetch_article(url: str, timeout: float = 10.0) -> FetchedArticle | None: ...
