"""Data quality orchestrator for running checks.

Coordinates data fetching and check execution across variables.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import pandas as pd

from raglite.forecasting.data_quality.check_result import CheckResult, CheckStatus
from raglite.forecasting.data_quality.checks import (
    check_effective_frequency,
    check_entity_contamination,
    check_entity_coverage,
    check_missing_data_pattern,
    check_robust_outliers,
    check_time_index_integrity,
    check_unit_consistency,
    check_value_range,
)
from raglite.forecasting.data_quality.config import (
    EntityMatchMode,
    VariableQualityConfig,
    get_variable_config,
    list_configured_variables,
)
from raglite.shared.clients import get_postgresql_connection
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


@dataclass
class VariableAuditResult:
    """Audit results for a single variable.

    Attributes:
        variable: Variable name
        checks: List of individual check results
        passed: Number of passed checks
        warned: Number of warned checks
        failed: Number of failed checks
        skipped: Number of skipped checks
        status: Overall status (PASS/WARN/FAIL based on worst result)
    """

    variable: str
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for c in self.checks if c.status == CheckStatus.PASS)

    @property
    def warned(self) -> int:
        return sum(1 for c in self.checks if c.status == CheckStatus.WARN)

    @property
    def failed(self) -> int:
        return sum(1 for c in self.checks if c.status == CheckStatus.FAIL)

    @property
    def skipped(self) -> int:
        return sum(1 for c in self.checks if c.status == CheckStatus.SKIP)

    @property
    def status(self) -> CheckStatus:
        if self.failed > 0:
            return CheckStatus.FAIL
        if self.warned > 0:
            return CheckStatus.WARN
        return CheckStatus.PASS


@dataclass
class AuditResult:
    """Complete audit results across all variables.

    Attributes:
        timestamp: When audit was run
        runtime_seconds: Total execution time
        variables_audited: Number of variables checked
        total_checks: Total individual checks run
        results: Per-variable results
    """

    timestamp: str
    runtime_seconds: float
    variables_audited: int
    total_checks: int
    results: list[VariableAuditResult] = field(default_factory=list)

    @property
    def total_passed(self) -> int:
        return sum(r.passed for r in self.results)

    @property
    def total_warned(self) -> int:
        return sum(r.warned for r in self.results)

    @property
    def total_failed(self) -> int:
        return sum(r.failed for r in self.results)

    @property
    def total_skipped(self) -> int:
        return sum(r.skipped for r in self.results)

    @property
    def pass_rate(self) -> float:
        actionable = self.total_passed + self.total_warned + self.total_failed
        if actionable == 0:
            return 1.0
        return self.total_passed / actionable

    @property
    def variables_passed(self) -> int:
        return sum(1 for r in self.results if r.status == CheckStatus.PASS)

    @property
    def variables_warned(self) -> int:
        return sum(1 for r in self.results if r.status == CheckStatus.WARN)

    @property
    def variables_failed(self) -> int:
        return sum(1 for r in self.results if r.status == CheckStatus.FAIL)


# Type alias for async check functions
CheckFunction = Callable[[str, VariableQualityConfig, Any], Awaitable[CheckResult]]

# All available checks
ALL_CHECKS: list[tuple[str, CheckFunction]] = [
    ("entity_contamination", check_entity_contamination),
    ("entity_coverage", check_entity_coverage),
    ("value_range", check_value_range),
    ("unit_consistency", check_unit_consistency),
    ("robust_outliers", check_robust_outliers),
    ("effective_frequency", check_effective_frequency),
    ("time_index_integrity", check_time_index_integrity),
    ("missing_data_pattern", check_missing_data_pattern),
]


class DataQualityOrchestrator:
    """Orchestrates data quality checks across variables."""

    def __init__(self) -> None:
        """Initialize orchestrator."""
        self._data_cache: dict[str, pd.DataFrame] = {}

    async def fetch_data(self, variable: str, config: VariableQualityConfig) -> pd.DataFrame | None:
        """Fetch data for a variable from database.

        Args:
            variable: Variable name
            config: Variable quality configuration

        Returns:
            DataFrame with date, value columns or None if no data
        """
        # Check cache first
        cache_key = f"{variable}_{config.entity.required_entity}"
        if cache_key in self._data_cache:
            return self._data_cache[cache_key]

        # External-only variables need different handling
        if config.is_external_only:
            data = await self._fetch_external_data(variable, config)
        else:
            data = await self._fetch_secil_data(variable, config)

        self._data_cache[cache_key] = data
        return data

    async def _fetch_secil_data(
        self, variable: str, config: VariableQualityConfig
    ) -> pd.DataFrame | None:
        """Fetch SECIL financial data from PostgreSQL."""
        conn = get_postgresql_connection()
        cursor = conn.cursor()

        try:
            # Build metric condition
            aliases = config.db_metric_aliases or [variable]
            metric_condition = " OR ".join(["metric ILIKE %s"] * len(aliases))
            metric_params = [f"%{alias}%" for alias in aliases]

            # Build entity condition
            entity_condition = "TRUE"
            entity_params = []
            if config.entity.required_entity:
                if config.entity.match_mode == EntityMatchMode.EXACT:
                    entity_condition = "entity = %s"
                    entity_params = [config.entity.required_entity]
                elif config.entity.match_mode == EntityMatchMode.ILIKE:
                    entity_condition = "entity ILIKE %s"
                    entity_params = [f"%{config.entity.required_entity}%"]

            query = f"""  # nosec
                SELECT period, value, entity, metric
                FROM financial_tables
                WHERE ({metric_condition})
                AND {entity_condition}
                AND period IS NOT NULL
                ORDER BY period
            """

            cursor.execute(query, metric_params + entity_params)
            rows = cursor.fetchall()

            if not rows:
                logger.warning(
                    "No data found for variable",
                    extra={"variable": variable, "aliases": aliases},
                )
                return None

            df = pd.DataFrame(rows, columns=["period", "value", "entity", "metric"])

            # Parse period to date
            df["date"] = pd.to_datetime(df["period"], format="%b-%y", errors="coerce")

            logger.info(
                "Fetched SECIL data",
                extra={
                    "variable": variable,
                    "rows": len(df),
                    "date_parsed": df["date"].notna().sum(),
                },
            )

            return df

        except Exception as e:
            logger.error(
                "Failed to fetch SECIL data",
                extra={"variable": variable, "error": str(e)},
            )
            return None
        finally:
            cursor.close()

    async def _fetch_external_data(
        self, variable: str, config: VariableQualityConfig
    ) -> pd.DataFrame | None:
        """Fetch external data from external_data_points table."""
        conn = get_postgresql_connection()
        cursor = conn.cursor()

        try:
            # Map variable name to external source/metric
            # This mapping should match EXTERNAL_METRIC_MAPPINGS in metrics.py
            source_mapping = {
                "ttf_gas_price": ("ICE_TTF_Gas", "settlement_price"),
                "petcoke_price": ("ICE_API2_Coal", "settlement_price"),
                "co2_eua_price": ("CO2_EUA", "co2_eua_price"),
            }

            if variable in source_mapping:
                source_name, metric_name = source_mapping[variable]
                query = """
                    SELECT edp.date, edp.value
                    FROM external_data_points edp
                    JOIN external_data_sources eds ON edp.source_id = eds.id
                    WHERE eds.source_name = %s
                    AND edp.metric_name = %s
                    AND edp.deleted_at IS NULL
                    ORDER BY edp.date
                """
                cursor.execute(query, [source_name, metric_name])
            else:
                # For regressor data, check regressor_cache table
                query = """
                    SELECT date, value
                    FROM regressor_cache
                    WHERE regressor_name = %s
                    ORDER BY date
                """
                cursor.execute(query, [variable])

            rows = cursor.fetchall()

            if not rows:
                logger.warning(
                    "No external data found for variable",
                    extra={"variable": variable},
                )
                return None

            df = pd.DataFrame(rows, columns=["date", "value"])
            df["date"] = pd.to_datetime(df["date"], errors="coerce")

            logger.info(
                "Fetched external data",
                extra={"variable": variable, "rows": len(df)},
            )

            return df

        except Exception as e:
            logger.error(
                "Failed to fetch external data",
                extra={"variable": variable, "error": str(e)},
            )
            return None
        finally:
            cursor.close()

    async def run_variable_checks(
        self,
        variable: str,
        config: VariableQualityConfig,
    ) -> VariableAuditResult:
        """Run all checks for a single variable.

        Args:
            variable: Variable name
            config: Variable quality configuration

        Returns:
            VariableAuditResult with all check results
        """
        result = VariableAuditResult(variable=variable)

        # Fetch data once for all checks
        data = await self.fetch_data(variable, config)

        for check_name, check_fn in ALL_CHECKS:
            # Skip if check is in skip list
            if check_name in config.checks_to_skip:
                result.checks.append(
                    CheckResult(
                        check_name=check_name,
                        status=CheckStatus.SKIP,
                        message="Check skipped by configuration",
                        variable=variable,
                    )
                )
                continue

            try:
                check_result = await check_fn(variable, config, data)
                result.checks.append(check_result)
            except Exception as e:
                logger.error(
                    "Check failed with exception",
                    extra={"variable": variable, "check": check_name, "error": str(e)},
                )
                result.checks.append(
                    CheckResult(
                        check_name=check_name,
                        status=CheckStatus.FAIL,
                        message=f"Check error: {e}",
                        variable=variable,
                        severity=3,
                    )
                )

        return result

    async def run_audit(
        self,
        variables: list[str] | None = None,
    ) -> AuditResult:
        """Run data quality audit across variables.

        Args:
            variables: List of variables to audit (None = all configured)

        Returns:
            AuditResult with complete audit data
        """
        import time

        start_time = time.time()

        # Default to all configured variables
        if variables is None:
            variables = list_configured_variables()

        results = []
        total_checks = 0

        for variable in variables:
            config = get_variable_config(variable)
            if config is None:
                logger.warning(
                    "No config found for variable, skipping",
                    extra={"variable": variable},
                )
                continue

            logger.info(
                "Auditing variable",
                extra={"variable": variable, "is_external": config.is_external_only},
            )

            var_result = await self.run_variable_checks(variable, config)
            results.append(var_result)
            total_checks += len(var_result.checks)

        runtime = time.time() - start_time

        audit_result = AuditResult(
            timestamp=datetime.now().isoformat(),
            runtime_seconds=runtime,
            variables_audited=len(results),
            total_checks=total_checks,
            results=results,
        )

        logger.info(
            "Audit complete",
            extra={
                "variables": len(results),
                "total_checks": total_checks,
                "pass_rate": f"{audit_result.pass_rate:.1%}",
                "runtime": f"{runtime:.1f}s",
            },
        )

        return audit_result

    def clear_cache(self) -> None:
        """Clear the data cache."""
        self._data_cache.clear()
