#!/usr/bin/env python3
"""
QA Intelligence Test Runner
Comprehensive test suite for validating core functionality and preventing regressions
"""

import sys
import subprocess
import os
from pathlib import Path


def run_command(cmd: list, description: str) -> bool:
    """Run a command and return success status"""
    print(f"\n🔄 {description}")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent)
        
        if result.returncode == 0:
            print(f"✅ {description} - SUCCESS")
            return True
        else:
            print(f"❌ {description} - FAILED")
            print(f"STDOUT:\n{result.stdout}")
            print(f"STDERR:\n{result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False


def main():
    """Run comprehensive test suite"""
    print("🧪 QA Intelligence Test Suite")
    print("=" * 50)
    print("Testing core functionality and regression safety")
    
    # Ensure we're in the right directory
    os.chdir(Path(__file__).parent)
    
    # Test commands with descriptions
    test_commands = [
        {
            "cmd": ["python", "-m", "pytest", "tests/", "-v", "--tb=short"],
            "desc": "Running full test suite with verbose output",
            "critical": True
        },
        {
            "cmd": ["python", "-m", "pytest", "tests/test_config_validation.py", "-v"],
            "desc": "Testing configuration validation contract",
            "critical": True
        },
        {
            "cmd": ["python", "-m", "pytest", "tests/test_instructions_normalization.py", "-v"],
            "desc": "Testing instructions normalization bug fix",
            "critical": True
        },
        {
            "cmd": ["python", "-m", "pytest", "tests/test_tools_validation.py", "-v"],
            "desc": "Testing tools validation improvements",
            "critical": True
        },
        {
            "cmd": ["python", "-m", "pytest", "tests/test_qa_agent.py", "-v"],
            "desc": "Testing QA Agent core functionality",
            "critical": True
        },
        {
            "cmd": ["python", "-m", "pytest", "tests/", "--cov=src", "--cov-report=term-missing"],
            "desc": "Running tests with coverage analysis",
            "critical": False
        }
    ]
    
    results = []
    critical_failures = []
    
    for test in test_commands:
        success = run_command(test["cmd"], test["desc"])
        results.append({"test": test["desc"], "success": success, "critical": test["critical"]})
        
        if test["critical"] and not success:
            critical_failures.append(test["desc"])
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for r in results if r["success"])
    total = len(results)
    
    print(f"Total tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    
    if critical_failures:
        print(f"\n❌ CRITICAL FAILURES ({len(critical_failures)}):")
        for failure in critical_failures:
            print(f"   • {failure}")
        print("\n🚨 Critical tests must pass for system stability!")
        return 1
    
    if passed == total:
        print(f"\n🎉 ALL TESTS PASSED!")
        print("✅ Core functionality validated")
        print("✅ Regression safety confirmed")
        print("✅ System ready for production")
        return 0
    else:
        print(f"\n⚠️  Some non-critical tests failed")
        print("🔍 Review test output for details")
        return 0


if __name__ == "__main__":
    sys.exit(main())
