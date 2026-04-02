"""End turn tool — signals the agent loop to stop."""


def end_turn(summary: str) -> str:
    """
    Signal that the agent's turn is complete.

    This is a sentinel tool: when the model calls it, the agent_loop
    interprets it as a stop condition and breaks out of the loop.

    Args:
        summary: Brief description of what was accomplished.

    Returns:
        Acknowledgment string (sent back to model as tool result).
    """
    return f"Turn ended. Summary: {summary}"
