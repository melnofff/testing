#!/usr/bin/env python3
"""
Horizontal Scaling Test
Tests system scalability by adding/removing servers dynamically
"""

import requests
import time
import logging
import json
import subprocess
from datetime import datetime
from collections import defaultdict
import statistics
import concurrent.futures

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'scaling_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

class HorizontalScalingTest:
    """Test horizontal scaling capabilities"""

    def __init__(self, base_url="http://localhost:8080", max_workers=100):
        self.base_url = base_url
        self.max_workers = max_workers
        self.metrics = {
            'scaling_results': [],
            'throughput_by_replicas': {},
            'response_times_by_replicas': {},
            'errors_by_replicas': {}
        }

    def run_load_test(self, duration_seconds=30, concurrent_users=50):
        """Run load test and measure performance"""

        logging.info(f"  Running load test: {duration_seconds}s, {concurrent_users} concurrent users")

        results = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'response_times': [],
            'errors': defaultdict(int)
        }

        end_time = time.time() + duration_seconds

        def make_request():
            """Make a single request"""
            start = time.time()
            try:
                response = requests.get(
                    f"{self.base_url}/",
                    timeout=10
                )
                elapsed = (time.time() - start) * 1000

                if response.status_code in [200, 301, 302]:
                    return True, elapsed, None
                else:
                    return False, elapsed, f"HTTP_{response.status_code}"

            except requests.exceptions.Timeout:
                elapsed = (time.time() - start) * 1000
                return False, elapsed, "Timeout"
            except Exception as e:
                elapsed = (time.time() - start) * 1000
                return False, elapsed, type(e).__name__

        # Run concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            while time.time() < end_time:
                # Submit batch of requests
                futures = []
                for _ in range(concurrent_users):
                    if time.time() >= end_time:
                        break
                    future = executor.submit(make_request)
                    futures.append(future)

                # Collect results
                for future in concurrent.futures.as_completed(futures):
                    if time.time() >= end_time:
                        break

                    success, response_time, error = future.result()
                    results['total_requests'] += 1

                    if success:
                        results['successful_requests'] += 1
                        results['response_times'].append(response_time)
                    else:
                        results['failed_requests'] += 1
                        results['errors'][error] += 1

                time.sleep(0.1)  # Small delay between batches

        # Calculate metrics
        if results['response_times']:
            results['avg_response_time'] = statistics.mean(results['response_times'])
            results['median_response_time'] = statistics.median(results['response_times'])
            results['p95_response_time'] = statistics.quantiles(results['response_times'], n=20)[18]  # 95th percentile
        else:
            results['avg_response_time'] = 0
            results['median_response_time'] = 0
            results['p95_response_time'] = 0

        results['throughput'] = results['successful_requests'] / duration_seconds
        results['success_rate'] = (results['successful_requests'] / results['total_requests'] * 100) if results['total_requests'] > 0 else 0

        return results

    def get_replica_count(self):
        """Get current number of replicas (simulated)"""
        # In real scenario, query Docker Swarm or Kubernetes
        # For testing, we'll simulate this
        try:
            # Example: docker service ls --filter name=myapp_web --format "{{.Replicas}}"
            result = subprocess.run(
                ['docker', 'service', 'ls', '--filter', 'name=web', '--format', '{{.Replicas}}'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                # Parse "3/3" format
                replicas = result.stdout.strip().split('/')[0]
                return int(replicas)
        except Exception as e:
            logging.warning(f"Could not get replica count: {e}")

        # Return simulated value if Docker not available
        return 1

    def scale_service(self, replicas):
        """Scale service to specified number of replicas"""

        logging.info(f"  Scaling service to {replicas} replicas...")

        try:
            # Example: docker service scale myapp_web=5
            result = subprocess.run(
                ['docker', 'service', 'scale', f'web={replicas}'],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                logging.info(f"  Successfully scaled to {replicas} replicas")
                # Wait for scaling to complete
                time.sleep(10)
                return True
            else:
                logging.warning(f"  Scaling failed: {result.stderr}")
                return False

        except Exception as e:
            logging.warning(f"Could not scale service: {e}")
            logging.info("  Running in simulation mode")
            time.sleep(2)  # Simulate scaling delay
            return True

    def test_horizontal_scaling(self):
        """Main test for horizontal scaling"""

        logging.info("="*70)
        logging.info("HORIZONTAL SCALING TEST")
        logging.info("="*70)

        # Test with different replica counts
        replica_counts = [1, 2, 3, 5]

        for replicas in replica_counts:
            logging.info(f"\n{'='*70}")
            logging.info(f"Testing with {replicas} replica(s)")
            logging.info("="*70)

            # Scale to target replicas
            self.scale_service(replicas)

            # Run load test
            logging.info("\n  Phase 1: Low Load Test")
            low_load = self.run_load_test(duration_seconds=30, concurrent_users=10)

            logging.info("\n  Phase 2: Medium Load Test")
            medium_load = self.run_load_test(duration_seconds=30, concurrent_users=30)

            logging.info("\n  Phase 3: High Load Test")
            high_load = self.run_load_test(duration_seconds=30, concurrent_users=50)

            # Store results
            self.metrics['scaling_results'].append({
                'replicas': replicas,
                'low_load': low_load,
                'medium_load': medium_load,
                'high_load': high_load
            })

            # Summary for this replica count
            self._print_replica_summary(replicas, low_load, medium_load, high_load)

        # Final analysis
        self._generate_scaling_analysis()

    def _print_replica_summary(self, replicas, low_load, medium_load, high_load):
        """Print summary for specific replica count"""

        logging.info(f"\n  Summary for {replicas} replica(s):")
        logging.info(f"  {'Load Level':<15} {'Throughput':<15} {'Avg Response':<15} {'Success Rate'}")
        logging.info(f"  {'-'*65}")

        logging.info(f"  {'Low':<15} {low_load['throughput']:<15.2f} "
                    f"{low_load['avg_response_time']:<15.2f} {low_load['success_rate']:.1f}%")

        logging.info(f"  {'Medium':<15} {medium_load['throughput']:<15.2f} "
                    f"{medium_load['avg_response_time']:<15.2f} {medium_load['success_rate']:.1f}%")

        logging.info(f"  {'High':<15} {high_load['throughput']:<15.2f} "
                    f"{high_load['avg_response_time']:<15.2f} {high_load['success_rate']:.1f}%")

    def _generate_scaling_analysis(self):
        """Generate comprehensive scaling analysis"""

        logging.info("\n" + "="*70)
        logging.info("HORIZONTAL SCALING ANALYSIS")
        logging.info("="*70)

        # Analyze scaling efficiency
        logging.info("\n1. Scaling Efficiency (High Load):")
        logging.info(f"  {'Replicas':<12} {'Throughput':<15} {'Scaling Factor':<15} {'Efficiency'}")
        logging.info(f"  {'-'*65}")

        baseline_throughput = None
        for result in self.metrics['scaling_results']:
            replicas = result['replicas']
            throughput = result['high_load']['throughput']

            if baseline_throughput is None:
                baseline_throughput = throughput
                scaling_factor = 1.0
                efficiency = 100.0
            else:
                scaling_factor = throughput / baseline_throughput
                ideal_scaling = replicas
                efficiency = (scaling_factor / ideal_scaling) * 100

            logging.info(f"  {replicas:<12} {throughput:<15.2f} "
                        f"{scaling_factor:<15.2f}x {efficiency:.1f}%")

        # Analyze response times
        logging.info("\n2. Response Time Analysis:")
        logging.info(f"  {'Replicas':<12} {'Low Load':<15} {'Medium Load':<15} {'High Load'}")
        logging.info(f"  {'-'*65}")

        for result in self.metrics['scaling_results']:
            replicas = result['replicas']
            low = result['low_load']['avg_response_time']
            medium = result['medium_load']['avg_response_time']
            high = result['high_load']['avg_response_time']

            logging.info(f"  {replicas:<12} {low:<15.2f} {medium:<15.2f} {high:<15.2f}")

        # Success rate analysis
        logging.info("\n3. Reliability Analysis:")
        logging.info(f"  {'Replicas':<12} {'Low Load':<15} {'Medium Load':<15} {'High Load'}")
        logging.info(f"  {'-'*65}")

        for result in self.metrics['scaling_results']:
            replicas = result['replicas']
            low = result['low_load']['success_rate']
            medium = result['medium_load']['success_rate']
            high = result['high_load']['success_rate']

            logging.info(f"  {replicas:<12} {low:<15.1f}% {medium:<15.1f}% {high:<15.1f}%")

        # Recommendations
        logging.info("\n4. Scaling Recommendations:")

        # Find optimal replica count
        best_efficiency = 0
        optimal_replicas = 1

        for result in self.metrics['scaling_results']:
            replicas = result['replicas']
            throughput = result['high_load']['throughput']
            success_rate = result['high_load']['success_rate']

            if replicas == 1:
                baseline = throughput
                continue

            efficiency = (throughput / baseline) / replicas * 100

            if efficiency > best_efficiency and success_rate > 99:
                best_efficiency = efficiency
                optimal_replicas = replicas

        recommendations = [
            f"Optimal replica count for current load: {optimal_replicas}",
            f"Best scaling efficiency achieved: {best_efficiency:.1f}%",
            "Implement auto-scaling based on CPU/memory metrics",
            "Set scale-up threshold at 70% resource utilization",
            "Set scale-down threshold at 30% resource utilization",
            "Use horizontal pod autoscaler (HPA) in production"
        ]

        for i, rec in enumerate(recommendations, 1):
            logging.info(f"  {i}. {rec}")

        # Economic analysis
        logging.info("\n5. Cost-Performance Analysis:")

        for result in self.metrics['scaling_results']:
            replicas = result['replicas']
            throughput = result['high_load']['throughput']
            cost_per_replica = 10  # Simulated cost per replica per hour

            total_cost = replicas * cost_per_replica
            cost_per_request = total_cost / (throughput * 3600) if throughput > 0 else 0

            logging.info(f"  {replicas} replicas: ${total_cost}/hour, "
                        f"${cost_per_request:.6f} per request")

        # Save detailed metrics
        metrics_file = f'scaling_metrics_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(metrics_file, 'w') as f:
            json.dump(self.metrics, f, indent=2)

        logging.info(f"\n  Detailed metrics saved to: {metrics_file}")

        logging.info("\n" + "="*70)
        logging.info("Test Completed")
        logging.info("="*70)

if __name__ == "__main__":
    import sys

    # Target URL (default to localhost)
    target_url = "http://localhost:8080"

    if len(sys.argv) > 1:
        target_url = sys.argv[1]

    logging.info(f"Starting horizontal scaling test")
    logging.info(f"Target URL: {target_url}")

    test = HorizontalScalingTest(base_url=target_url)
    test.test_horizontal_scaling()
