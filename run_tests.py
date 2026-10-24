"""FaultSense Test Suite Runner.

Discovers and runs all unit tests, providing a detailed summary of results.
"""

import sys
import time
import unittest


def run_all_tests() -> int:
    """Discovers and executes all tests in the 'tests' directory."""
    print("=" * 70)
    print("FAULTSENSE UNIT TEST EXECUTION SUITE")
    print("=" * 70)

    loader = unittest.TestLoader()
    suite = loader.discover(start_dir="tests", pattern="test_*.py")

    start_time = time.time()
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    elapsed = time.time() - start_time

    print("\n" + "=" * 70)
    print("TEST EXECUTION SUMMARY")
    print("=" * 70)
    print(f"Total Tests Run : {result.testsRun}")
    print(f"Successful Tests: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures        : {len(result.failures)}")
    print(f"Errors          : {len(result.errors)}")
    print(f"Execution Time  : {elapsed:.3f} seconds")
    print("=" * 70)

    if result.wasSuccessful():
        print(">>> ALL TESTS PASSED SUCCESSFULLY! <<<")
        return 0
    else:
        print(">>> TEST FAILURES DETECTED! <<<")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
