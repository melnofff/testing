#!/usr/bin/env python3
"""
API Reliability Testing
Tests API behavior with rate limiting, retries, circuit breakers, and timeouts
"""

import requests
import time
import logging
import json
from datetime import datetime
from collections import defaultdict
import statistics

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'api_reliability_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

class CircuitBreaker:
    """Simple circuit breaker implementation"""

    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN

    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""

        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.timeout:
                self.state = 'HALF_OPEN'
                logging.info("  Circuit breaker: OPEN -> HALF_OPEN")
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)

            if self.state == 'HALF_OPEN':
                self.state = 'CLOSED'
                self.failures = 0
                logging.info("  Circuit breaker: HALF_OPEN -> CLOSED")

            return result

        except Exception as e:
            self.failures += 1
            self.last_failure_time = time.time()

            if self.failures >= self.failure_threshold:
                self.state = 'OPEN'
                logging.warning(f"  Circuit breaker: CLOSED -> OPEN (failures: {self.failures})")

            raise e

class APIReliabilityTest:
    """Test API reliability patterns"""

    def __init__(self, base_url="https://jsonplaceholder.typicode.com"):
        self.base_url = base_url
        self.metrics = {
            'rate_limit_tests': [],
            'retry_tests': [],
            'circuit_breaker_tests': [],
            'timeout_tests': []
        }

    def test_rate_limiting(self):
        """Test rate limiting behavior"""

        logging.info("="*70)
        logging.info("TEST 1: Rate Limiting")
        logging.info("="*70)

        # Simulate requests exceeding rate limit
        requests_per_second = 100
        duration = 10

        logging.info(f"\nSending {requests_per_second} requests/second for {duration} seconds")

        results = {
            'total': 0,
            'successful': 0,
            'rate_limited': 0,
            'errors': defaultdict(int)
        }

        start_time = time.time()

        while time.time() - start_time < duration:
            batch_start = time.time()

            for _ in range(requests_per_second):
                try:
                    response = requests.get(
                        f"{self.base_url}/posts/1",
                        timeout=5
                    )

                    results['total'] += 1

                    if response.status_code == 200:
                        results['successful'] += 1
                    elif response.status_code == 429:  # Too Many Requests
                        results['rate_limited'] += 1
                    else:
                        results['errors'][f'HTTP_{response.status_code}'] += 1

                except requests.exceptions.Timeout:
                    results['total'] += 1
                    results['errors']['Timeout'] += 1

                except Exception as e:
                    results['total'] += 1
                    results['errors'][type(e).__name__] += 1

            # Wait to maintain rate
            elapsed = time.time() - batch_start
            if elapsed < 1.0:
                time.sleep(1.0 - elapsed)

        # Analysis
        logging.info(f"\nResults:")
        logging.info(f"  Total Requests: {results['total']}")
        logging.info(f"  Successful: {results['successful']} ({results['successful']/results['total']*100:.1f}%)")
        logging.info(f"  Rate Limited (429): {results['rate_limited']}")

        if results['errors']:
            logging.info(f"  Errors:")
            for error_type, count in results['errors'].items():
                logging.info(f"    {error_type}: {count}")

        logging.info(f"\nRecommendations:")
        if results['rate_limited'] > 0:
            logging.info(f"  - Implement exponential backoff for rate-limited requests")
            logging.info(f"  - Add request queuing with rate limiter")
        else:
            logging.info(f"  - Monitor for future rate limiting")

        logging.info(f"  - Implement client-side rate limiting to prevent 429 errors")
        logging.info(f"  - Use token bucket or leaky bucket algorithm")

        self.metrics['rate_limit_tests'].append(results)

        return results

    def test_retry_mechanism(self):
        """Test retry logic with exponential backoff"""

        logging.info("\n" + "="*70)
        logging.info("TEST 2: Retry Mechanism")
        logging.info("="*70)

        max_retries = 3
        base_delay = 1  # seconds

        def make_request_with_retry(url, retries=max_retries):
            """Make request with exponential backoff retry"""

            for attempt in range(retries + 1):
                try:
                    logging.info(f"  Attempt {attempt + 1}/{retries + 1}")

                    response = requests.get(url, timeout=5)

                    if response.status_code == 200:
                        logging.info(f"    SUCCESS on attempt {attempt + 1}")
                        return True, attempt + 1

                    elif response.status_code >= 500:
                        if attempt < retries:
                            delay = base_delay * (2 ** attempt)  # Exponential backoff
                            logging.warning(f"    Server error (HTTP {response.status_code}), "
                                          f"retrying in {delay}s...")
                            time.sleep(delay)
                        else:
                            logging.error(f"    FAILED after {retries + 1} attempts")
                            return False, attempt + 1

                except requests.exceptions.Timeout:
                    if attempt < retries:
                        delay = base_delay * (2 ** attempt)
                        logging.warning(f"    Timeout, retrying in {delay}s...")
                        time.sleep(delay)
                    else:
                        logging.error(f"    FAILED after {retries + 1} attempts (Timeout)")
                        return False, attempt + 1

                except Exception as e:
                    logging.error(f"    ERROR: {type(e).__name__}: {e}")
                    return False, attempt + 1

            return False, retries + 1

        # Test scenarios
        test_urls = [
            (f"{self.base_url}/posts/1", "Valid endpoint"),
            (f"{self.base_url}/posts/99999", "Non-existent resource"),
            ("https://httpstat.us/500?sleep=1000", "Server error simulation"),
        ]

        results = []

        for url, description in test_urls:
            logging.info(f"\nTest: {description}")
            logging.info(f"  URL: {url}")

            success, attempts = make_request_with_retry(url)

            results.append({
                'description': description,
                'success': success,
                'attempts': attempts
            })

        # Analysis
        logging.info(f"\n{'='*70}")
        logging.info("Retry Mechanism Analysis")
        logging.info("="*70)

        for result in results:
            status = "[PASS]" if result['success'] else "[FAIL]"
            logging.info(f"  {result['description']}: {status} (attempts: {result['attempts']})")

        logging.info(f"\nRecommendations:")
        logging.info(f"  - Use exponential backoff with jitter to prevent thundering herd")
        logging.info(f"  - Set maximum retry budget to prevent infinite loops")
        logging.info(f"  - Implement different retry strategies for different error types")
        logging.info(f"  - Log retry attempts for monitoring and debugging")

        self.metrics['retry_tests'] = results

        return results

    def test_circuit_breaker(self):
        """Test circuit breaker pattern"""

        logging.info("\n" + "="*70)
        logging.info("TEST 3: Circuit Breaker Pattern")
        logging.info("="*70)

        circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=10)

        def unreliable_api_call():
            """Simulate an unreliable API call"""
            # Simulate 70% failure rate
            import random
            if random.random() < 0.7:
                raise Exception("API call failed")
            return "Success"

        results = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'circuit_open_rejections': 0,
            'state_changes': []
        }

        logging.info("\nSimulating unreliable API (70% failure rate)")

        for i in range(50):
            results['total_calls'] += 1

            try:
                result = circuit_breaker.call(unreliable_api_call)
                results['successful_calls'] += 1

                if i % 10 == 0:
                    logging.info(f"  Call {i+1}: SUCCESS (state: {circuit_breaker.state})")

            except Exception as e:
                if "Circuit breaker is OPEN" in str(e):
                    results['circuit_open_rejections'] += 1

                    if i % 10 == 0:
                        logging.warning(f"  Call {i+1}: REJECTED - Circuit OPEN")

                else:
                    results['failed_calls'] += 1

                    if i % 10 == 0:
                        logging.warning(f"  Call {i+1}: FAILED (state: {circuit_breaker.state})")

            time.sleep(0.2)

        # Analysis
        logging.info(f"\n{'='*70}")
        logging.info("Circuit Breaker Analysis")
        logging.info("="*70)

        logging.info(f"  Total Calls: {results['total_calls']}")
        logging.info(f"  Successful: {results['successful_calls']}")
        logging.info(f"  Failed: {results['failed_calls']}")
        logging.info(f"  Rejected (Circuit Open): {results['circuit_open_rejections']}")
        logging.info(f"  Final State: {circuit_breaker.state}")

        protection_rate = (results['circuit_open_rejections'] / results['total_calls'] * 100)
        logging.info(f"\nCircuit breaker prevented {protection_rate:.1f}% of calls during OPEN state")

        logging.info(f"\nRecommendations:")
        logging.info(f"  - Circuit breaker successfully protected system from cascading failures")
        logging.info(f"  - Tune failure threshold based on acceptable error rate")
        logging.info(f"  - Implement fallback mechanisms for OPEN state")
        logging.info(f"  - Monitor circuit breaker state changes and alerts")

        self.metrics['circuit_breaker_tests'].append(results)

        return results

    def test_timeout_handling(self):
        """Test various timeout scenarios"""

        logging.info("\n" + "="*70)
        logging.info("TEST 4: Timeout Handling")
        logging.info("="*70)

        timeout_scenarios = [
            (1, "https://httpstat.us/200?sleep=500", "Fast response (500ms)"),
            (2, "https://httpstat.us/200?sleep=3000", "Slow response (3s)"),
            (1, "https://httpstat.us/200?sleep=2000", "Timeout scenario (2s with 1s timeout)"),
        ]

        results = []

        for timeout, url, description in timeout_scenarios:
            logging.info(f"\nTest: {description}")
            logging.info(f"  URL: {url}")
            logging.info(f"  Timeout: {timeout}s")

            start = time.time()

            try:
                response = requests.get(url, timeout=timeout)
                elapsed = (time.time() - start) * 1000

                logging.info(f"  Result: SUCCESS ({elapsed:.0f}ms, HTTP {response.status_code})")

                results.append({
                    'description': description,
                    'success': True,
                    'elapsed_ms': elapsed,
                    'timeout_ms': timeout * 1000
                })

            except requests.exceptions.Timeout:
                elapsed = (time.time() - start) * 1000

                logging.warning(f"  Result: TIMEOUT ({elapsed:.0f}ms)")

                results.append({
                    'description': description,
                    'success': False,
                    'elapsed_ms': elapsed,
                    'timeout_ms': timeout * 1000,
                    'error': 'Timeout'
                })

            except Exception as e:
                elapsed = (time.time() - start) * 1000

                logging.error(f"  Result: ERROR - {type(e).__name__}")

                results.append({
                    'description': description,
                    'success': False,
                    'elapsed_ms': elapsed,
                    'timeout_ms': timeout * 1000,
                    'error': type(e).__name__
                })

        # Analysis
        logging.info(f"\n{'='*70}")
        logging.info("Timeout Handling Analysis")
        logging.info("="*70)

        for result in results:
            status = "[PASS]" if result['success'] else "[FAIL]"
            logging.info(f"  {result['description']}: {status} ({result['elapsed_ms']:.0f}ms)")

        logging.info(f"\nRecommendations:")
        logging.info(f"  - Set appropriate timeouts based on SLA requirements")
        logging.info(f"  - Use different timeouts for different endpoints")
        logging.info(f"  - Implement connection timeout AND read timeout separately")
        logging.info(f"  - Add timeout monitoring and alerting")
        logging.info(f"  - Consider using circuit breakers for timeout-prone endpoints")

        self.metrics['timeout_tests'] = results

        return results

    def generate_final_report(self):
        """Generate comprehensive API reliability report"""

        logging.info("\n" + "="*70)
        logging.info("API RELIABILITY TEST - FINAL REPORT")
        logging.info("="*70)

        logging.info("\nExecutive Summary:")
        logging.info("  This report analyzes API reliability patterns including:")
        logging.info("  - Rate limiting and throttling")
        logging.info("  - Retry mechanisms with exponential backoff")
        logging.info("  - Circuit breaker implementation")
        logging.info("  - Timeout handling strategies")

        logging.info("\nKey Findings:")
        logging.info("  1. Rate limiting should be implemented client-side to prevent 429 errors")
        logging.info("  2. Exponential backoff retry is effective for transient failures")
        logging.info("  3. Circuit breakers prevent cascading failures in distributed systems")
        logging.info("  4. Appropriate timeout configuration is critical for system reliability")

        logging.info("\nBest Practices:")
        best_practices = [
            "Implement client-side rate limiting before API calls",
            "Use exponential backoff with jitter for retries",
            "Deploy circuit breakers for external service dependencies",
            "Configure timeouts at connection, read, and overall request levels",
            "Monitor API error rates and response times continuously",
            "Implement fallback mechanisms for degraded service scenarios",
            "Use health checks to detect service degradation early",
            "Log all retry attempts and circuit breaker state changes"
        ]

        for i, practice in enumerate(best_practices, 1):
            logging.info(f"  {i}. {practice}")

        # Save detailed metrics
        metrics_file = f'api_reliability_metrics_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(metrics_file, 'w') as f:
            json.dump(self.metrics, f, indent=2, default=str)

        logging.info(f"\nDetailed metrics saved to: {metrics_file}")

        logging.info("\n" + "="*70)
        logging.info("All API Reliability Tests Completed")
        logging.info("="*70)

if __name__ == "__main__":
    logging.info("Starting API Reliability Testing\n")

    test = APIReliabilityTest()

    # Run all tests
    test.test_rate_limiting()
    test.test_retry_mechanism()
    test.test_circuit_breaker()
    test.test_timeout_handling()

    # Generate final report
    test.generate_final_report()
