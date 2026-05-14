from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class Slot:
    uuid: str
    hospital_uuid: str
    department: str
    type: str
    date: date
    created_by: str
    created_at: datetime
    mediciner_crm: str | None = None
