#!/usr/bin/env python3
"""
Memory Exhaustion Test
Tests system behavior under memory pressure
"""

import psutil
import time
import logging
from datetime import datetime
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'memory_stress_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

class MemoryStressTest:
    """Simulates memory exhaustion scenarios"""

    def __init__(self, target_memory_mb=500):
        self.target_memory_mb = target_memory_mb
        self.memory_chunks = []
        self.metrics = {
            'start_memory_mb': 0,
            'peak_memory_mb': 0,
            'end_memory_mb': 0,
            'oom_events': 0,
            'gc_collections': 0
        }

    def get_memory_usage(self):
        """Get current memory usage in MB"""
        process = psutil.Process()
        return process.memory_info().rss / (1024 * 1024)

    def get_system_memory(self):
        """Get system memory statistics"""
        mem = psutil.virtual_memory()
        return {
            'total_mb': mem.total / (1024 * 1024),
            'available_mb': mem.available / (1024 * 1024),
            'used_mb': mem.used / (1024 * 1024),
            'percent': mem.percent
        }

    def run_memory_stress_test(self):
        """Execute memory stress test"""

        logging.info("="*70)
        logging.info("Memory Exhaustion Stress Test")
        logging.info("="*70)

        # Initial state
        logging.info("\nPhase 1: Initial State")
        logging.info("-" * 50)

        sys_mem = self.get_system_memory()
        self.metrics['start_memory_mb'] = self.get_memory_usage()

        logging.info(f"  System Memory Total: {sys_mem['total_mb']:.0f} MB")
        logging.info(f"  System Memory Available: {sys_mem['available_mb']:.0f} MB")
        logging.info(f"  System Memory Used: {sys_mem['percent']:.1f}%")
        logging.info(f"  Process Memory: {self.metrics['start_memory_mb']:.2f} MB")

        # Phase 2: Gradual memory allocation
        logging.info("\nPhase 2: Memory Allocation (Gradual Increase)")
        logging.info("-" * 50)
        logging.info(f"  Target: {self.target_memory_mb} MB")

        chunk_size = 10 * 1024 * 1024  # 10 MB chunks
        allocated_mb = 0

        try:
            while allocated_mb < self.target_memory_mb:
                # Allocate memory chunk
                chunk = bytearray(chunk_size)
                self.memory_chunks.append(chunk)

                allocated_mb += 10
                current_mem = self.get_memory_usage()
                sys_mem = self.get_system_memory()

                if current_mem > self.metrics['peak_memory_mb']:
                    self.metrics['peak_memory_mb'] = current_mem

                logging.info(f"  Allocated: {allocated_mb} MB | "
                           f"Process: {current_mem:.0f} MB | "
                           f"System: {sys_mem['percent']:.1f}% | "
                           f"Available: {sys_mem['available_mb']:.0f} MB")

                # Check if system memory is critically low
                if sys_mem['percent'] > 90:
                    logging.warning("  WARNING: System memory critically low!")
                    self.metrics['oom_events'] += 1
                    break

                time.sleep(0.1)  # Small delay to observe behavior

        except MemoryError:
            logging.error("  MEMORY ERROR: Out of Memory!")
            self.metrics['oom_events'] += 1

        # Phase 3: Memory pressure period
        logging.info("\nPhase 3: Sustained Memory Pressure (30 seconds)")
        logging.info("-" * 50)

        for i in range(30):
            current_mem = self.get_memory_usage()
            sys_mem = self.get_system_memory()

            if i % 5 == 0:  # Log every 5 seconds
                logging.info(f"  Time: {i}s | "
                           f"Process: {current_mem:.0f} MB | "
                           f"System: {sys_mem['percent']:.1f}% | "
                           f"Available: {sys_mem['available_mb']:.0f} MB")

            time.sleep(1)

        # Phase 4: Memory release
        logging.info("\nPhase 4: Memory Release")
        logging.info("-" * 50)

        chunks_to_release = len(self.memory_chunks)
        logging.info(f"  Releasing {chunks_to_release} memory chunks...")

        # Release memory gradually
        while self.memory_chunks:
            self.memory_chunks.pop()

            if len(self.memory_chunks) % 10 == 0:
                current_mem = self.get_memory_usage()
                sys_mem = self.get_system_memory()
                logging.info(f"  Released chunks: {chunks_to_release - len(self.memory_chunks)} | "
                           f"Process: {current_mem:.0f} MB | "
                           f"System: {sys_mem['percent']:.1f}%")

        # Force garbage collection
        import gc
        gc.collect()
        self.metrics['gc_collections'] += 1

        time.sleep(2)  # Wait for GC

        self.metrics['end_memory_mb'] = self.get_memory_usage()

        logging.info(f"  Final Process Memory: {self.metrics['end_memory_mb']:.2f} MB")

        # Phase 5: Analysis
        self._generate_report()

    def _generate_report(self):
        """Generate analysis report"""

        logging.info("\n" + "="*70)
        logging.info("MEMORY STRESS TEST ANALYSIS")
        logging.info("="*70)

        logging.info("\n1. Memory Metrics:")
        logging.info(f"   Initial Memory: {self.metrics['start_memory_mb']:.2f} MB")
        logging.info(f"   Peak Memory: {self.metrics['peak_memory_mb']:.2f} MB")
        logging.info(f"   Final Memory: {self.metrics['end_memory_mb']:.2f} MB")
        memory_increase = self.metrics['peak_memory_mb'] - self.metrics['start_memory_mb']
        logging.info(f"   Memory Increase: {memory_increase:.2f} MB")

        logging.info("\n2. Memory Leak Analysis:")
        memory_leak = self.metrics['end_memory_mb'] - self.metrics['start_memory_mb']
        logging.info(f"   Potential Memory Leak: {memory_leak:.2f} MB")

        if memory_leak > 50:
            logging.warning("   WARNING: Significant memory not released (>50 MB)")
            logging.warning("   Recommendation: Investigate memory leaks")
        elif memory_leak > 10:
            logging.info("   NOTICE: Minor memory overhead detected")
        else:
            logging.info("   OK: Memory properly released")

        logging.info("\n3. Stability Metrics:")
        logging.info(f"   OOM Events: {self.metrics['oom_events']}")
        logging.info(f"   GC Collections: {self.metrics['gc_collections']}")

        if self.metrics['oom_events'] > 0:
            logging.warning("   System experienced memory exhaustion")
            logging.warning("   Recommendation: Implement memory limits and monitoring")

        logging.info("\n4. Recommendations:")
        recommendations = [
            "Implement memory limits using ulimit or cgroups",
            "Add memory monitoring with alerts at 80% threshold",
            "Use memory profiling tools to identify leaks",
            "Implement graceful degradation under memory pressure",
            "Consider implementing object pooling for large allocations",
            "Add automatic restart mechanism if memory exceeds threshold"
        ]

        for i, rec in enumerate(recommendations, 1):
            logging.info(f"   {i}. {rec}")

        logging.info("\n" + "="*70)
        logging.info("Test Completed")
        logging.info("="*70)

if __name__ == "__main__":
    # Configure test parameters
    target_memory = 500  # MB

    if len(sys.argv) > 1:
        target_memory = int(sys.argv[1])

    logging.info(f"Starting memory stress test with target: {target_memory} MB")

    test = MemoryStressTest(target_memory_mb=target_memory)
    test.run_memory_stress_test()
