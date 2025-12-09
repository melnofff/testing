import time
import random
import psutil
from datetime import datetime
import pandas as pd
import numpy as np
from cloud_client import CloudDataClient
import json

# ============================================================
# Универсальная функция конвертации данных в JSON-friendly формат
# ============================================================
def convert_for_json(obj):
    """Рекурсивно конвертирует любые pandas/numpy/сложные типы в JSON-сериализуемые."""
    
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (pd.Timestamp, datetime)):
        return obj.isoformat()
    if isinstance(obj, np.ndarray):
        return [convert_for_json(v) for v in obj.tolist()]
    if isinstance(obj, pd.Series):
        return [convert_for_json(v) for v in obj.tolist()]
    if isinstance(obj, pd.DataFrame):
        return convert_for_json(obj.to_dict(orient="records"))
    if isinstance(obj, dict):
        return {str(k): convert_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [convert_for_json(v) for v in obj]
    return str(obj)


# ============================================================
# Основной класс CHAOS FRAMEWORK
# ============================================================
class ChaosFramework:
    def __init__(self, use_localstack=True):
        self.client = CloudDataClient(use_localstack)
        self.experiments_log = []
        self._original_upload_method = None  # для data_corruption
        self.current_duration = 0

    def log_experiment(self, experiment_type, description, success):
        experiment = {
            'timestamp': datetime.now().isoformat(),
            'type': experiment_type,
            'description': description,
            'success': success,
            'duration': getattr(self, 'current_duration', 0)
        }
        self.experiments_log.append(experiment)
        print(f"📝 {experiment_type}: {description} - {'✅ УСПЕХ' if success else '❌ ПРОВАЛ'}")

    # -------------------- Эксперименты -----------------------
    def network_latency(self, duration=30, latency_ms=1000):
        print(f"🌐 Добавляем сетевую задержку {latency_ms}мс на {duration} секунд...")
        self.current_duration = duration

        try:
            if not hasattr(self, '_original_upload_for_latency'):
                self._original_upload_for_latency = self.client.upload_csv_to_s3

            latency_end_time = time.time() + duration

            def delayed_upload(*args, **kwargs):
                if time.time() < latency_end_time:
                    time.sleep(latency_ms / 1000)
                return self._original_upload_for_latency(*args, **kwargs)

            self.client.upload_csv_to_s3 = delayed_upload
            self._latency_end_time = latency_end_time

            self.log_experiment("NETWORK_LATENCY",
                                f"Задержка {latency_ms}мс в течение {duration}с",
                                True)
            return True
        except Exception as e:
            self.log_experiment("NETWORK_LATENCY", f"Ошибка: {e}", False)
            return False

    def stop_network_latency(self):
        """Останавливаем сетевую задержку"""
        if hasattr(self, '_original_upload_for_latency'):
            self.client.upload_csv_to_s3 = self._original_upload_for_latency
            delattr(self, '_original_upload_for_latency')
            if hasattr(self, '_latency_end_time'):
                delattr(self, '_latency_end_time')
            print("✅ Сетевая задержка остановлена")

    def service_failure(self, service_type, failure_duration=20):
        print(f"🔥 Эмулируем отказ {service_type} на {failure_duration} секунд...")
        self.current_duration = failure_duration

        try:
            if service_type == "S3":
                original_upload = self.client.upload_csv_to_s3
                original_download = self.client.download_csv_from_s3

                def failing_upload(*args, **kwargs):
                    raise Exception("S3 FAIL")
                def failing_download(*args, **kwargs):
                    raise Exception("S3 FAIL")

                self.client.upload_csv_to_s3 = failing_upload
                self.client.download_csv_from_s3 = failing_download

                # Сохраняем оригиналы для восстановления позже
                self._s3_restore_time = time.time() + failure_duration
                self._original_s3_upload = original_upload
                self._original_s3_download = original_download

            elif service_type == "SQS":
                original_send = self.client.send_message
                original_receive = self.client.receive_messages

                def failing_send(*a, **k):
                    raise Exception("SQS FAIL")
                def failing_receive(*a, **k):
                    raise Exception("SQS FAIL")

                self.client.send_message = failing_send
                self.client.receive_messages = failing_receive

                # Сохраняем оригиналы для восстановления позже
                self._sqs_restore_time = time.time() + failure_duration
                self._original_sqs_send = original_send
                self._original_sqs_receive = original_receive

            self.log_experiment("SERVICE_FAILURE",
                                f"Отказ {service_type} {failure_duration}с",
                                True)
            return True
        except Exception as e:
            self.log_experiment("SERVICE_FAILURE", str(e), False)
            return False

    def high_cpu_load(self, duration=30, load_percent=80):
        print(f"🔥 Создаем нагрузку на CPU ({load_percent}%) на {duration} секунд...")
        self.current_duration = duration
        start_time = time.time()

        try:
            import threading

            def cpu_stress():
                while time.time() - start_time < duration:
                    [x**2 for x in range(30000)]

            thread = threading.Thread(target=cpu_stress)
            thread.daemon = True
            thread.start()

            while time.time() - start_time < duration:
                cpu = psutil.cpu_percent(interval=1)
                print(f"⚡ CPU: {cpu}%")
                time.sleep(2)

            self.log_experiment("HIGH_CPU_LOAD",
                                f"CPU {load_percent}% {duration}с",
                                True)
            return True
        except Exception as e:
            self.log_experiment("HIGH_CPU_LOAD", str(e), False)
            return False

    def memory_pressure(self, duration=30, memory_mb=500):
        print(f"💾 Давление на память: {memory_mb}MB на {duration} секунд...")
        self.current_duration = duration
        blocks = []

        try:
            block_size = 1024 * 1024
            for i in range(memory_mb):
                blocks.append(" " * block_size)
                if i % 50 == 0:
                    print(f"📦 {i}MB выделено")

            print(f"✅ Выделено {len(blocks)}MB")
            time.sleep(duration)
            blocks.clear()

            self.log_experiment("MEMORY_PRESSURE",
                                f"Память {memory_mb}MB, {duration}с",
                                True)
            return True
        except MemoryError:
            self.log_experiment("MEMORY_PRESSURE",
                                f"MemoryError при {memory_mb}MB",
                                False)
            return False

    def data_corruption(self, probability=0.3):
        print(f"📉 Коррупция данных, вероятность {probability*100}%...")
        try:
            if self._original_upload_method is None:
                self._original_upload_method = self.client.upload_csv_to_s3

            def corrupt_upload(df, bucket_name, key):
                if random.random() < probability:
                    print("💀 Коррупция данных...")
                    corruption = random.choice(["nulls", "duplicates", "truncate"])
                    df2 = df.copy()
                    if corruption == "nulls":
                        for col in df2.columns:
                            if random.random() < 0.2:
                                df2[col] = None
                    elif corruption == "duplicates":
                        dup = df2.sample(min(5, len(df2)))
                        df2 = pd.concat([df2, dup])
                    elif corruption == "truncate":
                        df2 = df2.head(max(1, len(df2)//2))
                    return self._original_upload_method(df2, bucket_name, key)
                return self._original_upload_method(df, bucket_name, key)

            self.client.upload_csv_to_s3 = corrupt_upload
            self.log_experiment("DATA_CORRUPTION",
                                f"Вероятность {probability*100}%",
                                True)
            return True
        except Exception as e:
            self.log_experiment("DATA_CORRUPTION", str(e), False)
            return False

    def stop_data_corruption(self):
        if self._original_upload_method:
            self.client.upload_csv_to_s3 = self._original_upload_method
            self._original_upload_method = None
            print("✅ Коррупция данных остановлена")

    def restore_services(self):
        """Восстанавливаем все сервисы"""
        if hasattr(self, '_original_s3_upload'):
            self.client.upload_csv_to_s3 = self._original_s3_upload
            self.client.download_csv_from_s3 = self._original_s3_download
            delattr(self, '_original_s3_upload')
            delattr(self, '_original_s3_download')
            delattr(self, '_s3_restore_time')
            print("✅ S3 сервис восстановлен")

        if hasattr(self, '_original_sqs_send'):
            self.client.send_message = self._original_sqs_send
            self.client.receive_messages = self._original_sqs_receive
            delattr(self, '_original_sqs_send')
            delattr(self, '_original_sqs_receive')
            delattr(self, '_sqs_restore_time')
            print("✅ SQS сервис восстановлен")

    # ---------------------------------------------------------
    # Генерация отчета
    # ---------------------------------------------------------
    def generate_report(self):
        print("\n📊 ГЕНЕРИРУЕМ ОТЧЕТ\n" + "="*50)

        if not self.experiments_log:
            print("❌ Нет данных")
            return None

        df = pd.DataFrame(self.experiments_log)

        stats = df.groupby("type").agg({
            "success": ["count", "sum"],
            "duration": "mean"
        }).round(2)

        stats["success_rate"] = (
            stats[("success", "sum")] / stats[("success", "count")] * 100
        ).round(2)

        print(stats)

        report = {
            "timestamp": datetime.now().isoformat(),
            "experiments": df.to_dict("records"),
            "statistics": convert_for_json(stats.to_dict()),
            "total_experiments": len(df),  # <-- исправлено
            "successful_experiments": int(df["success"].sum()),
            "success_rate": float(df["success"].mean()*100)
        }

        safe_report = convert_for_json(report)

        with open("chaos_report.json", "w", encoding="utf-8") as f:
            json.dump(safe_report, f, indent=2, ensure_ascii=False)

        print("✅ Отчет сохранён: chaos_report.json")
        return safe_report

    # ---------------------------------------------------------
    # Запуск Chaos Monkey
    # ---------------------------------------------------------
    def run_chaos_monkey(self, duration=240, interval=20):
        start_time = time.time()
        experiment_count = 0
        print("🎲 CHAOS MONKEY запущен...")

        chaos_methods = [
            self.network_latency,
            self.service_failure,
            self.high_cpu_load,
            self.memory_pressure,
            self.data_corruption
        ]

        while time.time() - start_time < duration:
            experiment = random.choice(chaos_methods)
            if experiment == self.network_latency:
                experiment(duration=interval, latency_ms=random.randint(100, 1000))
                time.sleep(interval)
                self.stop_network_latency()
            elif experiment == self.service_failure:
                experiment(service_type=random.choice(["S3","SQS"]), failure_duration=interval)
                time.sleep(interval)
                self.restore_services()
            elif experiment == self.high_cpu_load:
                experiment(duration=interval, load_percent=random.randint(50,90))
            elif experiment == self.memory_pressure:
                experiment(duration=interval, memory_mb=random.randint(50,200))
            elif experiment == self.data_corruption:
                experiment(probability=random.uniform(0.1,0.5))
                time.sleep(interval)
                self.stop_data_corruption()
            experiment_count += 1

        print("🎲 CHAOS MONKEY завершён")
        return experiment_count


# ============================================================
# Демонстрация
# ============================================================
if __name__ == "__main__":
    chaos = ChaosFramework(use_localstack=True)

    print("🎯 ДЕМОНСТРАЦИЯ CHAOS ENGINEERING\n" + "="*40)

    chaos.network_latency(15, 800)
    chaos.service_failure("S3", 15)
    chaos.high_cpu_load(20, 60)
    chaos.data_corruption(0.5)
    chaos.stop_data_corruption()
    chaos.generate_report()
