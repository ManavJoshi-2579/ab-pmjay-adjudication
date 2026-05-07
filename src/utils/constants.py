"""Project-wide constants."""

DOCUMENT_LABELS = [
    "claim_form",
    "discharge_summary",
    "procedure_note",
    "bill",
    "investigation_report",
    "prescription",
    "id_proof",
    "other",
]

TIMELINE_EVENTS = [
    "admission",
    "investigation",
    "procedure",
    "monitoring",
    "discharge",
]

VISUAL_LABELS = ["stamp", "signature", "qr_code", "implant_sticker"]

EXTRACTABLE_FIELDS = [
    "patient_name",
    "diagnosis",
    "procedure",
    "dates",
    "amounts",
]
