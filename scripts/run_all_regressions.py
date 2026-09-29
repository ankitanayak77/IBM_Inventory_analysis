"""
Master Regression Test Runner
-----------------------------
Executes the complete test suite across all development phases:
1. Phase 6:  Sales Module & Transactions
2. Phase 7:  Restock Module & Inbound Flow
3. Phase 8:  Inventory Management & Stock Status
4. Phase 9:  Product Movement Analytics & Velocity
5. Phase 10: Rule-Based Inventory Recommendations
6. Phase 11: Interactive Dashboard Charts & Visual Analytics
7. Phase 12: Normalized Power BI CSV Exports & Reports
8. Phase 13 Model: Power BI TMDL Architecture & Portable Paths
9. Phase 13 Tests: Power BI Metric Reconciliation & Measures
10. Phase 14 Routes: Full Application Route & Presentation Validation
11. Phase 14 Workflow: End-to-End Business Lifecycle (Sale -> Restock -> Cleanup)
12. Enterprise Auth: Sign-In, Sign-Up, RBAC, CSRF, Abuse Protection, Session Security
"""

import sys
import subprocess
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

TEST_SUITES = [
    ("Phase 6  - Sales Transactions", "scripts/test_phase6.py"),
    ("Phase 7  - Inbound Restocking", "scripts/test_phase7.py"),
    ("Phase 8  - Inventory Valuation", "scripts/test_phase8.py"),
    ("Phase 9  - Velocity Analytics", "scripts/test_phase9.py"),
    ("Phase 10 - Recommendation Engine", "scripts/test_phase10.py"),
    ("Phase 11 - Dashboard Visuals", "scripts/test_phase11.py"),
    ("Phase 12 - Reports & CSV Exports", "scripts/test_phase12.py"),
    ("Phase 13 - Power BI Architecture", "scripts/validate_phase13_model.py"),
    ("Phase 13 - Power BI Measures", "scripts/test_phase13.py"),
    ("Phase 14 - Route & Auth Validation", "scripts/test_route_validation.py"),
    ("Phase 14 - Business Lifecycle", "scripts/test_business_workflow.py"),
    ("Security - Enterprise Auth & RBAC", "scripts/test_auth.py"),
    ("Account  - User Profile & Management", "scripts/test_profile.py"),
]

def run_all():
    print("=" * 75)
    print("STARTING FULL MASTER REGRESSION TEST SUITE (13 TEST SUITES)")
    print("=" * 75)

    start_time = time.time()
    passed_count = 0
    failed_suites = []

    for name, script_path in TEST_SUITES:
        print(f"\n---> Running: {name} ({script_path})")
        t0 = time.time()
        res = subprocess.run([sys.executable, str(BASE_DIR / script_path)], capture_output=True, text=True)
        elapsed = time.time() - t0

        if res.returncode == 0:
            passed_count += 1
            print(f"     [PASS] {name} completed successfully in {elapsed:.2f}s")
        else:
            print(f"     [FAIL] {name} failed with exit code {res.returncode} in {elapsed:.2f}s")
            print("STDOUT:")
            print(res.stdout[-1000:] if len(res.stdout) > 1000 else res.stdout)
            print("STDERR:")
            print(res.stderr[-1000:] if len(res.stderr) > 1000 else res.stderr)
            failed_suites.append(name)

    total_time = time.time() - start_time
    print("\n" + "=" * 75)
    print("MASTER REGRESSION EXECUTION SUMMARY")
    print("=" * 75)
    print(f"Total Suites Executed: {len(TEST_SUITES)}")
    print(f"Total Suites Passed:   {passed_count}/{len(TEST_SUITES)}")
    print(f"Total Execution Time:  {total_time:.2f}s")

    if failed_suites:
        print(f"\nFAILED SUITES: {failed_suites}")
        sys.exit(1)
    else:
        print("\nALL 13 REGRESSION SUITES PASSED CLEANLY! (100% SUCCESS)")
        print("=" * 75)
        sys.exit(0)

if __name__ == "__main__":
    run_all()
