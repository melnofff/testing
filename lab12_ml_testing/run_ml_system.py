from ml_pipeline import MLPipeline
from ml_api import app
from ml_testing_framework import MLTestingFramework
from ml_monitoring import MLMonitoring
import threading
import time
import subprocess
import sys

def run_ml_system():
    """Запускаем всю систему ML тестирования"""
    print("🎯 ЗАПУСКАЕМ ПОЛНУЮ СИСТЕМУ ML ТЕСТИРОВАНИЯ")
    print("=" * 60)

    # 1. Обучаем и сохраняем модель
    print("\n📚 ЭТАП 1: ПОДГОТОВКА ML PIPELINE")
    pipeline = MLPipeline()

    # Генерируем данные и обучаем модель
    data = pipeline.generate_sample_data(1500)
    X, y = pipeline.preprocess_data(data)
    pipeline.train_model(X, y)
    pipeline.save_model()

    print("✅ ML pipeline подготовлен")

    # 2. Запускаем API в отдельном потоке
    print("\n🌐 ЭТАП 2: ЗАПУСК ML API")

    def run_api():
        app.run(debug=False, host='0.0.0.0', port=5000)

    api_thread = threading.Thread(target=run_api)
    api_thread.daemon = True
    api_thread.start()

    # Даем время API на запуск
    print("⏳ Ожидаем запуск API...")
    time.sleep(5)

    # 3. Запускаем тестирование
    print("\n🧪 ЭТАП 3: ТЕСТИРОВАНИЕ ML PIPELINE")
    tester = MLTestingFramework()
    test_report = tester.run_complete_test_suite()

    # 4. Запускаем мониторинг
    print("\n📊 ЭТАП 4: МОНИТОРИНГ ML PIPELINE")
    monitor = MLMonitoring()
    monitor.pipeline.load_model()  # Загружаем обученную модель

    # Собираем данные мониторинга
    monitoring_data = monitor.collect_monitoring_data(days=2, interval_hours=3)
    monitor.create_monitoring_dashboard()
    monitoring_report = monitor.generate_monitoring_report()

    # 5. Финальный отчет
    print("\n📈 ЭТАП 5: ФИНАЛЬНЫЙ ОТЧЕТ")
    print("=" * 50)

    if test_report and monitoring_report:
        test_success_rate = test_report['success_rate']
        monitoring_stability = monitoring_report['stability_score']

        print(f"🎯 Результаты тестирования: {test_success_rate:.1f}%")
        print(f"📊 Стабильность мониторинга: {monitoring_stability:.1f}%")

        overall_score = (test_success_rate + monitoring_stability * 100) / 2
        print(f"\n🏆 ОБЩАЯ ОЦЕНКА ML PIPELINE: {overall_score:.1f}%")

        if overall_score >= 80:
            print("✅ ОТЛИЧНО: ML pipeline готов к продакшену!")
        elif overall_score >= 65:
            print("⚠️  ХОРОШО: ML pipeline работает, рекомендованы улучшения")
        else:
            print("🚨 ТРЕБУЕТСЯ РАБОТА: ML pipeline не готов к продакшену")

    print("\n✅ СИСТЕМА ML ТЕСТИРОВАНИЯ ЗАВЕРШИЛА РАБОТУ")
    print("💡 ML API продолжает работать на http://localhost:5000")
    print("💡 Для остановки нажмите Ctrl+C")

if __name__ == "__main__":
    try:
        run_ml_system()

        # Держим программу активной
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n🛑 Остановка системы ML тестирования")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
