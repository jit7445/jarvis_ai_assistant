MAX_SUMMARY_CHARS = 3000


def clean(summary: str, limit: int = MAX_SUMMARY_CHARS) -> str:
    """Keep the note's own structure: model text cannot add headings."""
    lines = [line.lstrip("#").strip() if line.lstrip().startswith("#") else line.rstrip()
             for line in summary.strip().splitlines()]
    text = "\n".join(lines).strip()
    return text[:limit]
