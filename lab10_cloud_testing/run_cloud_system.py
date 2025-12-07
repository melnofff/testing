from start_localstack import start_localstack, stop_localstack
from cloud_pipeline import CloudDataPipeline
from cloud_monitor import CloudMonitor
import threading
import time
import sys

def run_cloud_system():
    """Запускаем всю облачную систему"""
    print("☁️ ЗАПУСКАЕМ СИСТЕМУ ТЕСТИРОВАНИЯ ОБЛАЧНЫХ СЕРВИСОВ")
    print("=" * 60)
    
    # 1. Запускаем LocalStack
    if not start_localstack():
        print("❌ Не удалось запустить LocalStack. Проверьте установку Docker.")
        return
    
    # 2. Даем время на запуск
    time.sleep(5)
    
    # 3. Запускаем пайплайн
    print("\n🚀 ЗАПУСКАЕМ ОБЛАЧНЫЙ ПАЙПЛАЙН...")
    pipeline = CloudDataPipeline(use_localstack=True)
    
    # Запускаем пайплайн в отдельном потоке
    def run_pipeline():
        pipeline.run_full_pipeline()
    
    pipeline_thread = threading.Thread(target=run_pipeline)
    pipeline_thread.start()
    
    # 4. Запускаем мониторинг
    print("\n👀 ЗАПУСКАЕМ СИСТЕМУ МОНИТОРИНГА...")
    monitor = CloudMonitor(use_localstack=True)
    
    # Мониторим S3 bucket
    s3_thread = threading.Thread(
        target=monitor.monitor_s3_bucket,
        args=("raw-data-bucket", 10)
    )
    s3_thread.daemon = True
    
    # Мониторим SQS очередь
    sqs_thread = threading.Thread(
        target=monitor.monitor_sqs_queue,
        args=(monitor.client.create_queue("monitoring-queue"), 5)
    )
    sqs_thread.daemon = True
    
    s3_thread.start()
    sqs_thread.start()
    
    # 5. Ждем завершения пайплайна и показываем метрики
    pipeline_thread.join()
    
    print("\n" + "=" * 60)
    print("📊 ФИНАЛЬНЫЕ МЕТРИКИ СИСТЕМЫ:")
    monitor.print_metrics()
    
    print("\n✅ СИСТЕМА УСПЕШНО ЗАВЕРШИЛА РАБОТУ")
    print("💡 Для остановки LocalStack выполните: docker-compose down")

if __name__ == "__main__":
    try:
        run_cloud_system()
    except KeyboardInterrupt:
        print("\n🛑 Ручная остановка системы")
        stop_localstack()
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        stop_localstack()
