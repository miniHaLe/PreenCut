#!/usr/bin/env python3
"""
Test runner for all PreenCut tests.
This script runs all test files in the tests directory.
"""

import os
import sys
import subprocess
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_test_file(test_file):
    """Run a single test file and return results"""
    print(f"\n{'='*60}")
    print(f"🧪 Running: {test_file}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        # Run the test file
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True,
            text=True,
            cwd=project_root
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
            
        success = result.returncode == 0
        
        print(f"\n{'✅ PASSED' if success else '❌ FAILED'} - {test_file} ({duration:.2f}s)")
        
        return {
            'file': test_file,
            'success': success,
            'duration': duration,
            'output': result.stdout,
            'error': result.stderr
        }
        
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"❌ EXCEPTION in {test_file}: {str(e)}")
        
        return {
            'file': test_file,
            'success': False,
            'duration': duration,
            'output': '',
            'error': str(e)
        }

def main():
    """Main test runner"""
    print("🚀 PreenCut Test Suite")
    print("=" * 60)
    print("Running all tests in the tests directory...")
    
    # Find all test files
    tests_dir = Path(__file__).parent
    test_files = list(tests_dir.glob("test_*.py"))
    
    if not test_files:
        print("❌ No test files found!")
        return False
    
    print(f"Found {len(test_files)} test files:")
    for test_file in test_files:
        print(f"  - {test_file.name}")
    
    # Run all tests
    results = []
    start_time = time.time()
    
    for test_file in test_files:
        result = run_test_file(str(test_file))
        results.append(result)
    
    end_time = time.time()
    total_duration = end_time - start_time
    
    # Print summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for r in results if r['success'])
    failed = len(results) - passed
    
    print(f"Total Tests: {len(results)}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"⏱️  Total Time: {total_duration:.2f}s")
    
    print(f"\n📋 Detailed Results:")
    for result in results:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        print(f"  {status} - {result['file']} ({result['duration']:.2f}s)")
        if not result['success'] and result['error']:
            print(f"       Error: {result['error'][:100]}...")
    
    if failed > 0:
        print(f"\n⚠️  {failed} test(s) failed. Check the detailed output above.")
        return False
    else:
        print(f"\n🎉 All tests passed!")
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
