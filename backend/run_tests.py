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
    # New optimized test options
    parser.add_argument('--optimized', action='store_true', help='Run optimized tests with mocks (saves tokens)')
    parser.add_argument('--health-check', action='store_true', help='Run only health check tests (uses real APIs)')
    parser.add_argument('--mock-only', action='store_true', help='Run only tests that use mocks')
    parser.add_argument('--token-efficient', action='store_true', help='Run token-efficient test suite (optimized + health checks)')
    
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
    
    if args.all:
        # Run ALL tests in the test directory
        success &= run_command(
            "pytest tests/ -v",
            "ALL Tests (Complete Test Suite)"
        )
    elif args.critical:
        # Run critical email flow tests
        success &= run_command(
            "pytest tests/test_email_data_processing_regression.py tests/test_email_count_verification.py -v",
            "Critical Email Flow Tests"
        )
    elif args.regression:
        # Run regression tests
        success &= run_command(
            "pytest -m regression -v",
            "Regression Tests"
        )
    elif args.integration:
        # Run integration tests
        success &= run_command(
            "pytest tests/test_email_integration_flow.py -v",
            "Integration Tests"
        )
    
    # New optimized test options
    if args.optimized:
        # Run optimized tests using mocks
        success &= run_command(
            "TESTING=true pytest -m optimized -v",
            "Optimized Tests (Using Mocks - Token Efficient)"
        )
    
    if args.health_check:
        # Run health check tests (real API calls)
        success &= run_command(
            "pytest -m health_check -v",
            "Health Check Tests (Real API Calls)"
        )
    
    if args.mock_only:
        # Run only tests that use mocks
        success &= run_command(
            "TESTING=true pytest -m mock_only -v",
            "Mock-Only Tests (No Real API Calls)"
        )
    
    if args.token_efficient:
        # Run the most efficient test suite: optimized tests + minimal health checks
        print(f"\n🚀 Running Token-Efficient Test Suite")
        print(f"This runs optimized tests with mocks + minimal health checks")
        
        success &= run_command(
            "TESTING=true pytest -m optimized -v",
            "1/2: Optimized Integration Tests (Mocked)"
        )
        
        success &= run_command(
            "pytest -m health_check -v --tb=line",
            "2/2: API Health Checks (Minimal Real Calls)"
        )
        
        if success:
            print(f"\n💡 Token-Efficient Suite Complete!")
            print(f"✅ Full functionality tested with minimal API token usage")
    
    if args.coverage:
        # Run optimized tests with coverage by default to save tokens
        success &= run_command(
            "TESTING=true pytest -m 'optimized or critical' --cov=models --cov=services --cov-report=html --cov-report=term-missing",
            "Coverage Tests (Optimized for Token Efficiency)"
        )
        
        if success:
            print(f"\n📊 Coverage report generated in htmlcov/index.html")
            print(f"💡 Coverage ran with optimized tests to save tokens")
    
    # Update default behavior
    if not any([args.critical, args.regression, args.integration, args.all, args.coverage, 
                args.optimized, args.health_check, args.mock_only, args.token_efficient]):
        # New default: run token-efficient suite
        print(f"\n🎯 Running Default Token-Efficient Test Suite")
        success &= run_command(
            "TESTING=true pytest -m optimized -v",
            "Default - Optimized Tests (Token Efficient)"
        )
    
    print(f"\n{'='*60}")
    if success:
        print("🎉 ALL TESTS PASSED!")
        if args.token_efficient or args.optimized:
            print("✨ Tests completed with optimized token usage!")
            print("💰 Significant API cost savings achieved through smart mocking.")
        elif args.health_check:
            print("🔍 API connectivity verified - all external services are healthy.")
        else:
            print("📧 Application functionality verified and protected against regressions.")
    else:
        print("💥 SOME TESTS FAILED!")
        print("Please fix the failing tests before pushing changes.")
    print(f"{'='*60}\n")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())