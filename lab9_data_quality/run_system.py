from data_quality_framework import DataQualityFramework
from dashboard import app
from notifications import NotificationSystem
import threading
import time

def run_dashboard():
    """Запускаем веб-дашборд"""
    print("🚀 Запускаем дашборд...")
    app.run(debug=False, host='0.0.0.0', port=5000)

def run_monitoring():
    """Запускаем мониторинг с уведомлениями"""
    print("🔍 Запускаем мониторинг...")
    notifier = NotificationSystem()
    
    while True:
        notifier.check_and_notify()
        print("⏰ Следующая проверка через 60 секунд...")
        time.sleep(60)  # Проверяем каждые 60 секунд

if __name__ == "__main__":
    print("🎯 Запускаем систему мониторинга качества данных")
    
    # Первоначальная проверка
    dq = DataQualityFramework()
    report = dq.generate_report()
    dq.create_visualizations()
    
    print(f"📊 Первоначальная проверка: {report['overall_score']:.1f}%")
    
    # Запускаем дашборд в отдельном потоке
    dashboard_thread = threading.Thread(target=run_dashboard)
    dashboard_thread.daemon = True
    dashboard_thread.start()
    
    # Запускаем мониторинг в основном потоке
    try:
        run_monitoring()
    except KeyboardInterrupt:
        print("\n🛑 Система мониторинга остановлена")
