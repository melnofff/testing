#!/usr/bin/env python3
"""
CPU Stress Test
Tests system behavior under CPU load
"""

import psutil
import time
import logging
import multiprocessing
from datetime import datetime
import math

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'cpu_stress_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

class CPUStressTest:
    """CPU stress testing with performance monitoring"""

    def __init__(self, duration_seconds=60, target_load_percent=80):
        self.duration = duration_seconds
        self.target_load = target_load_percent
        self.metrics = {
            'avg_cpu_percent': 0,
            'peak_cpu_percent': 0,
            'min_cpu_percent': 100,
            'response_times_ms': [],
            'degradation_factor': 0
        }

    @staticmethod
    def cpu_intensive_task(duration):
        """CPU-intensive calculation task"""
        end_time = time.time() + duration
        result = 0

        while time.time() < end_time:
            # Perform CPU-intensive calculations
            for i in range(1000):
                result += math.sqrt(i) * math.sin(i) * math.cos(i)
                result = result % 1000000

        return result

    def simulate_request(self):
        """Simulate a web request with timing"""
        start = time.time()

        # Simulate some work
        result = 0
        for i in range(10000):
            result += math.sqrt(i)

        end = time.time()
        return (end - start) * 1000  # Convert to ms

    def run_stress_test(self):
        """Execute CPU stress test"""

        logging.info("="*70)
        logging.info("CPU Stress Test")
        logging.info("="*70)

        # Phase 1: Baseline measurement
        logging.info("\nPhase 1: Baseline Performance")
        logging.info("-" * 50)

        baseline_times = []
        for i in range(10):
            response_time = self.simulate_request()
            baseline_times.append(response_time)

        avg_baseline = sum(baseline_times) / len(baseline_times)
        logging.info(f"  CPU Usage: {psutil.cpu_percent(interval=1)}%")
        logging.info(f"  Average Response Time: {avg_baseline:.2f}ms")
        logging.info(f"  CPU Count: {multiprocessing.cpu_count()}")

        # Phase 2: Start CPU stress
        logging.info("\nPhase 2: CPU Stress Test (80% load)")
        logging.info("-" * 50)
        logging.info(f"  Duration: {self.duration} seconds")

        # Determine number of processes for target load
        cpu_count = multiprocessing.cpu_count()
        num_workers = max(1, int((self.target_load / 100) * cpu_count))

        logging.info(f"  Spawning {num_workers} worker processes...")

        # Start CPU stress workers
        pool = multiprocessing.Pool(processes=num_workers)
        worker_duration = self.duration / 6  # Workers run in batches

        # Start async workers
        async_results = []
        for _ in range(num_workers):
            result = pool.apply_async(self.cpu_intensive_task, (worker_duration,))
            async_results.append(result)

        # Monitor CPU and response times during stress
        logging.info("\n  Monitoring (samples every 5 seconds):")
        logging.info("  " + "-" * 60)

        cpu_samples = []
        stress_response_times = []
        samples = self.duration // 5

        for i in range(samples):
            time.sleep(5)

            # Measure CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_samples.append(cpu_percent)

            # Measure response time under load
            response_time = self.simulate_request()
            stress_response_times.append(response_time)

            logging.info(f"  Time: {(i+1)*5}s | "
                       f"CPU: {cpu_percent:.1f}% | "
                       f"Response Time: {response_time:.2f}ms")

            # Update metrics
            if cpu_percent > self.metrics['peak_cpu_percent']:
                self.metrics['peak_cpu_percent'] = cpu_percent
            if cpu_percent < self.metrics['min_cpu_percent']:
                self.metrics['min_cpu_percent'] = cpu_percent

        # Clean up workers
        pool.close()
        pool.join()

        # Phase 3: Recovery
        logging.info("\nPhase 3: Recovery Period")
        logging.info("-" * 50)

        time.sleep(5)  # Wait for CPU to settle

        recovery_times = []
        for i in range(10):
            response_time = self.simulate_request()
            recovery_times.append(response_time)
            time.sleep(0.5)

        avg_recovery = sum(recovery_times) / len(recovery_times)
        cpu_after = psutil.cpu_percent(interval=1)

        logging.info(f"  CPU Usage: {cpu_after}%")
        logging.info(f"  Average Response Time: {avg_recovery:.2f}ms")

        # Calculate metrics
        self.metrics['avg_cpu_percent'] = sum(cpu_samples) / len(cpu_samples) if cpu_samples else 0
        self.metrics['response_times_ms'] = stress_response_times
        avg_stress_response = sum(stress_response_times) / len(stress_response_times) if stress_response_times else 0
        self.metrics['degradation_factor'] = avg_stress_response / avg_baseline if avg_baseline > 0 else 1

        # Phase 4: Analysis
        self._generate_report(avg_baseline, avg_stress_response, avg_recovery)

    def _generate_report(self, baseline_ms, stress_ms, recovery_ms):
        """Generate comprehensive analysis report"""

        logging.info("\n" + "="*70)
        logging.info("CPU STRESS TEST ANALYSIS")
        logging.info("="*70)

        logging.info("\n1. CPU Utilization Metrics:")
        logging.info(f"   Target Load: {self.target_load}%")
        logging.info(f"   Average CPU Usage: {self.metrics['avg_cpu_percent']:.1f}%")
        logging.info(f"   Peak CPU Usage: {self.metrics['peak_cpu_percent']:.1f}%")
        logging.info(f"   Minimum CPU Usage: {self.metrics['min_cpu_percent']:.1f}%")

        load_accuracy = (self.metrics['avg_cpu_percent'] / self.target_load) * 100
        logging.info(f"   Load Accuracy: {load_accuracy:.1f}%")

        logging.info("\n2. Performance Impact:")
        logging.info(f"   Baseline Response Time: {baseline_ms:.2f}ms")
        logging.info(f"   Under Load Response Time: {stress_ms:.2f}ms")
        logging.info(f"   Recovery Response Time: {recovery_ms:.2f}ms")

        degradation = ((stress_ms - baseline_ms) / baseline_ms) * 100
        logging.info(f"   Performance Degradation: {degradation:.1f}%")
        logging.info(f"   Degradation Factor: {self.metrics['degradation_factor']:.2f}x")

        recovery_improvement = ((stress_ms - recovery_ms) / stress_ms) * 100
        logging.info(f"   Recovery Improvement: {recovery_improvement:.1f}%")

        logging.info("\n3. System Behavior Analysis:")

        if degradation < 20:
            logging.info("   Status: EXCELLENT - Minimal performance impact under load")
        elif degradation < 50:
            logging.info("   Status: GOOD - Acceptable performance degradation")
        elif degradation < 100:
            logging.info("   Status: WARNING - Significant performance impact")
        else:
            logging.warning("   Status: CRITICAL - Severe performance degradation")

        if recovery_ms <= baseline_ms * 1.1:
            logging.info("   Recovery: FULL - System returned to baseline")
        else:
            logging.warning("   Recovery: PARTIAL - Performance not fully restored")

        logging.info("\n4. Capacity Planning:")
        current_capacity = 100 - self.metrics['avg_cpu_percent']
        logging.info(f"   Remaining CPU Capacity: {current_capacity:.1f}%")

        if current_capacity > 30:
            logging.info("   Recommendation: System can handle additional load")
        elif current_capacity > 15:
            logging.warning("   Recommendation: Consider horizontal scaling soon")
        else:
            logging.error("   Recommendation: IMMEDIATE scaling required")

        logging.info("\n5. Reliability Recommendations:")
        recommendations = [
            "Implement CPU-based auto-scaling at 70% threshold",
            "Add request queuing to prevent overload",
            "Set up CPU monitoring with alerting",
            "Consider implementing rate limiting",
            "Use load balancing for distributing CPU-intensive tasks",
            "Implement circuit breakers for CPU-heavy operations",
            "Add graceful degradation for non-critical features"
        ]

        for i, rec in enumerate(recommendations, 1):
            logging.info(f"   {i}. {rec}")

        logging.info("\n6. SLA Compliance:")
        sla_threshold_ms = 100  # Example SLA threshold

        violations = sum(1 for rt in self.metrics['response_times_ms'] if rt > sla_threshold_ms)
        violation_rate = (violations / len(self.metrics['response_times_ms'])) * 100 if self.metrics['response_times_ms'] else 0

        logging.info(f"   SLA Threshold: {sla_threshold_ms}ms")
        logging.info(f"   SLA Violations: {violations}/{len(self.metrics['response_times_ms'])} ({violation_rate:.1f}%)")

        if violation_rate < 1:
            logging.info("   SLA Status: COMPLIANT")
        else:
            logging.warning("   SLA Status: NON-COMPLIANT")

        logging.info("\n" + "="*70)
        logging.info("Test Completed")
        logging.info("="*70)

if __name__ == "__main__":
    import sys

    duration = 60  # Default 60 seconds
    target_load = 80  # Default 80% CPU load

    if len(sys.argv) > 1:
        duration = int(sys.argv[1])
    if len(sys.argv) > 2:
        target_load = int(sys.argv[2])

    logging.info(f"Starting CPU stress test: {duration}s duration, {target_load}% target load")

    test = CPUStressTest(duration_seconds=duration, target_load_percent=target_load)
    test.run_stress_test()
