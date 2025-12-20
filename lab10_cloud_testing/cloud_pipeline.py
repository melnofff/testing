import pandas as pd
from cloud_client import CloudDataClient
import time
from datetime import datetime
import json

class CloudDataPipeline:
    def __init__(self, use_localstack=True):
        self.client = CloudDataClient(use_localstack)
        self.setup_infrastructure()
    
    def setup_infrastructure(self):
        """Создаем необходимую инфраструктуру"""
        print("🏗️ Настраиваем облачную инфраструктуру...")
        
        # Создаем S3 bucket для сырых данных
        self.raw_bucket = "raw-data-bucket"
        self.client.create_bucket(self.raw_bucket)
        
        # Создаем S3 bucket для обработанных данных
        self.processed_bucket = "processed-data-bucket" 
        self.client.create_bucket(self.processed_bucket)
        
        # Создаем SQS очередь для уведомлений
        self.notification_queue = self.client.create_queue("data-processing-queue")
        
        print("✅ Инфраструктура настроена")
    
    def generate_sample_data(self, num_records=100):
        """Генерируем тестовые данные"""
        print(f"📊 Генерируем {num_records} тестовых записей...")
        
        import random
        departments = ['IT', 'HR', 'Finance', 'Marketing', 'Sales']
        
        data = []
        for i in range(num_records):
            record = {
                'employee_id': i + 1,
                'name': f'Employee_{i+1}',
                'department': random.choice(departments),
                'salary': random.randint(30000, 100000),
                'join_date': f'202{random.randint(0,3)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}',
                'performance_score': round(random.uniform(1.0, 5.0), 2)
            }
            data.append(record)
        
        dataframe = pd.DataFrame(data)
        print(f"✅ Сгенерировано {len(dataframe)} записей")
        return dataframe
    
    def upload_raw_data(self, dataframe, filename):
        """Загружаем сырые данные в S3"""
        print(f"📤 Загружаем сырые данные в {self.raw_bucket}...")
        
        success = self.client.upload_csv_to_s3(
            dataframe, self.raw_bucket, f"raw/{filename}"
        )
        
        if success:
            # Отправляем уведомление о новой загрузке
            notification = {
                'event_type': 'RAW_DATA_UPLOADED',
                'bucket': self.raw_bucket,
                'filename': f"raw/{filename}",
                'timestamp': datetime.now().isoformat(),
                'record_count': len(dataframe)
            }
            self.client.send_message(self.notification_queue, notification)
        
        return success
    
    def process_data(self, input_filename, output_filename):
        """Обрабатываем данные: чистим и обогащаем"""
        print(f"🔄 Обрабатываем данные: {input_filename} -> {output_filename}")
        
        # Скачиваем сырые данные
        raw_data = self.client.download_csv_from_s3(
            self.raw_bucket, f"raw/{input_filename}"
        )
        
        if raw_data is None:
            print("❌ Не удалось загрузить данные для обработки")
            return False
        
        # Преобразуем данные
        processed_data = raw_data.copy()
        
        # 1. Добавляем вычисляемые поля
        processed_data['salary_category'] = processed_data['salary'].apply(
            lambda x: 'Low' if x < 50000 else 'Medium' if x < 80000 else 'High'
        )
        
        processed_data['experience_years'] = 2024 - pd.to_datetime(
            processed_data['join_date']
        ).dt.year
        
        # 2. Очищаем данные
        processed_data['name'] = processed_data['name'].str.strip()
        
        # 3. Добавляем агрегированные метрики
        dept_stats = processed_data.groupby('department').agg({
            'salary': ['mean', 'min', 'max'],
            'performance_score': 'mean'
        }).round(2)
        
        dept_stats.columns = ['avg_salary', 'min_salary', 'max_salary', 'avg_performance']
        dept_stats = dept_stats.reset_index()
        
        print("✅ Данные обработаны")
        
        # Сохраняем обработанные данные
        success1 = self.client.upload_csv_to_s3(
            processed_data, self.processed_bucket, f"processed/{output_filename}"
        )
        
        success2 = self.client.upload_csv_to_s3(
            dept_stats, self.processed_bucket, f"stats/department_stats.csv"
        )
        
        if success1 and success2:
            # Отправляем уведомление об обработке
            notification = {
                'event_type': 'DATA_PROCESSED',
                'input_file': input_filename,
                'output_file': output_filename,
                'timestamp': datetime.now().isoformat(),
                'record_count': len(processed_data)
            }
            self.client.send_message(self.notification_queue, notification)
        
        return success1 and success2
    
    def monitor_queue(self, duration_seconds=30):
        """Мониторим очередь сообщений"""
        print(f"👀 Мониторим очередь в течение {duration_seconds} секунд...")
        
        start_time = time.time()
        messages_processed = 0
        
        while time.time() - start_time < duration_seconds:
            messages = self.client.receive_messages(self.notification_queue)
            
            for msg in messages:
                message_body = msg['body']
                print(f"📨 Получено сообщение: {message_body['event_type']}")
                
                # Обрабатываем разные типы сообщений
                if message_body['event_type'] == 'RAW_DATA_UPLOADED':
                    print(f"   📊 Новые данные: {message_body['filename']}")
                    print(f"   📈 Записей: {message_body['record_count']}")
                
                elif message_body['event_type'] == 'DATA_PROCESSED':
                    print(f"   ✅ Обработаны данные: {message_body['input_file']} -> {message_body['output_file']}")
                
                # Удаляем обработанное сообщение
                self.client.delete_message(self.notification_queue, msg['receipt_handle'])
                messages_processed += 1
            
            time.sleep(2)  # Проверяем каждые 2 секунды
        
        print(f"✅ Обработано сообщений: {messages_processed}")
        return messages_processed
    
    def run_full_pipeline(self):
        """Запускаем полный пайплайн"""
        print("🚀 Запускаем полный облачный пайплайн...")
        
        # 1. Генерируем тестовые данные
        sample_data = self.generate_sample_data(50)
        
        # 2. Загружаем сырые данные
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        input_filename = f"employees_{timestamp}.csv"
        self.upload_raw_data(sample_data, input_filename)
        
        # 3. Обрабатываем данные
        output_filename = f"processed_employees_{timestamp}.csv"
        self.process_data(input_filename, output_filename)
        
        # 4. Мониторим очередь
        self.monitor_queue(10)
        
        # 5. Показываем результаты
        print("\n📊 РЕЗУЛЬТАТЫ ПАЙПЛАЙНА:")
        print(f"📁 Сырые данные: {self.client.list_bucket_files(self.raw_bucket)}")
        print(f"📁 Обработанные данные: {self.client.list_bucket_files(self.processed_bucket)}")
        
        print("🎉 Пайплайн завершен!")

# Пример использования
if __name__ == "__main__":
    # Запускаем пайплайн с LocalStack
    pipeline = CloudDataPipeline(use_localstack=True)
    pipeline.run_full_pipeline()