"""System prompt formatting for temporal context."""

from pitlane_agent.temporal.context import (
    F1Season,
    RaceWeekendContext,
    TemporalContext,
)


def format_for_system_prompt(context: TemporalContext, verbosity: str = "normal") -> str:
    """Format temporal context for inclusion in system prompt.

    Args:
        context: Temporal context
        verbosity: "minimal", "normal", or "detailed"

    Returns:
        Formatted string for system prompt
    """
    if verbosity == "minimal":
        return _format_minimal(context)
    elif verbosity == "detailed":
        return _format_detailed(context)
    else:
        return _format_normal(context)


def _format_minimal(context: TemporalContext) -> str:
    """Minimal format for system prompt.

    Args:
        context: Temporal context

    Returns:
        Formatted string
    """
    lines = [
        "## F1 Temporal Context",
        "",
        f"**Season:** {context.current_season} ({context.season_phase.value.replace('_', ' ').title()})",
    ]

    if context.next_race:
        lines.append(
            f"**Next Race:** {context.next_race.event_name} (Round {context.next_race.round_number}) - "
            f"{context.next_race.event_date.strftime('%B %d, %Y')}"
        )
        if context.days_until_next_race is not None:
            lines.append(f"  ({context.days_until_next_race} days)")

    if context.last_completed_race:
        lines.append(
            f"**Last Race:** {context.last_completed_race.event_name} - "
            f"Completed {context.last_completed_race.event_date.strftime('%B %d, %Y')}"
        )

    return "\n".join(lines)


def _format_normal(context: TemporalContext) -> str:
    """Normal format for system prompt.

    Args:
        context: Temporal context

    Returns:
        Formatted string
    """
    lines = ["## F1 Temporal Context", ""]

    # Current season and phase
    lines.append(f"**Current Season:** {context.current_season}")

    phase_display = context.season_phase.value.replace("_", " ").title()
    if context.season_phase == F1Season.IN_SEASON:
        lines.append(
            f"**Phase:** {phase_display} "
            f"(Round {context.races_completed} of {context.races_completed + context.races_remaining} completed)"
        )
    else:
        lines.append(f"**Phase:** {phase_display}")

    lines.append("")

    # Current race weekend (if any)
    if context.current_weekend:
        lines.extend(_format_current_weekend(context.current_weekend))
        lines.append("")

    # Next race
    if context.next_race and not context.current_weekend:
        lines.append(f"**Next Race:** {context.next_race.event_name}")
        lines.append(
            f"- Round {context.next_race.round_number} in {context.next_race.location}, {context.next_race.country}"
        )
        lines.append(f"- Race Weekend: {context.next_race.event_date.strftime('%B %d, %Y')}")

        if context.days_until_next_race is not None:
            if context.days_until_next_race == 0:
                lines.append("- TODAY")
            elif context.days_until_next_race == 1:
                lines.append("- Tomorrow")
            else:
                lines.append(f"- {context.days_until_next_race} days until race weekend")

        if context.next_race.is_sprint_weekend:
            lines.append("- Format: Sprint weekend")
        else:
            lines.append("- Format: Conventional weekend")

        lines.append("")

    # Last completed race
    if context.last_completed_race:
        lines.append(
            f"**Last Race:** {context.last_completed_race.event_name} "
            f"(Round {context.last_completed_race.round_number})"
        )
        lines.append(
            f"- Completed {context.last_completed_race.event_date.strftime('%B %d, %Y')} "
            f"in {context.last_completed_race.location}"
        )

        # Calculate days since
        days_since = (context.current_time_utc - context.last_completed_race.event_date).days
        if days_since == 0:
            lines.append("- Earlier today")
        elif days_since == 1:
            lines.append("- Yesterday")
        elif days_since < 7:
            lines.append(f"- {days_since} days ago")
        elif days_since < 14:
            lines.append("- 1 week ago")
        else:
            lines.append(f"- {days_since // 7} weeks ago")

    return "\n".join(lines)


def _format_detailed(context: TemporalContext) -> str:
    """Detailed format for system prompt.

    Args:
        context: Temporal context

    Returns:
        Formatted string
    """
    lines = ["## F1 Temporal Context", ""]

    # Current season and phase
    lines.append(f"**Current Season:** {context.current_season}")

    phase_display = context.season_phase.value.replace("_", " ").title()
    if context.season_phase == F1Season.IN_SEASON:
        lines.append(
            f"**Phase:** {phase_display} "
            f"(Round {context.races_completed} of {context.races_completed + context.races_remaining})"
        )
    else:
        lines.append(f"**Phase:** {phase_display}")

    lines.append("")

    # Current race weekend (if any)
    if context.current_weekend:
        lines.extend(_format_current_weekend_detailed(context.current_weekend, context.current_time_utc))
        lines.append("")

    # Next race (if not current weekend)
    if context.next_race and not context.current_weekend:
        lines.append(f"**Next Race:** {context.next_race.event_name}")
        lines.append(
            f"- Round {context.next_race.round_number} in {context.next_race.location}, {context.next_race.country}"
        )
        lines.append(f"- Event Date: {context.next_race.event_date.strftime('%B %d, %Y')}")

        if context.days_until_next_race is not None:
            lines.append(f"- Days Until Weekend: {context.days_until_next_race}")

        if context.next_race.is_sprint_weekend:
            lines.append("- Format: Sprint weekend")

        # Show upcoming sessions
        if context.next_race.all_sessions:
            lines.append("- Upcoming Sessions:")
            for session in context.next_race.all_sessions[:3]:  # Show first 3 sessions
                local_time = session.date_local.strftime("%A %H:%M local")
                lines.append(f"  - {session.name}: {local_time}")

        lines.append("")

    # Last completed race
    if context.last_completed_race:
        lines.append(
            f"**Last Completed Race:** {context.last_completed_race.event_name} "
            f"(Round {context.last_completed_race.round_number})"
        )
        lines.append(f"- Location: {context.last_completed_race.location}, {context.last_completed_race.country}")
        lines.append(f"- Date: {context.last_completed_race.event_date.strftime('%B %d, %Y')}")

        days_since = (context.current_time_utc - context.last_completed_race.event_date).days
        lines.append(f"- {days_since} day{'s' if days_since != 1 else ''} ago")

    return "\n".join(lines)


def _format_current_weekend(weekend: "RaceWeekendContext") -> list[str]:
    """Format current race weekend for normal verbosity.

    Args:
        weekend: Race weekend context

    Returns:
        List of formatted lines
    """
    lines = [f"**ACTIVE RACE WEEKEND: {weekend.event_name}**"]
    lines.append(f"- Round {weekend.round_number} in {weekend.location}, {weekend.country}")

    if weekend.is_sprint_weekend:
        lines.append("- Event Format: Sprint weekend")

    # Current session
    if weekend.current_session:
        lines.append("")
        if weekend.current_session.is_live:
            lines.append(f"**Current Session:** {weekend.current_session.name} ⚡ LIVE")
            if weekend.current_session.minutes_since:
                lines.append(f"- Started {weekend.current_session.minutes_since} minutes ago")
        else:
            lines.append(f"**Recent Session:** {weekend.current_session.name}")
            if weekend.current_session.minutes_since:
                hours = weekend.current_session.minutes_since // 60
                mins = weekend.current_session.minutes_since % 60
                if hours > 0:
                    lines.append(f"- Completed {hours}h {mins}m ago")
                else:
                    lines.append(f"- Completed {mins} minutes ago")

    # Next session
    if weekend.next_session:
        lines.append("")
        lines.append(f"**Next Session:** {weekend.next_session.name}")
        local_time = weekend.next_session.date_local.strftime("%A, %B %d at %H:%M local")
        lines.append(f"- Scheduled: {local_time}")

        if weekend.next_session.minutes_until:
            hours = weekend.next_session.minutes_until // 60
            mins = weekend.next_session.minutes_until % 60

            if hours < 1:
                lines.append(f"- {mins} minutes until start")
            elif hours < 24:
                lines.append(f"- {hours} hours, {mins} minutes until start")
            else:
                days = hours // 24
                remaining_hours = hours % 24
                lines.append(f"- {days} day{'s' if days != 1 else ''}, {remaining_hours} hours until start")

    return lines


def _format_current_weekend_detailed(weekend: "RaceWeekendContext", current_time) -> list[str]:
    """Format current race weekend for detailed verbosity.

    Args:
        weekend: Race weekend context
        current_time: Current time (UTC)

    Returns:
        List of formatted lines
    """
    lines = [f"**ACTIVE RACE WEEKEND: {weekend.event_name}**"]
    lines.append(f"- Round {weekend.round_number} in {weekend.location}, {weekend.country}")
    lines.append(f"- Event Date: {weekend.event_date.strftime('%B %d, %Y')}")

    if weekend.is_sprint_weekend:
        lines.append("- Event Format: Sprint weekend")
    else:
        lines.append("- Event Format: Conventional weekend")

    # Current session
    if weekend.current_session:
        lines.append("")
        if weekend.current_session.is_live:
            lines.append(f"**⚡ LIVE SESSION: {weekend.current_session.name}**")
            if weekend.current_session.minutes_since:
                lines.append(f"- Started {weekend.current_session.minutes_since} minutes ago")
            lines.append(f"- Session Type: {weekend.current_session.session_type}")
        else:
            lines.append(f"**Recent Session:** {weekend.current_session.name}")
            if weekend.current_session.minutes_since:
                lines.append(f"- Completed {weekend.current_session.minutes_since} minutes ago")

    # Next session
    if weekend.next_session:
        lines.append("")
        lines.append(f"**Next Session:** {weekend.next_session.name}")
        utc_time = weekend.next_session.date_utc.strftime("%H:%M UTC")
        local_time = weekend.next_session.date_local.strftime("%H:%M local")
        lines.append(f"- Scheduled: {local_time} ({utc_time})")

        if weekend.next_session.minutes_until:
            hours = weekend.next_session.minutes_until // 60
            mins = weekend.next_session.minutes_until % 60
            lines.append(f"- Time Until Start: {hours}h {mins}m")

    # All weekend sessions
    lines.append("")
    lines.append("**Weekend Sessions:**")
    for session in weekend.all_sessions:
        if session.is_recent or (session.minutes_since and session.minutes_since < 1440):
            status = "✓ Completed"
        elif session.is_live:
            status = "⚡ LIVE NOW"
        elif session.minutes_until and session.minutes_until < 120:
            status = "⏳ Starting soon"
        elif session.minutes_until:
            status = f"⏭ {session.date_local.strftime('%A %H:%M local')}"
        else:
            status = "Upcoming"

        lines.append(f"  {status} - {session.name}")

    return lines


def format_as_text(context: TemporalContext) -> str:
    """Format temporal context as human-readable text (for CLI display).

    Args:
        context: Temporal context

    Returns:
        Formatted text
    """
    lines = ["=" * 60]
    lines.append("F1 TEMPORAL CONTEXT")
    lines.append("=" * 60)
    lines.append("")

    # Basic info
    lines.append(f"Current Time (UTC): {context.current_time_utc.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Season: {context.current_season}")
    lines.append(f"Phase: {context.season_phase.value.replace('_', ' ').title()}")
    lines.append(f"Races Completed: {context.races_completed}")
    lines.append(f"Races Remaining: {context.races_remaining}")
    lines.append("")

    # Current weekend
    if context.current_weekend:
        lines.append("-" * 60)
        lines.append("CURRENT RACE WEEKEND")
        lines.append("-" * 60)
        lines.append(f"Event: {context.current_weekend.event_name}")
        lines.append(f"Round: {context.current_weekend.round_number}")
        lines.append(f"Location: {context.current_weekend.location}, {context.current_weekend.country}")
        lines.append(f"Date: {context.current_weekend.event_date.strftime('%B %d, %Y')}")
        lines.append(f"Format: {'Sprint' if context.current_weekend.is_sprint_weekend else 'Conventional'}")

        if context.current_weekend.current_session:
            lines.append("")
            status = "LIVE" if context.current_weekend.current_session.is_live else "Recent"
            lines.append(f"Current Session ({status}): {context.current_weekend.current_session.name}")

        if context.current_weekend.next_session:
            lines.append(f"Next Session: {context.current_weekend.next_session.name}")
            scheduled_time = context.current_weekend.next_session.date_local.strftime("%A, %B %d at %H:%M local")
            lines.append(f"  Scheduled: {scheduled_time}")

        lines.append("")

    # Next race
    if context.next_race:
        lines.append("-" * 60)
        lines.append("NEXT RACE")
        lines.append("-" * 60)
        lines.append(f"Event: {context.next_race.event_name}")
        lines.append(f"Round: {context.next_race.round_number}")
        lines.append(f"Location: {context.next_race.location}, {context.next_race.country}")
        lines.append(f"Date: {context.next_race.event_date.strftime('%B %d, %Y')}")

        if context.days_until_next_race is not None:
            lines.append(f"Days Until Race Weekend: {context.days_until_next_race}")

        lines.append("")

    # Last completed race
    if context.last_completed_race:
        lines.append("-" * 60)
        lines.append("LAST COMPLETED RACE")
        lines.append("-" * 60)
        lines.append(f"Event: {context.last_completed_race.event_name}")
        lines.append(f"Round: {context.last_completed_race.round_number}")
        lines.append(f"Location: {context.last_completed_race.location}, {context.last_completed_race.country}")
        lines.append(f"Date: {context.last_completed_race.event_date.strftime('%B %d, %Y')}")

        days_since = (context.current_time_utc - context.last_completed_race.event_date).days
        lines.append(f"Days Since: {days_since}")

        lines.append("")

    # Cache info
    lines.append("-" * 60)
    lines.append("CACHE INFO")
    lines.append("-" * 60)
    lines.append(f"Cached At: {context.cache_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append(f"TTL: {context.ttl_seconds} seconds ({context.ttl_seconds // 60} minutes)")

    lines.append("=" * 60)

    return "\n".join(lines)
