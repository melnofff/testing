import time
from datetime import datetime
from cloud_client import CloudDataClient
import json

class CloudMonitor:
    def __init__(self, use_localstack=True):
        self.client = CloudDataClient(use_localstack)
        self.metrics = {
            's3_operations': 0,
            'sqs_messages_sent': 0,
            'sqs_messages_received': 0,
            'errors': 0,
            'start_time': datetime.now()
        }
    
    def monitor_s3_bucket(self, bucket_name, check_interval=30):
        """Мониторим S3 bucket на новые файлы"""
        print(f"👀 Мониторим S3 bucket: {bucket_name}")
        
        last_files = set()
        
        while True:
            try:
                current_files = set(self.client.list_bucket_files(bucket_name))
                
                # Находим новые файлы
                new_files = current_files - last_files
                if new_files:
                    print(f"📁 Новые файлы в {bucket_name}: {new_files}")
                    
                    # Отправляем уведомление о новых файлах
                    for file in new_files:
                        notification = {
                            'event_type': 'NEW_S3_FILE',
                            'bucket': bucket_name,
                            'filename': file,
                            'timestamp': datetime.now().isoformat()
                        }
                        self.client.send_message(
                            self.client.create_queue("monitoring-queue"),
                            notification
                        )
                        self.metrics['sqs_messages_sent'] += 1
                
                last_files = current_files
                self.metrics['s3_operations'] += 1
                
            except Exception as e:
                print(f"❌ Ошибка мониторинга S3: {e}")
                self.metrics['errors'] += 1
            
            time.sleep(check_interval)
    
    def monitor_sqs_queue(self, queue_url, check_interval=10):
        """Мониторим SQS очередь на новые сообщения"""
        print(f"👀 Мониторим SQS очередь: {queue_url}")
        
        while True:
            try:
                messages = self.client.receive_messages(queue_url)
                
                if messages:
                    print(f"📨 Получено {len(messages)} сообщений")
                    
                    for msg in messages:
                        message_body = msg['body']
                        print(f"   📝 Сообщение: {message_body}")
                        
                        # Обрабатываем сообщение
                        self.process_monitoring_message(message_body)
                        
                        # Удаляем сообщение
                        self.client.delete_message(queue_url, msg['receipt_handle'])
                    
                    self.metrics['sqs_messages_received'] += len(messages)
                
            except Exception as e:
                print(f"❌ Ошибка мониторинга SQS: {e}")
                self.metrics['errors'] += 1
            
            time.sleep(check_interval)
    
    def process_monitoring_message(self, message):
        """Обрабатываем сообщения мониторинга"""
        event_type = message.get('event_type')
        
        if event_type == 'NEW_S3_FILE':
            print(f"   🚨 Обнаружен новый файл: {message['filename']}")
            
        elif event_type == 'RAW_DATA_UPLOADED':
            print(f"   📊 Загружены новые сырые данные: {message['record_count']} записей")
            
        elif event_type == 'DATA_PROCESSED':
            print(f"   ✅ Данные обработаны: {message['input_file']} -> {message['output_file']}")
    
    def print_metrics(self):
        """Выводим метрики мониторинга"""
        current_time = datetime.now()
        uptime = (current_time - self.metrics['start_time']).total_seconds()
        
        print("\n📊 МЕТРИКИ МОНИТОРИНГА:")
        print(f"⏱️  Uptime: {uptime:.0f} секунд")
        print(f"📁 S3 операций: {self.metrics['s3_operations']}")
        print(f"📤 SQS сообщений отправлено: {self.metrics['sqs_messages_sent']}")
        print(f"📥 SQS сообщений получено: {self.metrics['sqs_messages_received']}")
        print(f"❌ Ошибок: {self.metrics['errors']}")
        
        if uptime > 0:
            ops_per_second = self.metrics['s3_operations'] / uptime
            print(f"⚡ Операций в секунду: {ops_per_second:.2f}")

# Пример использования
if __name__ == "__main__":
    import threading
    
    monitor = CloudMonitor(use_localstack=True)
    
    print("🚀 Запускаем систему мониторинга облачных сервисов...")
    
    # Запускаем мониторинг в отдельных потоках
    s3_thread = threading.Thread(
        target=monitor.monitor_s3_bucket,
        args=("raw-data-bucket", 15)  # Проверяем каждые 15 секунд
    )
    s3_thread.daemon = True
    
    sqs_thread = threading.Thread(
        target=monitor.monitor_sqs_queue,
        args=(monitor.client.create_queue("monitoring-queue"), 10)
    )
    sqs_thread.daemon = True
    
    s3_thread.start()
    sqs_thread.start()
    
    # Периодически выводим метрики
    try:
        while True:
            time.sleep(60)
            monitor.print_metrics()
    except KeyboardInterrupt:
        print("\n🛑 Мониторинг остановлен")
