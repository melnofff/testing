import pytest
import pandas as pd
import time
from cloud_client import CloudDataClient
from cloud_pipeline import CloudDataPipeline
import os

class TestCloudPipeline:
    def setup_method(self):
        """Подготовка перед каждым тестом"""
        # Запускаем LocalStack если не запущен
        self.start_localstack_if_needed()
        
        self.client = CloudDataClient(use_localstack=True)
        self.pipeline = CloudDataPipeline(use_localstack=True)
        
    def start_localstack_if_needed(self):
        """Запускаем LocalStack если он не запущен"""
        try:
            import requests
            response = requests.get("http://localhost:4566/health")
            if response.status_code != 200:
                print("🔄 Запускаем LocalStack...")
                os.system("docker-compose up -d")
                time.sleep(10)
        except:
            print("🔄 Запускаем LocalStack...")
            os.system("docker-compose up -d")
            time.sleep(10)
    
    def test_s3_operations(self):
        """Тестируем операции с S3"""
        # Создаем тестовый bucket
        bucket_name = "test-s3-bucket"
        assert self.client.create_bucket(bucket_name)
        
        # Загружаем тестовые данные
        test_data = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['Test1', 'Test2', 'Test3']
        })
        
        assert self.client.upload_csv_to_s3(test_data, bucket_name, "test.csv")
        
        # Проверяем что файл загружен
        files = self.client.list_bucket_files(bucket_name)
        assert "test.csv" in files
        
        # Скачиваем и проверяем данные
        downloaded_data = self.client.download_csv_from_s3(bucket_name, "test.csv")
        assert downloaded_data is not None
        assert len(downloaded_data) == 3
        assert list(downloaded_data.columns) == ['id', 'name']
    
    def test_sqs_operations(self):
        """Тестируем операции с SQS"""
        # Создаем тестовую очередь
        queue_url = self.client.create_queue("test-sqs-queue")
        assert queue_url is not None
        
        # Отправляем сообщение
        test_message = {"test": "data", "value": 123}
        message_id = self.client.send_message(queue_url, test_message)
        assert message_id is not None
        
        # Получаем сообщение
        messages = self.client.receive_messages(queue_url)
        assert len(messages) == 1
        assert messages[0]['body'] == test_message
        
        # Удаляем сообщение
        assert self.client.delete_message(queue_url, messages[0]['receipt_handle'])
        
        # Проверяем что очередь пуста
        messages_after = self.client.receive_messages(queue_url)
        assert len(messages_after) == 0
    
    def test_data_generation(self):
        """Тестируем генерацию тестовых данных"""
        data = self.pipeline.generate_sample_data(10)
        
        assert data is not None
        assert len(data) == 10
        assert 'employee_id' in data.columns
        assert 'name' in data.columns
        assert 'department' in data.columns
        assert 'salary' in data.columns
        
        # Проверяем что зарплаты в разумных пределах
        assert data['salary'].min() >= 30000
        assert data['salary'].max() <= 100000
    
    def test_data_processing(self):
        """Тестируем обработку данных"""
        # Генерируем тестовые данные
        raw_data = self.pipeline.generate_sample_data(5)
        
        # Загружаем сырые данные
        self.pipeline.upload_raw_data(raw_data, "test_processing.csv")
        
        # Обрабатываем данные
        success = self.pipeline.process_data("test_processing.csv", "test_processed.csv")
        assert success
        
        # Проверяем что обработанные данные созданы
        processed_files = self.client.list_bucket_files(self.pipeline.processed_bucket)
        assert any("test_processed.csv" in f for f in processed_files)
        assert "stats/department_stats.csv" in processed_files
    
    def test_pipeline_integration(self):
        """Интеграционный тест всего пайплайна"""
        # Запускаем пайплайн с малым количеством данных
        self.pipeline.run_full_pipeline()
        
        # Проверяем что данные в нужных bucket'ах
        raw_files = self.client.list_bucket_files(self.pipeline.raw_bucket)
        processed_files = self.client.list_bucket_files(self.pipeline.processed_bucket)
        
        assert len(raw_files) > 0
        assert len(processed_files) > 0
        
        # Проверяем что есть статистика
        assert any("department_stats.csv" in f for f in processed_files)
    
    def test_error_handling(self):
        """Тестируем обработку ошибок"""
        # Пытаемся скачать несуществующий файл
        result = self.client.download_csv_from_s3("non-existent-bucket", "non-existent-file.csv")
        assert result is None
        
        # Пытаемся отправить сообщение в несуществующую очередь
        result = self.client.send_message("invalid-queue-url", {"test": "data"})
        assert result is None

if __name__ == "__main__":
    pytest.main([__file__, "-v"])