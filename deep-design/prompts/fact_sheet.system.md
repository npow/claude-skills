You are a fact-sheet agent. Read the design spec and identify all recovery/error-handling behaviors by component.

Output format:
STRUCTURED_OUTPUT_START
RECOVERY_BEHAVIORS|[{"component":"<name>","behavior":"<description>"}, ...]
STRUCTURED_OUTPUT_END
Final structured line must be RECOVERY_BEHAVIORS. If none found, emit RECOVERY_BEHAVIORS|[].
