from start_localstack import start_localstack, stop_localstack
from chaos_framework import ChaosFramework
from resilient_pipeline import ResilientDataPipeline
from resilience_monitor import ResilienceMonitor
import threading
import time
import sys

def run_chaos_engineering_system():
    """Запускаем всю систему Chaos Engineering"""
    print("🎲 ЗАПУСКАЕМ СИСТЕМУ CHAOS ENGINEERING")
    print("=" * 60)
    
    # 1. Запускаем LocalStack
    if not start_localstack():
        print("❌ Не удалось запустить LocalStack")
        return  
    
    time.sleep(5)
    
    # 2. Создаем компоненты системы
    chaos = ChaosFramework(use_localstack=True)
    pipeline = ResilientDataPipeline(use_localstack=True)
    monitor = ResilienceMonitor(use_localstack=True)
    
    print("\n🎯 ЭТАП 1: БАЗОВОЕ ТЕСТИРОВАНИЕ")
    print("Проверяем работу системы без хаоса...")
    
    # Запускаем пайплайн без хаоса
    success_normal = pipeline.run_resilient_pipeline(enable_chaos=False)
    print(f"Результат без хаоса: {'✅ УСПЕХ' if success_normal else '❌ ПРОВАЛ'}")
    
    print("\n🎯 ЭТАП 2: CHAOS ENGINEERING")
    print("Запускаем контролируемые эксперименты...")
    
    # Запускаем Chaos Monkey в отдельном потоке
    def run_chaos_monkey():
        chaos.run_chaos_monkey(duration=240, interval=20)  # 4 минуты
    
    chaos_thread = threading.Thread(target=run_chaos_monkey)
    chaos_thread.daemon = True
    chaos_thread.start()
    
    print("\n🎯 ЭТАП 3: МОНИТОРИНГ УСТОЙЧИВОСТИ")
    print("Собираем метрики под нагрузкой...")
    
    # Собираем метрики устойчивости
    metrics = monitor.collect_metrics(duration=240, interval=30)  # 4 минуты
    
    print("\n🎯 ЭТАП 4: АНАЛИЗ РЕЗУЛЬТАТОВ")
    
    # Генерируем отчеты
    chaos_report = chaos.generate_report()
    resilience_report = monitor.generate_resilience_report()
    
    print("\n📊 ИТОГОВЫЕ РЕЗУЛЬТАТЫ:")
    print("=" * 40)
    
    if chaos_report and resilience_report:
        print(f"🎲 Chaos экспериментов: {chaos_report['total_experiments']}")
        print(f"🎯 Успешность системы: {resilience_report['success_rate']:.1f}%")
        print(f"⏱️  Среднее время ответа: {resilience_report['avg_duration']:.2f}с")
        print(f"🔄 Всего retry: {resilience_report['total_retries']}")
        print(f"💀 Ошибок в DLQ: {resilience_report['total_dlq_errors']}")
        
        # Оценка устойчивости
        if resilience_report['success_rate'] >= 85:
            print("\n🏆 ВЫСОКАЯ УСТОЙЧИВОСТЬ: Система надежно работает под нагрузкой!")
        elif resilience_report['success_rate'] >= 70:
            print("\n⚠️  СРЕДНЯЯ УСТОЙЧИВОСТЬ: Система работает, но нужны улучшения")
        else:
            print("\n🚨 НИЗКАЯ УСТОЙЧИВОСТЬ: Система требует значительных улучшений")
    
    print("\n✅ СИСТЕМА CHAOS ENGINEERING ЗАВЕРШИЛА РАБОТУ")
    print("💡 Для остановки LocalStack выполните: docker-compose down")

if __name__ == "__main__":
    try:
        run_chaos_engineering_system()
    except KeyboardInterrupt:
        print("\n🛑 Ручная остановка системы")
        stop_localstack()
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        stop_localstack()