"""Temporal consistency checks."""

from __future__ import annotations

from datetime import datetime

from src.core.state_manager import RuleViolation, TimelineEvent


class TemporalValidator:
    """Validate timeline ordering and duration constraints."""

    def validate(
        self,
        timeline: list[TimelineEvent],
        max_length_of_stay_days: int = 30,
        date_order_rules: list[list[str]] | None = None,
    ) -> list[RuleViolation]:
        """Return temporal rule violations."""
        violations: list[RuleViolation] = []
        ordered = sorted(timeline, key=lambda item: item.date)
        if ordered != timeline:
            violations.append(
                RuleViolation(
                    rule_name="date_order",
                    severity="high",
                    message="Timeline events are not in chronological order.",
                    evidence=[
                        {"event_type": item.event_type, "date": item.date, "page_number": item.page_number}
                        for item in ordered
                    ],
                )
            )
        duplicates = self._duplicate_events(ordered)
        if duplicates:
            violations.append(
                RuleViolation(
                    rule_name="duplicate_events",
                    severity="medium",
                    message=f"Duplicate timeline events detected: {', '.join(duplicates)}.",
                    evidence=[{"event": item} for item in duplicates],
                )
            )
        admission = next((event for event in ordered if event.event_type == "admission"), None)
        discharge = next((event for event in ordered if event.event_type == "discharge"), None)
        if admission and discharge:
            los = (datetime.fromisoformat(discharge.date) - datetime.fromisoformat(admission.date)).days
            if los < 0 or los > max_length_of_stay_days:
                violations.append(
                    RuleViolation(
                        rule_name="length_of_stay",
                        severity="high",
                        message=f"Length of stay {los} days violates configured bounds.",
                    )
                )
        missing_core_events = [
            event_name for event_name in ("admission", "discharge") if not any(item.event_type == event_name for item in ordered)
        ]
        if missing_core_events:
            violations.append(
                RuleViolation(
                    rule_name="missing_timeline_events",
                    severity="medium",
                    message=f"Missing critical timeline events: {', '.join(missing_core_events)}.",
                    evidence=[{"missing_event": item} for item in missing_core_events],
                )
            )
        for before_event, after_event in date_order_rules or []:
            before = next((event for event in ordered if event.event_type == before_event), None)
            after = next((event for event in ordered if event.event_type == after_event), None)
            if before and after and before.date > after.date:
                violations.append(
                    RuleViolation(
                        rule_name="configured_date_order",
                        severity="high",
                        message=f"Configured date order violated: {before_event} occurs after {after_event}.",
                        evidence=[
                            {"event_type": before.event_type, "date": before.date},
                            {"event_type": after.event_type, "date": after.date},
                        ],
                    )
                )
        same_day_collisions = self._same_day_collisions(ordered)
        if same_day_collisions:
            violations.append(
                RuleViolation(
                    rule_name="same_day_event_overlap",
                    severity="low",
                    message="Multiple clinically meaningful events share the same day; verify ordering from source pages.",
                    evidence=same_day_collisions,
                )
            )
        return violations

    @staticmethod
    def _duplicate_events(timeline: list[TimelineEvent]) -> list[str]:
        """Return duplicate event identifiers."""
        seen: set[tuple[str, str]] = set()
        duplicates: list[str] = []
        for item in timeline:
            key = (item.event_type, item.date)
            if key in seen:
                duplicates.append(f"{item.event_type}@{item.date}")
            else:
                seen.add(key)
        return duplicates

    @staticmethod
    def _same_day_collisions(timeline: list[TimelineEvent]) -> list[dict[str, str]]:
        """Return same-day multi-event groupings for explainability."""
        by_date: dict[str, set[str]] = {}
        for item in timeline:
            by_date.setdefault(item.date, set()).add(item.event_type)
        return [
            {"date": date, "events": ", ".join(sorted(events))}
            for date, events in by_date.items()
            if len(events) > 1
        ]
