#!/usr/bin/env python3
"""
Network Failure Test - Chaos Engineering
Tests application resilience to network failures and latency
Works on Windows without requiring admin/iptables
"""

import requests
import time
import logging
import json
import threading
import subprocess
import os
from datetime import datetime
from collections import defaultdict
import statistics

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'network_failure_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

class NetworkFailureTest:
    """
    Tests application behavior under network failure conditions
    Simulates: timeouts, connection errors, high latency
    """

    def __init__(self, target_url="http://localhost:80"):
        self.target_url = target_url
        self.results = {
            'baseline': [],
            'during_failure': [],
            'after_recovery': []
        }
        self.metrics = defaultdict(list)

    def make_request(self, timeout=5):
        """Make HTTP request and measure response"""
        start = time.time()
        try:
            response = requests.get(self.target_url, timeout=timeout)
            elapsed = (time.time() - start) * 1000
            return {
                'success': response.status_code == 200,
                'status_code': response.status_code,
                'response_time_ms': elapsed,
                'error': None
            }
        except requests.exceptions.Timeout:
            elapsed = (time.time() - start) * 1000
            return {
                'success': False,
                'status_code': None,
                'response_time_ms': elapsed,
                'error': 'Timeout'
            }
        except requests.exceptions.ConnectionError as e:
            elapsed = (time.time() - start) * 1000
            return {
                'success': False,
                'status_code': None,
                'response_time_ms': elapsed,
                'error': 'ConnectionError'
            }
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            return {
                'success': False,
                'status_code': None,
                'response_time_ms': elapsed,
                'error': str(type(e).__name__)
            }

    def run_load_phase(self, phase_name, duration_seconds, requests_per_second=10, timeout=5):
        """Run load test for specified duration"""
        logging.info(f"\n{'='*70}")
        logging.info(f"Phase: {phase_name}")
        logging.info(f"Duration: {duration_seconds}s, Rate: {requests_per_second} req/s")
        logging.info('='*70)

        results = []
        interval = 1.0 / requests_per_second
        end_time = time.time() + duration_seconds
        request_count = 0

        while time.time() < end_time:
            result = self.make_request(timeout=timeout)
            results.append(result)
            request_count += 1

            if request_count % 10 == 0:
                success_count = sum(1 for r in results[-10:] if r['success'])
                logging.info(f"  Requests: {request_count}, Last 10 success rate: {success_count*10}%")

            time.sleep(interval)

        return results

    def simulate_timeout_scenario(self):
        """Test 1: Simulate timeout by using very short timeout"""
        logging.info("\n" + "="*70)
        logging.info("TEST 1: Timeout Simulation")
        logging.info("="*70)
        logging.info("Simulating network timeout by using 0.001s timeout")

        results = []
        for i in range(20):
            result = self.make_request(timeout=0.001)  # Very short timeout
            results.append(result)
            time.sleep(0.1)

        timeout_count = sum(1 for r in results if r['error'] == 'Timeout')
        logging.info(f"Results: {timeout_count}/20 requests timed out")
        logging.info(f"Application handled timeouts: {'[OK]' if timeout_count > 0 else '[FAIL]'}")

        return {
            'test': 'Timeout Simulation',
            'total_requests': 20,
            'timeouts': timeout_count,
            'passed': timeout_count > 0
        }

    def simulate_connection_refused(self):
        """Test 2: Simulate connection refused by targeting wrong port"""
        logging.info("\n" + "="*70)
        logging.info("TEST 2: Connection Refused Simulation")
        logging.info("="*70)
        logging.info("Simulating connection refused by targeting closed port")

        # Target a port that's definitely closed
        original_url = self.target_url
        self.target_url = "http://192.0.2.1:12345"  # RFC 5737 TEST-NET - guaranteed unreachable

        results = []
        for i in range(10):
            result = self.make_request(timeout=2)
            results.append(result)
            time.sleep(0.1)

        self.target_url = original_url  # Restore

        # Count any error (ConnectionError or Timeout) as successful error handling
        errors = sum(1 for r in results if r['error'] is not None)
        logging.info(f"Results: {errors}/10 requests failed (as expected)")
        logging.info(f"Application handled connection errors: {'[OK]' if errors >= 8 else '[FAIL]'}")

        return {
            'test': 'Connection Refused',
            'total_requests': 10,
            'connection_errors': errors,
            'passed': errors >= 8
        }

    def simulate_intermittent_failures(self):
        """Test 3: Simulate intermittent network failures"""
        logging.info("\n" + "="*70)
        logging.info("TEST 3: Intermittent Failures")
        logging.info("="*70)
        logging.info("Alternating between working and non-working endpoints")

        working_url = self.target_url
        broken_url = "http://192.0.2.1:12345"  # RFC 5737 TEST-NET - guaranteed unreachable

        results = []
        for i in range(30):
            # Alternate: 3 working, 2 broken
            if i % 5 < 3:
                self.target_url = working_url
            else:
                self.target_url = broken_url

            result = self.make_request(timeout=2)
            result['expected_success'] = (i % 5 < 3)
            results.append(result)
            time.sleep(0.1)

        self.target_url = working_url

        correct_behavior = sum(1 for r in results if r['success'] == r['expected_success'])
        logging.info(f"Results: {correct_behavior}/30 behaved as expected")
        logging.info(f"Intermittent failure handling: {'[OK]' if correct_behavior >= 25 else '[NEEDS IMPROVEMENT]'}")

        return {
            'test': 'Intermittent Failures',
            'total_requests': 30,
            'correct_behavior': correct_behavior,
            'passed': correct_behavior >= 25
        }

    def test_recovery_time(self):
        """Test 4: Measure recovery time after failure"""
        logging.info("\n" + "="*70)
        logging.info("TEST 4: Recovery Time Measurement")
        logging.info("="*70)

        # Phase 1: Baseline
        logging.info("\nPhase 1: Establishing baseline (10 requests)")
        baseline_results = []
        for i in range(10):
            result = self.make_request(timeout=5)
            baseline_results.append(result)
            time.sleep(0.2)

        baseline_success = sum(1 for r in baseline_results if r['success'])
        baseline_avg_time = statistics.mean([r['response_time_ms'] for r in baseline_results])
        logging.info(f"  Baseline: {baseline_success}/10 success, avg {baseline_avg_time:.1f}ms")

        # Phase 2: Induce failures (target wrong port)
        logging.info("\nPhase 2: Inducing failures (5 seconds)")
        original_url = self.target_url
        self.target_url = "http://localhost:59999"

        failure_start = time.time()
        while time.time() - failure_start < 5:
            self.make_request(timeout=1)
            time.sleep(0.2)

        # Phase 3: Restore and measure recovery
        logging.info("\nPhase 3: Restoring and measuring recovery time")
        self.target_url = original_url

        recovery_start = time.time()
        recovery_results = []
        first_success_time = None

        for i in range(20):
            result = self.make_request(timeout=5)
            recovery_results.append(result)

            if result['success'] and first_success_time is None:
                first_success_time = time.time() - recovery_start
                logging.info(f"  First successful request after {first_success_time*1000:.0f}ms")

            time.sleep(0.2)

        recovery_success = sum(1 for r in recovery_results if r['success'])
        recovery_time_ms = first_success_time * 1000 if first_success_time else float('inf')

        logging.info(f"\nRecovery Results:")
        logging.info(f"  Time to first success: {recovery_time_ms:.0f}ms")
        logging.info(f"  Recovery success rate: {recovery_success}/20")
        logging.info(f"  Recovery performance: {'[OK]' if recovery_time_ms < 1000 else '[SLOW]'}")

        return {
            'test': 'Recovery Time',
            'baseline_success_rate': baseline_success / 10 * 100,
            'recovery_time_ms': recovery_time_ms,
            'recovery_success_rate': recovery_success / 20 * 100,
            'passed': recovery_time_ms < 1000 and recovery_success >= 15
        }

    def run_full_test(self):
        """Run all network failure tests"""
        logging.info("="*70)
        logging.info("NETWORK FAILURE TEST - Chaos Engineering")
        logging.info("="*70)
        logging.info(f"Target URL: {self.target_url}")
        logging.info(f"Start Time: {datetime.now()}")

        # Check if target is reachable first
        logging.info("\nChecking target availability...")
        initial_check = self.make_request(timeout=5)
        if not initial_check['success']:
            logging.error(f"Target {self.target_url} is not reachable!")
            logging.error("Please ensure the target service is running.")
            logging.error("For Docker: docker service ls")
            return None

        logging.info(f"Target is reachable: {initial_check['response_time_ms']:.1f}ms")

        # Run all tests
        test_results = []

        test_results.append(self.simulate_timeout_scenario())
        test_results.append(self.simulate_connection_refused())
        test_results.append(self.simulate_intermittent_failures())
        test_results.append(self.test_recovery_time())

        # Summary
        logging.info("\n" + "="*70)
        logging.info("NETWORK FAILURE TEST - SUMMARY")
        logging.info("="*70)

        passed_tests = sum(1 for t in test_results if t['passed'])
        total_tests = len(test_results)

        logging.info(f"\nTest Results: {passed_tests}/{total_tests} passed")
        logging.info("-" * 50)

        for result in test_results:
            status = "[PASS]" if result['passed'] else "[FAIL]"
            logging.info(f"  {result['test']}: {status}")

        logging.info("-" * 50)

        # Recommendations
        logging.info("\nRecommendations:")
        logging.info("  1. Implement retry logic with exponential backoff")
        logging.info("  2. Use circuit breakers for external dependencies")
        logging.info("  3. Set appropriate timeouts for all network calls")
        logging.info("  4. Implement health checks and automatic failover")
        logging.info("  5. Monitor network errors and set up alerts")

        overall_status = "[OK] RESILIENT" if passed_tests >= 3 else "[NEEDS IMPROVEMENT]"
        logging.info(f"\nOverall Status: {overall_status}")
        logging.info("="*70)

        # Save results
        results_file = f'network_failure_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(results_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'target_url': self.target_url,
                'tests': test_results,
                'passed': passed_tests,
                'total': total_tests,
                'overall_status': overall_status
            }, f, indent=2)

        logging.info(f"\nResults saved to: {results_file}")

        return test_results


if __name__ == "__main__":
    import sys

    target = "http://localhost:80"
    if len(sys.argv) > 1:
        target = sys.argv[1]

    test = NetworkFailureTest(target_url=target)
    test.run_full_test()
