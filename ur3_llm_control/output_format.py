"""Human-readable formatting shared by the command-plan and execution views."""


def format_step(step):
    """Format a validated skill dictionary as pick(...), place(...), or home()."""
    skill = step["skill"]
    if skill == "pick":
        return f"pick({step['object']})"
    if skill == "place":
        return f"place({step['object']}, {step['zone']})"
    if skill == "home":
        return "home()"
    raise ValueError(f"Cannot format unknown skill: {skill}")


def format_plan(steps):
    """Format an ordered sequence of validated skill dictionaries."""
    return "\n".join(f"{index}. {format_step(step)}"
                     for index, step in enumerate(steps, start=1))


def format_execution(results):
    """Format SkillExecutor result entries with the same skill spelling."""
    return "\n".join(
        f"{format_step(entry['step'])} ........ {entry['status']}"
        for entry in results
    )
