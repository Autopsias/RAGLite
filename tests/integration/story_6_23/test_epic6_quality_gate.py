"""Test Epic 6 Quality Gate: Final validation combining all acceptance criteria.

Story 6.23 - This is the ultimate pass/fail test for Epic 6.
"""

from __future__ import annotations

import json
import subprocess

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.preserve_collection,
    pytest.mark.slow,
    pytest.mark.xfail(
        reason="TDD RED phase - expected to fail until Story 6.23 implementation complete"
    ),
]


class TestEpic6QualityGate:
    """Epic 6 Quality Gate: Final validation combining all acceptance criteria.

    This is the ultimate pass/fail test for Epic 6.
    """

    @pytest.mark.slow
    def test_epic6_quality_gate_passes(self, validation_script_path, project_root):
        """TEST-EPIC6-QG: Epic 6 quality gate must pass.

        GIVEN: All stories 6.15-6.22 are implemented
        WHEN: Running full validation
        THEN: Quality gate passes (Variable Cost <8% AND 10/12 pass)
        """
        # Run full validation
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                str(validation_script_path),
                "--full",
                "--export-json",
                "--mcp-format",
                "--quiet",
            ],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=660,
        )

        json_output = None
        for line in result.stdout.strip().split("\n"):
            try:
                json_output = json.loads(line)
                break
            except json.JSONDecodeError:
                continue

        if json_output is None:
            pytest.fail("Could not parse validation output")

        # Check quality gate
        quality_gate = json_output.get("quality_gate", {})

        # EPIC 6 QUALITY GATE ASSERTION
        assert quality_gate.get("passed") is True, (
            f"EPIC 6 QUALITY GATE FAILED:\n"
            f"  - Variable Cost MAPE: {quality_gate.get('variable_cost_mape')}% (target: <8%)\n"
            f"  - Variables Passed: {quality_gate.get('actual_passed')}/{quality_gate.get('minimum_required')} required\n"
            f"  - Pass Rate: {json_output.get('pass_rate', 0):.1%}\n"
            f"Full results: {json.dumps(json_output, indent=2)}"
        )
