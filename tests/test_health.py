"""Unit tests for system health and diagnostics checks."""

import unittest

from src.utils.health import HealthChecker


class TestHealthChecker(unittest.TestCase):
    """Verifies automated status probes across all subsystem components."""

    def test_database_check(self):
        """Database probe should report accessibility."""
        res = HealthChecker.check_database()
        self.assertIn(res.status, ("healthy", "degraded"))
        self.assertIn("path", res.details)

    def test_filesystem_check(self):
        """Filesystem probe should confirm write permissions."""
        res = HealthChecker.check_filesystem()
        self.assertEqual(res.status, "healthy")
        self.assertGreater(len(res.details.get("directories", [])), 0)

    def test_configuration_check(self):
        """Configuration probe should report demo mode or production status."""
        res = HealthChecker.check_configuration()
        self.assertIn(res.status, ("healthy", "degraded"))
        self.assertIn("environment", res.details)

    def test_runtime_check(self):
        """Runtime probe should report Python version and OS platform."""
        res = HealthChecker.check_runtime()
        self.assertEqual(res.status, "healthy")
        self.assertIn("python_version", res.details)

    def test_run_all_checks(self):
        """run_all_checks should return comprehensive HealthStatus report."""
        overall = HealthChecker.run_all_checks()
        self.assertIn(overall.overall_status, ("healthy", "degraded"))
        self.assertIn("database", overall.components)
        self.assertIn("filesystem", overall.components)
        self.assertIn("configuration", overall.components)
        self.assertIn("runtime", overall.components)
        self.assertTrue(overall.is_healthy)


if __name__ == "__main__":
    unittest.main()
