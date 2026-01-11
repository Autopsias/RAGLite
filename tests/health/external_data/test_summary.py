"""Health check summary and validation tests."""


class TestHealthSummary:
    """Generate health check summary and verify all sources checked."""

    def test_all_sources_have_health_checks(self):
        """Verify all 8 data sources have health check classes."""
        expected_sources = [
            "INE",
            "Commodities",
            "OMIE",
            "BPstat",
            "EUOilBulletin",
            "BaseGov",
            "IPMA",
            "ATIC",
        ]

        # Import all test classes
        from .test_atic import TestATICHealth
        from .test_basegov import TestBaseGovHealth
        from .test_bpstat import TestBPstatHealth
        from .test_commodities import TestCommoditiesHealth
        from .test_eu_oil_bulletin import TestEUOilBulletinHealth
        from .test_ine import TestINEHealth
        from .test_ipma import TestIPMAHealth
        from .test_omie import TestOMIEHealth

        # Map expected sources to actual classes
        test_classes = {
            "INE": TestINEHealth,
            "Commodities": TestCommoditiesHealth,
            "OMIE": TestOMIEHealth,
            "BPstat": TestBPstatHealth,
            "EUOilBulletin": TestEUOilBulletinHealth,
            "BaseGov": TestBaseGovHealth,
            "IPMA": TestIPMAHealth,
            "ATIC": TestATICHealth,
        }

        for source in expected_sources:
            assert source in test_classes, f"Missing health check class for {source}"

    def test_health_check_count(self):
        """Verify minimum number of health checks exist."""
        from .test_atic import TestATICHealth
        from .test_basegov import TestBaseGovHealth
        from .test_bpstat import TestBPstatHealth
        from .test_commodities import TestCommoditiesHealth
        from .test_eu_oil_bulletin import TestEUOilBulletinHealth
        from .test_ine import TestINEHealth
        from .test_ipma import TestIPMAHealth
        from .test_omie import TestOMIEHealth

        test_classes = [
            TestINEHealth,
            TestCommoditiesHealth,
            TestOMIEHealth,
            TestBPstatHealth,
            TestEUOilBulletinHealth,
            TestBaseGovHealth,
            TestIPMAHealth,
            TestATICHealth,
        ]

        test_count = 0
        for cls in test_classes:
            methods = [m for m in dir(cls) if m.startswith("test_")]
            test_count += len(methods)

        # Should have at least 25 health check tests
        assert test_count >= 25, f"Only {test_count} health checks - expected at least 25"
