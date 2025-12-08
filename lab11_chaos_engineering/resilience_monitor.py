import time
from datetime import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json

from resilient_pipeline import ResilientDataPipeline
from chaos_framework import ChaosFramework


# ============================================================
# Универсальный JSON-конвертер (решает int64 / float64 / NaN)
# ============================================================
def convert_for_json(obj):
    """Преобразование numpy/pandas типов к сериализуемым JSON."""
    if obj is None:
        return None

    # Примитивы
    if isinstance(obj, (str, int, float, bool)):
        return obj

    # numpy scalar types
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)

    # pandas timestamps
    if isinstance(obj, (pd.Timestamp, datetime)):
        return obj.isoformat()

    # numpy arrays
    if isinstance(obj, np.ndarray):
        return [convert_for_json(v) for v in obj.tolist()]

    # pandas Series
    if isinstance(obj, pd.Series):
        return convert_for_json(obj.to_dict())

    # pandas DataFrame
    if isinstance(obj, pd.DataFrame):
        return convert_for_json(obj.to_dict("records"))

    # dict
    if isinstance(obj, dict):
        return {str(k): convert_for_json(v) for k, v in obj.items()}

    # list/tuple/set
    if isinstance(obj, (list, tuple, set)):
        return [convert_for_json(v) for v in obj]

    # NaN → None
    if isinstance(obj, float) and np.isnan(obj):
        return None

    # fallback
    return str(obj)


# ============================================================
# Основной класс мониторинга устойчивости
# ============================================================
class ResilienceMonitor:
    def __init__(self, use_localstack=True):
        self.pipeline = ResilientDataPipeline(use_localstack)
        self.chaos = ChaosFramework(use_localstack)
        self.metrics = []
    
    def collect_metrics(self, duration=300, interval=30):
        print(f"📊 Собираем метрики устойчивости в течение {duration} секунд...")

        start_time = time.time()
        iteration = 0
        
        while time.time() - start_time < duration:
            iteration += 1
            print(f"\n📈 Итерация {iteration}")
            
            pipeline_start = time.time()
            success = self.pipeline.run_resilient_pipeline(enable_chaos=True)
            pipeline_duration = time.time() - pipeline_start
            
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'iteration': iteration,
                'pipeline_success': success,
                'pipeline_duration': pipeline_duration,
                'retry_count': int(self.pipeline.retry_count),
                'dlq_errors': int(self.pipeline.monitor_dead_letter_queue(5)),
                'chaos_experiments': len(self.chaos.experiments_log)
            }
            
            self.metrics.append(metrics)
            
            print(f"   ✅ Успех пайплайна: {success}")
            print(f"   ⏱️  Длительность: {pipeline_duration:.2f}с")
            print(f"   🔄 Retry попытки: {self.pipeline.retry_count}")
            
            self.pipeline.retry_count = 0
            
            time_left = duration - (time.time() - start_time)
            if time_left > interval:
                time.sleep(interval)
            else:
                break
        
        print(f"\n🎉 Сбор метрик завершен: {len(self.metrics)} итераций")
        return self.metrics
    
    def generate_resilience_report(self):
        if not self.metrics:
            print("❌ Нет данных для отчета")
            return None
        
        df = pd.DataFrame(self.metrics)
        
        success_rate = float(df['pipeline_success'].mean() * 100)
        avg_duration = float(df['pipeline_duration'].mean())
        total_retries = int(df['retry_count'].sum())
        total_dlq_errors = int(df['dlq_errors'].sum())
        
        print("\n📊 ОТЧЕТ ОБ УСТОЙЧИВОСТИ")
        print("=" * 50)
        print(f"🎯 Успешность пайплайна: {success_rate:.1f}%")
        print(f"⏱️  Среднее время выполнения: {avg_duration:.2f}с")
        print(f"🔄 Всего retry попыток: {total_retries}")
        print(f"💀 Ошибок в DLQ: {total_dlq_errors}")
        print(f"🎲 Chaos экспериментов: {len(self.chaos.experiments_log)}")
        
        self.create_visualizations(df)
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_experiments': len(self.metrics),           # <-- добавлено
            'success_rate': success_rate,
            'avg_duration': avg_duration,
            'total_retries': total_retries,
            'total_dlq_errors': total_dlq_errors,
            'total_chaos_experiments': len(self.chaos.experiments_log),
            'detailed_metrics': df.to_dict('records')
        }
        
        safe_json = convert_for_json(report)

        with open('resilience_report.json', 'w', encoding='utf-8') as f:
            json.dump(safe_json, f, indent=2, ensure_ascii=False)
        
        print("✅ Отчет сохранен в resilience_report.json")
        return safe_json
    
    def create_visualizations(self, df):
        print("📈 Создаем визуализации...")
        
        plt.figure(figsize=(12, 8))
        
        plt.subplot(2, 2, 1)
        plt.plot(df['iteration'], df['pipeline_success'].cumsum() / df['iteration'], marker='o')
        plt.title('Кумулятивная успешность пайплайна')
        plt.xlabel('Итерация')
        plt.ylabel('Успешность')
        plt.grid(True)
        
        plt.subplot(2, 2, 2)
        plt.plot(df['iteration'], df['pipeline_duration'], marker='s', color='orange')
        plt.title('Время выполнения пайплайна')
        plt.xlabel('Итерация')
        plt.ylabel('Секунды')
        plt.grid(True)
        
        plt.subplot(2, 2, 3)
        plt.bar(df['iteration'], df['retry_count'], color='red', alpha=0.7)
        plt.title('Retry попытки по итерациям')
        plt.xlabel('Итерация')
        plt.ylabel('Количество retry')
        plt.grid(True)
        
        plt.subplot(2, 2, 4)
        plt.bar(df['iteration'], df['dlq_errors'], color='purple', alpha=0.7)
        plt.title('Ошибки в DLQ по итерациям')
        plt.xlabel('Итерация')
        plt.ylabel('Ошибки в DLQ')
        plt.grid(True)
        
        plt.tight_layout()
        plt.savefig('resilience_metrics.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        print("✅ Визуализации сохранены в resilience_metrics.png")


# ============================================================
# Запуск вручную
# ============================================================
if __name__ == "__main__":
    monitor = ResilienceMonitor(use_localstack=True)
    
    print("🎯 ЗАПУСКАЕМ МОНИТОРИНГ УСТОЙЧИВОСТИ")
    print("=" * 50)
    
    metrics = monitor.collect_metrics(duration=300, interval=30)
    report = monitor.generate_resilience_report()
    
    if report:
        print(f"\n🎉 МОНИТОРИНГ ЗАВЕРШЕН")
        print(f"📈 Успешность системы: {report['success_rate']:.1f}%")
        
        if report['success_rate'] >= 80:
            print("✅ Система демонстрирует высокую устойчивость!")
        elif report['success_rate'] >= 60:
            print("⚠️  Система имеет среднюю устойчивость, нужны улучшения")
        else:
            print("❌ Система имеет низкую устойчивость, требуется доработка")
