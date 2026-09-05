"""Validate codex-review results and derive their Phase-4 findings."""


VALID_SEVERITIES = {"critical", "high", "medium", "low"}


def validate_result(value):
    """Raise ValueError unless value exactly matches the review result contract."""
    if not isinstance(value, dict) or set(value) != {"findings"}:
        raise ValueError("result must be an object containing only findings")
    findings = value["findings"]
    if not isinstance(findings, list):
        raise ValueError("result.findings must be an array")
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict) or set(finding) != {"severity", "title", "file"}:
            raise ValueError(f"result.findings[{index}] has invalid keys")
        if finding["severity"] not in VALID_SEVERITIES:
            raise ValueError(f"result.findings[{index}].severity is invalid")
        for field in ("title", "file"):
            if not isinstance(finding[field], str) or not finding[field]:
                raise ValueError(f"result.findings[{index}].{field} must be a non-empty string")
    return value


def derive_findings(result_obj):
    """Return Phase-4 findings in the result's original order, preserving duplicates."""
    validate_result(result_obj)
    return [
        {
            "severity": item["severity"].upper(),
            "source": "codex-review",
            "title": f'{item["title"]} ({item["file"]})',
            "file": item["file"],
        }
        for item in result_obj["findings"]
    ]
