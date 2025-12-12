#!/usr/bin/env python3
"""
Load Spike Testing
Tests system response to sudden increases in load
"""

import requests
import time
import logging
import json
import threading
from datetime import datetime
from collections import defaultdict
import statistics

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'spike_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

class LoadSpikeTest:
    """Test system behavior under sudden load spikes"""

    def __init__(self, base_url="http://localhost:80"):
        self.base_url = base_url
        self.active_threads = []
        self.stop_flag = threading.Event()
        self.metrics = {
            'requests': [],
            'timestamps': [],
            'response_times': [],
            'errors': defaultdict(int)
        }
        self.lock = threading.Lock()

    def make_request(self, thread_id):
        """Make HTTP request and record metrics"""
        start = time.time()

        try:
            response = requests.get(
                f"{self.base_url}/",
                timeout=10
            )
            elapsed = (time.time() - start) * 1000

            with self.lock:
                self.metrics['requests'].append({
                    'thread_id': thread_id,
                    'timestamp': time.time(),
                    'success': response.status_code in [200, 301, 302],
                    'response_time_ms': elapsed,
                    'status_code': response.status_code
                })

            return True, elapsed

        except requests.exceptions.Timeout:
            elapsed = (time.time() - start) * 1000
            with self.lock:
                self.metrics['requests'].append({
                    'thread_id': thread_id,
                    'timestamp': time.time(),
                    'success': False,
                    'response_time_ms': elapsed,
                    'error': 'Timeout'
                })
                self.metrics['errors']['Timeout'] += 1
            return False, elapsed

        except Exception as e:
            elapsed = (time.time() - start) * 1000
            with self.lock:
                self.metrics['requests'].append({
                    'thread_id': thread_id,
                    'timestamp': time.time(),
                    'success': False,
                    'response_time_ms': elapsed,
                    'error': type(e).__name__
                })
                self.metrics['errors'][type(e).__name__] += 1
            return False, elapsed

    def request_worker(self, thread_id, requests_per_second=1):
        """Worker thread that makes requests at specified rate"""
        interval = 1.0 / requests_per_second if requests_per_second > 0 else 0

        while not self.stop_flag.is_set():
            self.make_request(thread_id)
            if interval > 0:
                time.sleep(interval)

    def spike_pattern_instant(self):
        """
        Pattern 1: Instant spike
        10 users -> 500 users in 10 seconds
        """
        logging.info("="*70)
        logging.info("SPIKE PATTERN 1: Instant Spike")
        logging.info("="*70)
        logging.info("Load: 10 -> 500 users in 10 seconds")

        self.metrics = {'requests': [], 'timestamps': [], 'response_times': [], 'errors': defaultdict(int)}
        self.stop_flag.clear()

        # Phase 1: Baseline (10 users)
        logging.info("\nPhase 1: Baseline Load (10 users, 30s)")
        baseline_users = 10

        for i in range(baseline_users):
            thread = threading.Thread(target=self.request_worker, args=(i, 2))  # 2 req/s each
            thread.daemon = True
            thread.start()
            self.active_threads.append(thread)

        time.sleep(30)

        baseline_metrics = self._calculate_recent_metrics(10)
        logging.info(f"  Baseline Throughput: {baseline_metrics['throughput']:.2f} req/s")
        logging.info(f"  Baseline Response Time: {baseline_metrics['avg_response_time']:.2f}ms")

        # Phase 2: Instant spike to 500 users
        logging.info("\nPhase 2: Instant Spike (10 -> 500 users in 10s)")

        spike_start = time.time()
        users_to_add = 490

        # Add users rapidly
        for i in range(users_to_add):
            thread = threading.Thread(target=self.request_worker, args=(baseline_users + i, 2))
            thread.daemon = True
            thread.start()
            self.active_threads.append(thread)

            if i % 50 == 0:
                logging.info(f"  Current users: {baseline_users + i}")

            time.sleep(10 / users_to_add)  # Distribute over 10 seconds

        spike_duration = time.time() - spike_start
        logging.info(f"  Spike completed in {spike_duration:.2f}s")

        # Phase 3: Sustained high load
        logging.info("\nPhase 3: Sustained Peak Load (500 users, 60s)")

        time.sleep(60)

        peak_metrics = self._calculate_recent_metrics(30)
        logging.info(f"  Peak Throughput: {peak_metrics['throughput']:.2f} req/s")
        logging.info(f"  Peak Response Time: {peak_metrics['avg_response_time']:.2f}ms")
        logging.info(f"  Success Rate: {peak_metrics['success_rate']:.1f}%")

        # Phase 4: Ramp down
        logging.info("\nPhase 4: Load Reduction")

        self.stop_flag.set()
        time.sleep(2)

        # Analyze spike response
        self._analyze_spike_response("Instant Spike", baseline_metrics, peak_metrics)

        return baseline_metrics, peak_metrics

    def spike_pattern_periodic(self):
        """
        Pattern 2: Periodic spikes
        Every 5 minutes: +200 users for 1 minute
        """
        logging.info("\n" + "="*70)
        logging.info("SPIKE PATTERN 2: Periodic Spikes")
        logging.info("="*70)
        logging.info("Pattern: +200 users every 5 minutes (lasting 1 minute)")

        self.metrics = {'requests': [], 'timestamps': [], 'response_times': [], 'errors': defaultdict(int)}
        self.stop_flag.clear()
        self.active_threads = []

        # Baseline load
        baseline_users = 50
        logging.info(f"\nBaseline: {baseline_users} users")

        for i in range(baseline_users):
            thread = threading.Thread(target=self.request_worker, args=(i, 1))
            thread.daemon = True
            thread.start()
            self.active_threads.append(thread)

        time.sleep(20)

        results = []

        # Run 3 spike cycles
        for cycle in range(3):
            logging.info(f"\n--- Spike Cycle {cycle + 1}/3 ---")

            # Normal period
            logging.info(f"  Normal load period (4 minutes)")
            time.sleep(60)  # Shortened for testing (normally 4 minutes)

            normal_metrics = self._calculate_recent_metrics(30)
            logging.info(f"    Throughput: {normal_metrics['throughput']:.2f} req/s")
            logging.info(f"    Response Time: {normal_metrics['avg_response_time']:.2f}ms")

            # Spike period
            logging.info(f"  SPIKE: Adding 200 users for 1 minute")

            spike_threads = []
            for i in range(200):
                thread = threading.Thread(target=self.request_worker, args=(baseline_users + i, 2))
                thread.daemon = True
                thread.start()
                spike_threads.append(thread)

            time.sleep(60)

            spike_metrics = self._calculate_recent_metrics(30)
            logging.info(f"    Spike Throughput: {spike_metrics['throughput']:.2f} req/s")
            logging.info(f"    Spike Response Time: {spike_metrics['avg_response_time']:.2f}ms")
            logging.info(f"    Success Rate: {spike_metrics['success_rate']:.1f}%")

            # Stop spike threads
            self.stop_flag.set()
            time.sleep(1)
            self.stop_flag.clear()

            results.append({
                'cycle': cycle + 1,
                'normal': normal_metrics,
                'spike': spike_metrics
            })

        # Stop all threads
        self.stop_flag.set()

        # Analyze periodic spikes
        self._analyze_periodic_spikes(results)

        return results

    def spike_pattern_gradual_with_peaks(self):
        """
        Pattern 3: Gradual growth with periodic peaks
        Base load grows from 50 to 200, with spikes to 400
        """
        logging.info("\n" + "="*70)
        logging.info("SPIKE PATTERN 3: Gradual Growth with Peaks")
        logging.info("="*70)
        logging.info("Pattern: 50 -> 200 users over 10 minutes, with spikes to 400")

        self.metrics = {'requests': [], 'timestamps': [], 'response_times': [], 'errors': defaultdict(int)}
        self.stop_flag.clear()
        self.active_threads = []

        # Start with 50 users
        current_users = 50
        logging.info(f"\nStarting with {current_users} users")

        for i in range(current_users):
            thread = threading.Thread(target=self.request_worker, args=(i, 1))
            thread.daemon = True
            thread.start()
            self.active_threads.append(thread)

        time.sleep(20)

        # Gradual ramp up with spikes
        ramp_duration = 300  # 5 minutes (shortened from 10 for testing)
        users_to_add = 150
        interval = ramp_duration / users_to_add

        logging.info(f"\nGradual ramp: adding {users_to_add} users over {ramp_duration}s")

        for i in range(users_to_add):
            thread = threading.Thread(target=self.request_worker, args=(current_users + i, 1))
            thread.daemon = True
            thread.start()
            self.active_threads.append(thread)

            # Add spike every minute
            if i > 0 and i % 30 == 0:  # Every 30 users (~ 1 minute)
                logging.info(f"\n  SPIKE at {current_users + i} base users")

                spike_threads = []
                for j in range(200):
                    thread = threading.Thread(target=self.request_worker, args=(1000 + j, 2))
                    thread.daemon = True
                    thread.start()
                    spike_threads.append(thread)

                time.sleep(30)  # Spike duration

                spike_metrics = self._calculate_recent_metrics(20)
                logging.info(f"    During spike: {spike_metrics['throughput']:.2f} req/s, "
                           f"{spike_metrics['avg_response_time']:.2f}ms, "
                           f"{spike_metrics['success_rate']:.1f}% success")

                # Stop spike
                self.stop_flag.set()
                time.sleep(1)
                self.stop_flag.clear()

            time.sleep(interval)

        # Final metrics
        logging.info("\nFinal sustained load analysis (30s)")
        time.sleep(30)

        final_metrics = self._calculate_recent_metrics(30)
        logging.info(f"  Final Throughput: {final_metrics['throughput']:.2f} req/s")
        logging.info(f"  Final Response Time: {final_metrics['avg_response_time']:.2f}ms")
        logging.info(f"  Final Success Rate: {final_metrics['success_rate']:.1f}%")

        self.stop_flag.set()

        return final_metrics

    def _calculate_recent_metrics(self, time_window_seconds):
        """Calculate metrics for recent time window"""

        with self.lock:
            recent_requests = [
                r for r in self.metrics['requests']
                if r['timestamp'] > time.time() - time_window_seconds
            ]

        if not recent_requests:
            return {
                'throughput': 0,
                'avg_response_time': 0,
                'success_rate': 0,
                'total_requests': 0
            }

        successful = [r for r in recent_requests if r.get('success', False)]
        response_times = [r['response_time_ms'] for r in recent_requests if 'response_time_ms' in r]

        return {
            'throughput': len(successful) / time_window_seconds,
            'avg_response_time': statistics.mean(response_times) if response_times else 0,
            'success_rate': (len(successful) / len(recent_requests) * 100) if recent_requests else 0,
            'total_requests': len(recent_requests)
        }

    def _analyze_spike_response(self, pattern_name, baseline, peak):
        """Analyze system response to spike"""

        logging.info(f"\n{'='*70}")
        logging.info(f"SPIKE ANALYSIS: {pattern_name}")
        logging.info("="*70)

        # Throughput analysis
        throughput_increase = ((peak['throughput'] - baseline['throughput']) / baseline['throughput'] * 100) if baseline['throughput'] > 0 else 0
        logging.info(f"\n1. Throughput Impact:")
        logging.info(f"   Baseline: {baseline['throughput']:.2f} req/s")
        logging.info(f"   Peak: {peak['throughput']:.2f} req/s")
        logging.info(f"   Increase: {throughput_increase:.1f}%")

        # Response time analysis
        response_degradation = ((peak['avg_response_time'] - baseline['avg_response_time']) / baseline['avg_response_time'] * 100) if baseline['avg_response_time'] > 0 else 0
        logging.info(f"\n2. Response Time Impact:")
        logging.info(f"   Baseline: {baseline['avg_response_time']:.2f}ms")
        logging.info(f"   Peak: {peak['avg_response_time']:.2f}ms")
        logging.info(f"   Degradation: {response_degradation:.1f}%")

        # Success rate
        logging.info(f"\n3. Reliability:")
        logging.info(f"   Peak Success Rate: {peak['success_rate']:.1f}%")

        if peak['success_rate'] < 95:
            logging.warning("   WARNING: Success rate below 95% during spike")

        # Recommendations
        logging.info(f"\n4. Recommendations:")

        recommendations = []

        if response_degradation > 200:
            recommendations.append("CRITICAL: Response time degraded >200% - implement request queuing")
        elif response_degradation > 100:
            recommendations.append("WARNING: Significant response time degradation - optimize or scale")

        if peak['success_rate'] < 95:
            recommendations.append("CRITICAL: Low success rate - implement rate limiting and circuit breakers")
        elif peak['success_rate'] < 99:
            recommendations.append("WARNING: Decreased reliability - review error handling")

        if throughput_increase < 300:
            recommendations.append("System did not scale well with load - investigate bottlenecks")

        recommendations.extend([
            "Implement auto-scaling with aggressive scale-up policies",
            "Use request queuing to buffer traffic spikes",
            "Enable connection pooling and keep-alive",
            "Consider CDN for static content",
            "Implement rate limiting to protect backend"
        ])

        for i, rec in enumerate(recommendations, 1):
            logging.info(f"   {i}. {rec}")

    def _analyze_periodic_spikes(self, results):
        """Analyze periodic spike pattern results"""

        logging.info(f"\n{'='*70}")
        logging.info("PERIODIC SPIKE ANALYSIS")
        logging.info("="*70)

        logging.info(f"\n{'Cycle':<10} {'Normal (req/s)':<20} {'Spike (req/s)':<20} {'Success Rate'}")
        logging.info("-" * 70)

        for result in results:
            logging.info(f"{result['cycle']:<10} "
                        f"{result['normal']['throughput']:<20.2f} "
                        f"{result['spike']['throughput']:<20.2f} "
                        f"{result['spike']['success_rate']:.1f}%")

        # Check for degradation over cycles
        first_spike = results[0]['spike']['throughput']
        last_spike = results[-1]['spike']['throughput']

        degradation = ((first_spike - last_spike) / first_spike * 100) if first_spike > 0 else 0

        logging.info(f"\nDegradation over cycles: {degradation:.1f}%")

        if degradation > 10:
            logging.warning("  WARNING: Performance degraded across cycles - possible resource leak")
        else:
            logging.info("  System maintained consistent performance across cycles")

if __name__ == "__main__":
    import sys

    target_url = "http://localhost:80"
    if len(sys.argv) > 1:
        target_url = sys.argv[1]

    logging.info("Starting Load Spike Testing")
    logging.info(f"Target: {target_url}\n")

    test = LoadSpikeTest(base_url=target_url)

    # Run all spike patterns
    logging.info("Running all spike patterns...\n")

    test.spike_pattern_instant()
    test.spike_pattern_periodic()
    test.spike_pattern_gradual_with_peaks()

    logging.info("\n" + "="*70)
    logging.info("All spike tests completed")
    logging.info("="*70)
