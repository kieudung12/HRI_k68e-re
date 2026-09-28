"""Policy for classifying student-specific natural-language requests."""


def classify_student_request(planner, command, strict_student_task, mapping, config_error=None):
    """Always classify natural-language intent, then fail closed without identity."""
    student_specific = bool(strict_student_task) or planner.classify_student_task(command)
    if student_specific and mapping is None:
        detail = config_error or "student identity is unavailable or invalid"
        raise ValueError("Student-specific request requires a valid student configuration: " + detail)
    return student_specific
