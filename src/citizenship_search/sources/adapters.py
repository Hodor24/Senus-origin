from __future__ import annotations

from dataclasses import dataclass

from citizenship_search.sources.base import SourceHit


@dataclass(slots=True)
class StaticAdapter:
    name: str
    jurisdiction: str
    archive: str
    records: list[dict[str, str]]

    def search(self, query: str) -> list[SourceHit]:
        query_lower = query.lower()
        hits: list[SourceHit] = []
        for record in self.records:
            blob = " ".join(record.values()).lower()
            if query_lower in blob:
                hits.append(
                    SourceHit(
                        source_name=self.name,
                        title=record["title"],
                        document_id=record["document_id"],
                        summary=record["summary"],
                        jurisdiction=self.jurisdiction,
                        archive=self.archive,
                        url=record.get("url"),
                    )
                )
        return hits

    def fetch_metadata(self, document_id: str) -> dict[str, str]:
        for record in self.records:
            if record["document_id"] == document_id:
                return record
        raise KeyError(f"Unknown document: {document_id}")

    def fetch_document(self, document_id: str) -> bytes:
        metadata = self.fetch_metadata(document_id)
        return f"Placeholder bytes for {metadata['title']}".encode("utf-8")

    def rate_limit_state(self) -> dict[str, str]:
        return {"status": "ok", "remaining": "unlimited", "window": "demo"}


def build_default_adapters() -> list[StaticAdapter]:
    return [
        StaticAdapter(
            name="uk_civil_manchester",
            jurisdiction="UK",
            archive="Manchester Civil & Local Archives",
            records=[
                {
                    "document_id": "uk-death-2014-roman-senus",
                    "title": "Death Certificate - Roman Senus (2014)",
                    "summary": "Manchester death entry, birthplace stated as Poland.",
                    "url": "https://example.org/uk/death/roman-senus-2014",
                },
                {
                    "document_id": "uk-marriage-roman-senus",
                    "title": "Marriage Certificate - Roman Senus",
                    "summary": "Father listed as Michal/Michael, occupation painter.",
                    "url": "https://example.org/uk/marriage/roman-senus",
                },
            ],
        ),
        StaticAdapter(
            name="poland_state_archives",
            jurisdiction="Poland",
            archive="State Archives",
            records=[
                {
                    "document_id": "pl-military-1945-1947",
                    "title": "Polish Army Service Card 1945-1947",
                    "summary": "Soviet military affiliation listed for Roman Senus.",
                    "url": "https://example.org/pl/military/1945-1947",
                }
            ],
        ),
        StaticAdapter(
            name="ukraine_regional_stryi",
            jurisdiction="Ukraine",
            archive="Lviv Regional Archives",
            records=[
                {
                    "document_id": "ua-stryi-population-ledger",
                    "title": "Stryi population ledger reference",
                    "summary": "Possible family entry with surname Senus.",
                    "url": "https://example.org/ua/stryi/ledger",
                }
            ],
        ),
        StaticAdapter(
            name="russia_soviet_military_index",
            jurisdiction="Russia",
            archive="Soviet Military Indexes",
            records=[
                {
                    "document_id": "ru-red-army-senus",
                    "title": "Soviet era service listing",
                    "summary": "Potential service overlap 1945-1947.",
                    "url": "https://example.org/ru/service/senus",
                }
            ],
        ),
        StaticAdapter(
            name="polish_forces_west",
            jurisdiction="International",
            archive="Polish Armed Forces in West Collection",
            records=[
                {
                    "document_id": "paw-return-1948-senus",
                    "title": "Return from armed forces in west (1948)",
                    "summary": "Father name variant recorded as Mikolaj.",
                    "url": "https://example.org/int/paw/senus-1948",
                }
            ],
        ),
    ]
