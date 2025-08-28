#!/usr/bin/env python3
"""
Test runner script for PM Co-Pilot backend.
Provides easy commands to run different test suites.
"""

import subprocess
import sys
import os
import argparse

def run_command(command, description):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"🔄 {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(command, shell=True, check=True, cwd='backend' if os.path.exists('backend') else '.')
        print(f"✅ {description} - SUCCESS")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - FAILED (exit code {e.returncode})")
        return False

def main():
    parser = argparse.ArgumentParser(description="Run PM Co-Pilot backend tests")
    parser.add_argument('--critical', action='store_true', help='Run only critical email flow tests')
    parser.add_argument('--regression', action='store_true', help='Run only regression tests')
    parser.add_argument('--integration', action='store_true', help='Run only integration tests')
    parser.add_argument('--all', action='store_true', help='Run all tests')
    parser.add_argument('--coverage', action='store_true', help='Run tests with coverage report')
    parser.add_argument('--install-deps', action='store_true', help='Install test dependencies first')
    
    args = parser.parse_args()
    
    if args.install_deps:
        if not run_command("pip install -r requirements.txt", "Installing main dependencies"):
            return 1
        if not run_command("pip install -r requirements-test.txt", "Installing test dependencies"):
            return 1
    
    # Change to backend directory if we're in root
    if os.path.exists('backend') and os.getcwd().endswith('PM Co-Pilot'):
        os.chdir('backend')
    
    success = True
    
    if args.critical or args.all:
        # Run critical email flow tests
        success &= run_command(
            "pytest tests/test_email_data_processing_regression.py tests/test_email_count_verification.py -v",
            "Critical Email Flow Tests"
        )
    
    if args.regression or args.all:
        # Run regression tests
        success &= run_command(
            "pytest -m regression -v",
            "Regression Tests"
        )
    
    if args.integration or args.all:
        # Run integration tests
        success &= run_command(
            "pytest tests/test_email_integration_flow.py -v",
            "Integration Tests"
        )
    
    if args.coverage:
        # Run all tests with coverage
        success &= run_command(
            "pytest tests/test_email_*.py --cov=models --cov=services --cov-report=html --cov-report=term-missing",
            "All Tests with Coverage"
        )
        
        if success:
            print(f"\n📊 Coverage report generated in htmlcov/index.html")
    
    if not any([args.critical, args.regression, args.integration, args.all, args.coverage]):
        # Default: run critical tests
        success &= run_command(
            "pytest tests/test_email_data_processing_regression.py tests/test_email_count_verification.py -v",
            "Default - Critical Email Flow Tests"
        )
    
    print(f"\n{'='*60}")
    if success:
        print("🎉 ALL TESTS PASSED!")
        print("The email flow is working correctly and protected against regressions.")
    else:
        print("💥 SOME TESTS FAILED!")
        print("Please fix the failing tests before pushing changes.")
    print(f"{'='*60}\n")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())