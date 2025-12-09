import time
import random
from datetime import datetime
import pandas as pd
from chaos_framework import ChaosFramework

class ResilientDataPipeline:
    def __init__(self, use_localstack=True):
        self.chaos = ChaosFramework(use_localstack)
        self.client = self.chaos.client  # Используем тот же клиент, что и в chaos
        self.retry_count = 0
        self.max_retries = 3
        self.setup_infrastructure()
    
    def setup_infrastructure(self):
        """Настраиваем инфраструктуру"""
        print("🏗️ Настраиваем устойчивую инфраструктуру...")
        
        self.raw_bucket = "resilient-raw-data"
        self.processed_bucket = "resilient-processed-data"
        self.dead_letter_queue = self.client.create_queue("dead-letter-queue")
        
        self.client.create_bucket(self.raw_bucket)
        self.client.create_bucket(self.processed_bucket)
        
        print("✅ Инфраструктура настроена")
    
    def generate_sample_data(self, num_records=20):
        """Генерируем тестовые данные"""
        departments = ['IT', 'HR', 'Finance', 'Marketing']
        
        data = []
        for i in range(num_records):
            record = {
                'transaction_id': f"TXN_{i+1:06d}",
                'customer_id': f"CUST_{random.randint(1000, 9999)}",
                'amount': round(random.uniform(10.0, 1000.0), 2),
                'department': random.choice(departments),
                'timestamp': datetime.now().isoformat(),
                'status': random.choice(['PENDING', 'COMPLETED', 'FAILED'])
            }
            data.append(record)
        
        return pd.DataFrame(data)
    
    def upload_with_retry(self, dataframe, bucket_name, file_key, max_retries=3):
        """Загружаем данные с повторными попытками при ошибках"""
        for attempt in range(max_retries):
            try:
                print(f"🔄 Попытка загрузки {attempt + 1}/{max_retries}...")
                success = self.client.upload_csv_to_s3(dataframe, bucket_name, file_key)

                if success:
                    print("✅ Данные успешно загружены")
                    return True
                else:
                    print("❌ Ошибка загрузки, повторяем...")
                    if attempt < max_retries - 1:  # Не делаем задержку после последней попытки
                        time.sleep(2 ** attempt)  # Экспоненциальная backoff задержка

            except Exception as e:
                print(f"❌ Ошибка на попытке {attempt + 1}: {e}")
                if attempt < max_retries - 1:  # Не делаем задержку после последней попытки
                    time.sleep(2 ** attempt)

        # Если все попытки не удались, отправляем в dead letter queue
        print("💀 Все попытки не удались, отправляем в DLQ...")
        try:
            error_message = {
                'error_type': 'UPLOAD_FAILED',
                'bucket': bucket_name,
                'file_key': file_key,
                'timestamp': datetime.now().isoformat(),
                'attempts': max_retries
            }
            self.client.send_message(self.dead_letter_queue, error_message)
        except Exception as e:
            print(f"❌ Не удалось отправить сообщение в DLQ: {e}")
        return False
    
    def process_with_circuit_breaker(self, operation_func, *args, **kwargs):
        """Реализуем Circuit Breaker паттерн"""
        max_failures = 3
        reset_timeout = 30  # секунды
        
        if hasattr(self, 'circuit_breaker_failures') and self.circuit_breaker_failures >= max_failures:
            if time.time() - getattr(self, 'circuit_breaker_opened', 0) < reset_timeout:
                print("🔴 Circuit Breaker: операция заблокирована")
                return None
            else:
                # Сброс circuit breaker после timeout
                print("🟡 Circuit Breaker: пробуем сбросить...")
                self.circuit_breaker_failures = 0
        
        try:
            result = operation_func(*args, **kwargs)
            # Сбрасываем счетчик ошибок при успехе
            if hasattr(self, 'circuit_breaker_failures'):
                self.circuit_breaker_failures = 0
            return result
            
        except Exception as e:
            # Увеличиваем счетчик ошибок
            if not hasattr(self, 'circuit_breaker_failures'):
                self.circuit_breaker_failures = 0
            self.circuit_breaker_failures += 1
            
            if self.circuit_breaker_failures >= max_failures:
                self.circuit_breaker_opened = time.time()
                print("🔴 Circuit Breaker: открыт после множественных ошибок")
            
            print(f"❌ Ошибка в операции: {e}")
            raise
    
    def run_resilient_pipeline(self, enable_chaos=False):
        """Запускаем устойчивый пайплайн"""
        print("🚀 ЗАПУСКАЕМ УСТОЙЧИВЫЙ ПАЙПЛАЙН")
        if enable_chaos:
            print("🎲 CHAOS ENGINEERING ВКЛЮЧЕН")
        
        # Генерируем данные
        data = self.generate_sample_data(15)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"transactions_{timestamp}.csv"
        
        # Включаем хаос если нужно
        if enable_chaos:
            self.chaos.data_corruption(0.3)
        
        # Загружаем данные с retry логикой
        upload_success = self.upload_with_retry(
            data, self.raw_bucket, f"raw/{filename}", max_retries=3
        )
        
        # Выключаем коррупцию данных
        if enable_chaos:
            self.chaos.stop_data_corruption()
        
        if upload_success:
            # Обрабатываем данные с circuit breaker
            try:
                processed_data = self.process_with_circuit_breaker(
                    self.process_data, filename
                )
                
                if processed_data is not None:
                    print("🎉 Пайплайн успешно завершен!")
                    return True
                else:
                    print("💥 Пайплайн завершен с ошибками")
                    return False
                    
            except Exception as e:
                print(f"💥 Критическая ошибка обработки: {e}")
                return False
        else:
            print("💥 Не удалось загрузить данные")
            return False
    
    def process_data(self, filename):
        """Обрабатываем данные"""
        print(f"🔄 Обрабатываем данные: {filename}")
        
        # Скачиваем данные
        raw_data = self.client.download_csv_from_s3(
            self.raw_bucket, f"raw/{filename}"
        )
        
        if raw_data is None:
            raise Exception("Не удалось загрузить данные для обработки")
        
        # Валидируем данные
        self.validate_data(raw_data)
        
        # Обрабатываем данные
        processed_data = raw_data.copy()
        
        # Добавляем вычисляемые поля
        processed_data['amount_category'] = processed_data['amount'].apply(
            lambda x: 'SMALL' if x < 100 else 'MEDIUM' if x < 500 else 'LARGE'
        )
        
        processed_data['processing_timestamp'] = datetime.now().isoformat()
        
        # Сохраняем обработанные данные
        success = self.client.upload_csv_to_s3(
            processed_data, self.processed_bucket, f"processed/{filename}"
        )
        
        if not success:
            raise Exception("Не удалось сохранить обработанные данные")
        
        print("✅ Данные успешно обработаны")
        return processed_data
    
    def validate_data(self, dataframe):
        """Валидируем данные перед обработкой"""
        print("🔍 Валидируем данные...")
        
        # Проверяем обязательные поля
        required_columns = ['transaction_id', 'customer_id', 'amount', 'department']
        for col in required_columns:
            if col not in dataframe.columns:
                raise Exception(f"Отсутствует обязательная колонка: {col}")
        
        # Проверяем что amount числовой и положительный
        if (dataframe['amount'] <= 0).any():
            raise Exception("Обнаружены неположительные значения amount")
        
        # Проверяем уникальность transaction_id
        if dataframe['transaction_id'].duplicated().any():
            raise Exception("Обнаружены дубликаты transaction_id")
        
        print("✅ Данные прошли валидацию")
    
    def monitor_dead_letter_queue(self, duration=60):
        """Мониторим dead letter queue на предмет ошибок"""
        print(f"👀 Мониторим Dead Letter Queue в течение {duration} секунд...")
        
        start_time = time.time()
        error_count = 0
        
        while time.time() - start_time < duration:
            messages = self.client.receive_messages(self.dead_letter_queue)
            
            for msg in messages:
                error_count += 1
                error_data = msg['body']
                print(f"💀 Ошибка в DLQ: {error_data['error_type']}")
                print(f"   📁 Файл: {error_data.get('file_key', 'N/A')}")
                print(f"   ⏰ Время: {error_data['timestamp']}")
                
                # Удаляем сообщение после обработки
                self.client.delete_message(self.dead_letter_queue, msg['receipt_handle'])
            
            time.sleep(5)  # Проверяем каждые 5 секунд
        
        print(f"📊 Найдено ошибок в DLQ: {error_count}")
        return error_count

# Пример использования
if __name__ == "__main__":
    # Тестируем устойчивый пайплайн
    pipeline = ResilientDataPipeline(use_localstack=True)
    
    print("🎯 ТЕСТ 1: Нормальная работа")
    success1 = pipeline.run_resilient_pipeline(enable_chaos=False)
    
    print("\n🎯 ТЕСТ 2: С Chaos Engineering")
    success2 = pipeline.run_resilient_pipeline(enable_chaos=True)
    
    print("\n📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    print(f"Тест 1 (нормальный): {'✅ УСПЕХ' if success1 else '❌ ПРОВАЛ'}")
    print(f"Тест 2 (с хаосом): {'✅ УСПЕХ' if success2 else '❌ ПРОВАЛ'}")
    
    # Мониторим DLQ
    pipeline.monitor_dead_letter_queue(30)