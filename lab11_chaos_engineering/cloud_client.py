import boto3
import pandas as pd
import json
from io import StringIO, BytesIO
import os

class CloudDataClient:
    def __init__(self, use_localstack=True):
        self.use_localstack = use_localstack
        self.setup_clients()
        
    def setup_clients(self):
        """Настраиваем клиенты для AWS сервисов"""
        if self.use_localstack:
            # Используем LocalStack для локального тестирования
            self.s3_client = boto3.client(
                's3',
                endpoint_url='http://localhost:4566',
                aws_access_key_id='test',
                aws_secret_access_key='test',
                region_name='us-east-1'
            )
            self.sqs_client = boto3.client(
                'sqs',
                endpoint_url='http://localhost:4566',
                aws_access_key_id='test',
                aws_secret_access_key='test',
                region_name='us-east-1'
            )
        else:
            # Используем реальные AWS сервисы
            self.s3_client = boto3.client('s3')
            self.sqs_client = boto3.client('sqs')
    
    # S3 операции
    def create_bucket(self, bucket_name):
        """Создаем S3 bucket"""
        try:
            if self.use_localstack:
                self.s3_client.create_bucket(Bucket=bucket_name)
            else:
                self.s3_client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': 'us-east-1'}
                )
            print(f"✅ Bucket '{bucket_name}' создан")
            return True
        except Exception as e:
            print(f"❌ Ошибка создания bucket: {e}")
            return False
    
    def upload_csv_to_s3(self, dataframe, bucket_name, file_key):
        """Загружаем DataFrame в S3 как CSV"""
        try:
            # Конвертируем DataFrame в CSV
            csv_buffer = StringIO()
            dataframe.to_csv(csv_buffer, index=False)
            
            # Загружаем в S3
            self.s3_client.put_object(
                Bucket=bucket_name,
                Key=file_key,
                Body=csv_buffer.getvalue()
            )
            print(f"✅ Файл '{file_key}' загружен в S3")
            return True
        except Exception as e:
            print(f"❌ Ошибка загрузки в S3: {e}")
            return False
    
    def download_csv_from_s3(self, bucket_name, file_key):
        """Скачиваем CSV из S3 и возвращаем DataFrame"""
        try:
            response = self.s3_client.get_object(Bucket=bucket_name, Key=file_key)
            csv_content = response['Body'].read().decode('utf-8')
            dataframe = pd.read_csv(StringIO(csv_content))
            print(f"✅ Файл '{file_key}' скачан из S3")
            return dataframe
        except Exception as e:
            print(f"❌ Ошибка скачивания из S3: {e}")
            return None
    
    def list_bucket_files(self, bucket_name):
        """Получаем список файлов в bucket"""
        try:
            response = self.s3_client.list_objects_v2(Bucket=bucket_name)
            if 'Contents' in response:
                files = [obj['Key'] for obj in response['Contents']]
                print(f"📁 Файлы в bucket '{bucket_name}': {files}")
                return files
            else:
                print(f"📁 Bucket '{bucket_name}' пуст")
                return []
        except Exception as e:
            print(f"❌ Ошибка получения списка файлов: {e}")
            return []
    
    # SQS операции
    def create_queue(self, queue_name):
        """Создаем SQS очередь"""
        try:
            response = self.sqs_client.create_queue(QueueName=queue_name)
            queue_url = response['QueueUrl']
            print(f"✅ Очередь '{queue_name}' создана: {queue_url}")
            return queue_url
        except Exception as e:
            print(f"❌ Ошибка создания очереди: {e}")
            return None
    
    def send_message(self, queue_url, message_body):
        """Отправляем сообщение в SQS очередь"""
        try:
            response = self.sqs_client.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(message_body)
            )
            print(f"✅ Сообщение отправлено: {message_body}")
            return response['MessageId']
        except Exception as e:
            print(f"❌ Ошибка отправки сообщения: {e}")
            return None
    
    def receive_messages(self, queue_url, max_messages=10):
        """Получаем сообщения из SQS очереди"""
        try:
            response = self.sqs_client.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=max_messages,
                WaitTimeSeconds=5
            )
            
            messages = []
            if 'Messages' in response:
                for msg in response['Messages']:
                    message_body = json.loads(msg['Body'])
                    messages.append({
                        'body': message_body,
                        'receipt_handle': msg['ReceiptHandle']
                    })
                print(f"✅ Получено {len(messages)} сообщений")
            else:
                print("📭 Нет новых сообщений")
            
            return messages
        except Exception as e:
            print(f"❌ Ошибка получения сообщений: {e}")
            return []
    
    def delete_message(self, queue_url, receipt_handle):
        """Удаляем сообщение из очереди"""
        try:
            self.sqs_client.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=receipt_handle
            )
            print("✅ Сообщение удалено из очереди")
            return True
        except Exception as e:
            print(f"❌ Ошибка удаления сообщения: {e}")
            return False

# Пример использования
if __name__ == "__main__":
    # Создаем клиент для локального тестирования
    client = CloudDataClient(use_localstack=True)
    
    # Тестируем S3
    client.create_bucket("test-bucket")
    
    # Создаем тестовые данные
    test_data = pd.DataFrame({
        'id': [1, 2, 3],
        'name': ['Alice', 'Bob', 'Charlie'],
        'value': [100, 200, 300]
    })
    
    client.upload_csv_to_s3(test_data, "test-bucket", "test-data.csv")
    client.list_bucket_files("test-bucket")
    
    # Тестируем SQS
    queue_url = client.create_queue("test-queue")
    client.send_message(queue_url, {"type": "test", "data": "hello"})
    messages = client.receive_messages(queue_url)
    
    for msg in messages:
        print(f"Получено: {msg['body']}")
        client.delete_message(queue_url, msg['receipt_handle'])
