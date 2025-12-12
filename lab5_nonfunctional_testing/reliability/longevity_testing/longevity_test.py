#!/usr/bin/env python3
"""
Long-Running Test (Longevity/Endurance Testing)
Runs for 8+ hours to detect memory leaks, connection leaks, and performance degradation
"""

import time
import psutil
import requests
import logging
import json
import threading
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'longevity_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

class LongevityTest:
    """
    Long-running stability test
    Tests system behavior over extended periods
    """

    def __init__(self, duration_hours=8, target_url="http://localhost:80"):
        self.duration_hours = duration_hours
        self.target_url = target_url
        self.start_time = None
        self.end_time = None

        # Metrics storage
        self.metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'response_times': [],
            'memory_samples': [],
            'cpu_samples': [],
            'connection_count_samples': [],
            'file_descriptor_samples': [],
            'error_types': defaultdict(int),
            'hourly_stats': []
        }

        self.running = False

    def get_system_metrics(self):
        """Collect system metrics"""
        process = psutil.Process()

        return {
            'memory_mb': process.memory_info().rss / (1024 * 1024),
            'cpu_percent': process.cpu_percent(),
            'num_threads': process.num_threads(),
            'num_fds': process.num_fds() if hasattr(process, 'num_fds') else 0,
            'connections': len(process.connections()) if hasattr(process, 'connections') else 0
        }

    def make_request(self):
        """Make a single HTTP request"""
        start_time = time.time()

        try:
            response = requests.get(
                self.target_url,
                timeout=10,
                allow_redirects=True
            )

            elapsed = (time.time() - start_time) * 1000  # Convert to ms

            self.metrics['total_requests'] += 1

            if response.status_code in [200, 301, 302]:
                self.metrics['successful_requests'] += 1
                self.metrics['response_times'].append(elapsed)
                return True, elapsed, None
            else:
                self.metrics['failed_requests'] += 1
                self.metrics['error_types'][f'HTTP_{response.status_code}'] += 1
                return False, elapsed, f'HTTP {response.status_code}'

        except requests.exceptions.Timeout:
            elapsed = (time.time() - start_time) * 1000
            self.metrics['failed_requests'] += 1
            self.metrics['error_types']['Timeout'] += 1
            return False, elapsed, 'Timeout'

        except requests.exceptions.ConnectionError as e:
            elapsed = (time.time() - start_time) * 1000
            self.metrics['failed_requests'] += 1
            self.metrics['error_types']['ConnectionError'] += 1
            return False, elapsed, f'ConnectionError: {str(e)[:50]}'

        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            self.metrics['failed_requests'] += 1
            self.metrics['error_types'][type(e).__name__] += 1
            return False, elapsed, f'{type(e).__name__}: {str(e)[:50]}'

    def monitoring_thread(self):
        """Background thread for monitoring system metrics"""
        while self.running:
            try:
                sys_metrics = self.get_system_metrics()

                self.metrics['memory_samples'].append(sys_metrics['memory_mb'])
                self.metrics['cpu_samples'].append(sys_metrics['cpu_percent'])
                self.metrics['connection_count_samples'].append(sys_metrics['connections'])
                self.metrics['file_descriptor_samples'].append(sys_metrics['num_fds'])

                time.sleep(30)  # Sample every 30 seconds

            except Exception as e:
                logging.error(f"Monitoring error: {e}")

    def run_longevity_test(self):
        """Execute the long-running test"""

        logging.info("="*70)
        logging.info("LONGEVITY TEST - Extended Stability Testing")
        logging.info("="*70)
        logging.info(f"Duration: {self.duration_hours} hours")
        logging.info(f"Target URL: {self.target_url}")
        logging.info(f"Start Time: {datetime.now()}")
        logging.info("="*70)

        self.start_time = datetime.now()
        self.running = True

        # Start monitoring thread
        monitor = threading.Thread(target=self.monitoring_thread, daemon=True)
        monitor.start()

        # Initial metrics
        initial_metrics = self.get_system_metrics()
        logging.info(f"\nInitial State:")
        logging.info(f"  Memory: {initial_metrics['memory_mb']:.2f} MB")
        logging.info(f"  CPU: {initial_metrics['cpu_percent']:.1f}%")
        logging.info(f"  Threads: {initial_metrics['num_threads']}")
        logging.info(f"  Connections: {initial_metrics['connections']}")

        # Calculate end time
        end_time = datetime.now() + timedelta(hours=self.duration_hours)
        hour_count = 0
        next_hour_report = datetime.now() + timedelta(hours=1)

        logging.info(f"\nTest will run until: {end_time}")
        logging.info("\nStarting request loop...\n")

        # Progress tracking
        last_progress_time = datetime.now()
        progress_interval = timedelta(seconds=30)  # Show progress every 30 seconds

        try:
            while datetime.now() < end_time:
                # Make request
                success, response_time, error = self.make_request()

                # Log errors
                if not success:
                    logging.warning(f"Request failed: {error} ({response_time:.0f}ms)")

                # Progress update every 30 seconds
                if datetime.now() >= last_progress_time + progress_interval:
                    elapsed = (datetime.now() - self.start_time).total_seconds()
                    total = (end_time - self.start_time).total_seconds()
                    progress = (elapsed / total) * 100
                    remaining = total - elapsed
                    success_rate = (self.metrics['successful_requests'] / self.metrics['total_requests'] * 100) if self.metrics['total_requests'] > 0 else 0
                    avg_resp = statistics.mean(self.metrics['response_times'][-50:]) if self.metrics['response_times'] else 0

                    logging.info(f"[Progress: {progress:.1f}%] Requests: {self.metrics['total_requests']}, Success: {success_rate:.1f}%, Avg: {avg_resp:.1f}ms, Remaining: {remaining:.0f}s")
                    last_progress_time = datetime.now()

                # Hourly report
                if datetime.now() >= next_hour_report:
                    hour_count += 1
                    self._generate_hourly_report(hour_count)
                    next_hour_report = datetime.now() + timedelta(hours=1)

                # Maintain ~30% load (20-30% of capacity)
                # Adjust sleep time based on desired request rate
                time.sleep(2)  # ~30 requests per minute

        except KeyboardInterrupt:
            logging.warning("\nTest interrupted by user")

        finally:
            self.running = False
            self.end_time = datetime.now()

        # Final report
        self._generate_final_report(initial_metrics)

    def _generate_hourly_report(self, hour_number):
        """Generate report for each hour"""

        logging.info("\n" + "="*70)
        logging.info(f"HOURLY REPORT - Hour {hour_number}")
        logging.info("="*70)

        # Calculate hourly metrics
        total_reqs = self.metrics['total_requests']
        success_rate = (self.metrics['successful_requests'] / total_reqs * 100) if total_reqs > 0 else 0

        recent_response_times = self.metrics['response_times'][-100:] if self.metrics['response_times'] else [0]
        avg_response = statistics.mean(recent_response_times)

        current_metrics = self.get_system_metrics()

        logging.info(f"Time: {datetime.now()}")
        logging.info(f"Total Requests: {total_reqs}")
        logging.info(f"Success Rate: {success_rate:.2f}%")
        logging.info(f"Avg Response Time (last 100): {avg_response:.2f}ms")
        logging.info(f"Current Memory: {current_metrics['memory_mb']:.2f} MB")
        logging.info(f"Current CPU: {current_metrics['cpu_percent']:.1f}%")
        logging.info(f"Active Connections: {current_metrics['connections']}")

        # Store hourly stats
        self.metrics['hourly_stats'].append({
            'hour': hour_number,
            'timestamp': datetime.now().isoformat(),
            'total_requests': total_reqs,
            'success_rate': success_rate,
            'avg_response_ms': avg_response,
            'memory_mb': current_metrics['memory_mb'],
            'cpu_percent': current_metrics['cpu_percent'],
            'connections': current_metrics['connections']
        })

        logging.info("="*70 + "\n")

    def _generate_final_report(self, initial_metrics):
        """Generate comprehensive final report"""

        logging.info("\n" + "="*70)
        logging.info("LONGEVITY TEST - FINAL REPORT")
        logging.info("="*70)

        actual_duration = (self.end_time - self.start_time).total_seconds() / 3600

        logging.info(f"\n1. Test Overview:")
        logging.info(f"   Start Time: {self.start_time}")
        logging.info(f"   End Time: {self.end_time}")
        logging.info(f"   Planned Duration: {self.duration_hours} hours")
        logging.info(f"   Actual Duration: {actual_duration:.2f} hours")

        # Request statistics
        total_reqs = self.metrics['total_requests']
        success_rate = (self.metrics['successful_requests'] / total_reqs * 100) if total_reqs > 0 else 0

        logging.info(f"\n2. Request Statistics:")
        logging.info(f"   Total Requests: {total_reqs}")
        logging.info(f"   Successful: {self.metrics['successful_requests']}")
        logging.info(f"   Failed: {self.metrics['failed_requests']}")
        logging.info(f"   Success Rate: {success_rate:.2f}%")

        if total_reqs > 0:
            logging.info(f"   Requests/Hour: {total_reqs/actual_duration:.1f}")

        # Response time analysis
        degradation = 0  # Initialize to prevent UnboundLocalError
        if self.metrics['response_times']:
            avg_response = statistics.mean(self.metrics['response_times'])
            median_response = statistics.median(self.metrics['response_times'])
            min_response = min(self.metrics['response_times'])
            max_response = max(self.metrics['response_times'])

            logging.info(f"\n3. Response Time Analysis:")
            logging.info(f"   Average: {avg_response:.2f}ms")
            logging.info(f"   Median: {median_response:.2f}ms")
            logging.info(f"   Min: {min_response:.2f}ms")
            logging.info(f"   Max: {max_response:.2f}ms")

            # Check for degradation
            first_hour_times = self.metrics['response_times'][:100] if len(self.metrics['response_times']) > 100 else self.metrics['response_times']
            last_hour_times = self.metrics['response_times'][-100:] if len(self.metrics['response_times']) > 100 else self.metrics['response_times']

            first_avg = statistics.mean(first_hour_times)
            last_avg = statistics.mean(last_hour_times)
            degradation = ((last_avg - first_avg) / first_avg * 100) if first_avg > 0 else 0

            logging.info(f"   First Hour Avg: {first_avg:.2f}ms")
            logging.info(f"   Last Hour Avg: {last_avg:.2f}ms")
            logging.info(f"   Performance Degradation: {degradation:.2f}%")

        # Memory leak analysis
        memory_growth = 0  # Initialize to prevent UnboundLocalError
        if self.metrics['memory_samples']:
            initial_memory = self.metrics['memory_samples'][0]
            final_memory = self.metrics['memory_samples'][-1]
            peak_memory = max(self.metrics['memory_samples'])
            memory_growth = final_memory - initial_memory

            logging.info(f"\n4. Memory Analysis:")
            logging.info(f"   Initial Memory: {initial_memory:.2f} MB")
            logging.info(f"   Final Memory: {final_memory:.2f} MB")
            logging.info(f"   Peak Memory: {peak_memory:.2f} MB")
            logging.info(f"   Memory Growth: {memory_growth:.2f} MB ({(memory_growth/initial_memory*100):.1f}%)")

            if memory_growth > 100:
                logging.warning("   WARNING: Significant memory leak detected (>100 MB)")
            elif memory_growth > 50:
                logging.warning("   NOTICE: Possible memory leak (>50 MB)")
            else:
                logging.info("   Status: No significant memory leak detected")

        # Connection leak analysis
        initial_connections = 0  # Initialize to prevent UnboundLocalError
        final_connections = 0    # Initialize to prevent UnboundLocalError
        if self.metrics['connection_count_samples']:
            initial_connections = self.metrics['connection_count_samples'][0]
            final_connections = self.metrics['connection_count_samples'][-1]
            peak_connections = max(self.metrics['connection_count_samples'])

            logging.info(f"\n5. Connection Analysis:")
            logging.info(f"   Initial Connections: {initial_connections}")
            logging.info(f"   Final Connections: {final_connections}")
            logging.info(f"   Peak Connections: {peak_connections}")

            if final_connections > initial_connections + 10:
                logging.warning(f"   WARNING: Possible connection leak (+{final_connections - initial_connections})")
            else:
                logging.info("   Status: No connection leak detected")

        # Error analysis
        if self.metrics['error_types']:
            logging.info(f"\n6. Error Analysis:")
            for error_type, count in sorted(self.metrics['error_types'].items(), key=lambda x: x[1], reverse=True):
                error_rate = (count / total_reqs * 100) if total_reqs > 0 else 0
                logging.info(f"   {error_type}: {count} ({error_rate:.2f}%)")

        # Recommendations
        logging.info(f"\n7. Recommendations:")

        recommendations = []

        if degradation > 20:
            recommendations.append("Performance degradation detected - investigate resource optimization")

        if memory_growth > 50:
            recommendations.append("Memory leak suspected - use profiling tools to identify leak source")

        if final_connections > initial_connections + 10:
            recommendations.append("Connection leak detected - ensure proper connection cleanup")

        if success_rate < 99:
            recommendations.append("Reliability issues detected - implement retry mechanisms")

        if not recommendations:
            recommendations.append("System shows good stability over extended run")
            recommendations.append("Continue monitoring in production environment")

        for i, rec in enumerate(recommendations, 1):
            logging.info(f"   {i}. {rec}")

        # Save detailed metrics
        metrics_file = f'longevity_metrics_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(metrics_file, 'w') as f:
            json.dump({
                'test_info': {
                    'duration_hours': actual_duration,
                    'start_time': self.start_time.isoformat(),
                    'end_time': self.end_time.isoformat()
                },
                'summary': {
                    'total_requests': total_reqs,
                    'success_rate': success_rate,
                    'avg_response_ms': avg_response if self.metrics['response_times'] else 0,
                    'memory_growth_mb': memory_growth if self.metrics['memory_samples'] else 0
                },
                'hourly_stats': self.metrics['hourly_stats'],
                'error_distribution': dict(self.metrics['error_types'])
            }, f, indent=2)

        logging.info(f"\n   Detailed metrics saved to: {metrics_file}")

        logging.info("\n" + "="*70)
        logging.info("Test Completed")
        logging.info("="*70)

if __name__ == "__main__":
    import sys

    # Default: 8 hours (can be reduced for testing)
    duration = 8

    if len(sys.argv) > 1:
        duration = float(sys.argv[1])

    # For quick testing, use: python longevity_test.py 0.1 (6 minutes)
    logging.info(f"Starting longevity test for {duration} hours")

    test = LongevityTest(duration_hours=duration)
    test.run_longevity_test()
