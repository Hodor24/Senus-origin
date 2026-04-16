from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import uuid4


@dataclass(slots=True)
class ArchiveRequest:
    request_id: str
    repository_name: str
    language: str
    contact_email: str
    request_text: str
    due_date: str
    fee_estimate: str
    status: str = "draft"


def build_request_template(
    repository_name: str,
    language: str,
    person_name: str,
    birthplace: str,
    year_range: str,
) -> str:
    if language.lower() == "pl":
        return (
            f"Szanowni Panstwo,\n\n"
            f"Zwracam sie z prosba o wyszukanie dokumentow dotyczacych osoby {person_name}, "
            f"urodzonej prawdopodobnie w {birthplace}, okres {year_range}. "
            f"Prosze o informacje o dostepnych aktach i procedurze uzyskania kopii.\n\n"
            "Z powazaniem,"
        )
    return (
        f"Dear Archive Team,\n\n"
        f"I am requesting records related to {person_name}, likely born in {birthplace}, "
        f"for the period {year_range}. Please advise what records are available and the "
        "process/fees for obtaining certified copies.\n\n"
        "Kind regards,"
    )


def create_archive_request(
    repository_name: str,
    language: str,
    contact_email: str,
    person_name: str,
    birthplace: str,
    year_range: str,
    due_in_days: int = 30,
    fee_estimate: str = "unknown",
) -> ArchiveRequest:
    request_text = build_request_template(repository_name, language, person_name, birthplace, year_range)
    due_date = date.fromordinal(date.today().toordinal() + due_in_days).isoformat()
    return ArchiveRequest(
        request_id=str(uuid4()),
        repository_name=repository_name,
        language=language,
        contact_email=contact_email,
        request_text=request_text,
        due_date=due_date,
        fee_estimate=fee_estimate,
    )
