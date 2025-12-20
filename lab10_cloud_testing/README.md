# Лабораторная работа 10: Cloud Testing with LocalStack

## 📋 Описание проекта

Система тестирования облачных сервисов (AWS S3, SQS) с использованием LocalStack для локальной разработки. Проект демонстрирует работу с облачными хранилищами данных, очередями сообщений и ETL-пайплайнами без необходимости использования реальных AWS сервисов.

**Что делает система:**
- 📊 Генерирует тестовые данные о сотрудниках
- 📤 Загружает сырые данные в S3 (raw-data-bucket)
- 🔄 Обрабатывает данные (очистка, агрегация, вычисление метрик)
- 📥 Сохраняет обработанные данные и статистику в S3 (processed-data-bucket)
- 📨 Отправляет уведомления через SQS при каждом шаге
- 👀 Мониторит процессы и показывает метрики

## 🗂️ Структура проекта

```
lab10_cloud_testing/
├── cloud_client.py          # Клиент для работы с AWS S3 и SQS
├── cloud_pipeline.py        # ETL пайплайн для обработки данных
├── cloud_monitor.py         # Система мониторинга облачных ресурсов
├── start_localstack.py      # Скрипт запуска LocalStack через Docker
├── run_cloud_system.py      # Запуск всей системы
├── docker-compose.yml       # Конфигурация LocalStack
├── requirements.txt         # Зависимости Python
└── tests/                   # Тесты
    └── test_cloud_pipeline.py
```

## 🔧 Проблемы, которые были решены

### Проблема 1: Ошибка создания S3 bucket в LocalStack

**Ошибка:** `InvalidLocationConstraint: The specified location constraint is not valid`

**Причина:** LocalStack не требует и не поддерживает `CreateBucketConfiguration` для региона `us-east-1`.

**Решение:** Добавлена проверка на использование LocalStack:
```python
def create_bucket(self, bucket_name):
    """Создаем S3 bucket"""
    try:
        if self.use_localstack:
            # LocalStack - упрощенное создание bucket
            self.s3_client.create_bucket(Bucket=bucket_name)
        else:
            # Реальный AWS - с конфигурацией региона
            self.s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': 'us-east-1'}
            )
        print(f"✅ Bucket '{bucket_name}' создан")
        return True
    except Exception as e:
        print(f"❌ Ошибка создания bucket: {e}")
        return False
```

**Метод решения:** Условная логика (conditional logic) в зависимости от окружения (LocalStack vs AWS).

---

### Проблема 2: Проблемы с endpoint URL для boto3

**Ошибка:** `EndpointConnectionError: Could not connect to the endpoint URL`

**Решение:** Добавлена явная настройка endpoint для LocalStack:
```python
def setup_clients(self):
    """Настраиваем клиенты для AWS сервисов"""
    if self.use_localstack:
        # Используем LocalStack для локального тестирования
        self.s3_client = boto3.client(
            's3',
            endpoint_url='http://localhost:4566',  # LocalStack endpoint
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
```

**Метод решения:** Конфигурирование клиента с явным указанием endpoint URL для LocalStack.

---

### Проблема 3: LocalStack не запускается из-за отсутствия Docker

**Ошибка:** `FileNotFoundError: [Errno 2] No such file or directory: 'docker-compose'`

**Решение:** Добавлена проверка наличия Docker и docker-compose:
```python
def start_localstack():
    """Запускаем LocalStack через docker-compose"""
    # Проверяем Docker
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
    except:
        print("❌ Docker Desktop не установлен или не запущен")
        return False
    # ... остальной код
```

**Метод решения:** Предварительная валидация окружения (environment validation).

---

### Проблема 4: Таймаут при ожидании запуска LocalStack

**Ошибка:** `ConnectionError: Connection refused` при попытке создать bucket сразу после запуска.

**Решение:** Добавлена проверка готовности LocalStack с ретраями:
```python
def wait_for_localstack(timeout=30):
    """Ждём пока LocalStack начнёт слушать порт 4566"""
    print("⏳ Ожидаем запуск LocalStack...")
    host = "localhost"
    port = 4566
    start = time.time()

    while time.time() - start < timeout:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.connect((host, port))
                print("✅ LocalStack запущен (порт 4566 доступен)")
                return True
            except ConnectionRefusedError:
                time.sleep(1)

    print("❌ LocalStack не запустился вовремя")
    return False
```

**Метод решения:** Polling с retry logic и health check endpoint.

---

### Проблема 5: Неправильная работа с CSV в памяти

**Ошибка:** `UnicodeDecodeError` при скачивании CSV обратно из S3.

**Решение:** Явное указание кодировки UTF-8:
```python
def upload_csv_to_s3(self, dataframe, bucket_name, file_key):
    """Загружаем DataFrame в S3 как CSV"""
    try:
        # Конвертируем DataFrame в CSV с UTF-8
        csv_buffer = StringIO()
        dataframe.to_csv(csv_buffer, index=False, encoding='utf-8')
        
        # Загружаем в S3
        self.s3_client.put_object(
            Bucket=bucket_name,
            Key=file_key,
            Body=csv_buffer.getvalue().encode('utf-8')
        )
        print(f"✅ Файл '{file_key}' загружен в S3")
        return True
    except Exception as e:
        print(f"❌ Ошибка загрузки в S3: {e}")
        return False
```

**Метод решения:** Явная работа с кодировками при сериализации/десериализации данных.

---

### Проблема 6: Не удалялись сообщения из SQS очереди

**Причина:** Отсутствовал вызов `delete_message` после обработки.

**Решение:** Добавлен явный паттерн получения → обработка → удаление:
```python
def receive_messages(self, queue_url, max_messages=10):
    """Получаем сообщения из SQS очереди"""
    try:
        response = self.sqs_client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=max_messages,
            WaitTimeSeconds=5  # Long polling для эффективности
        )
        
        messages = []
        if 'Messages' in response:
            for msg in response['Messages']:
                message_body = json.loads(msg['Body'])
                messages.append({
                    'body': message_body,
                    'receipt_handle': msg['ReceiptHandle']  # Нужен для удаления!
                })
            print(f"✅ Получено {len(messages)} сообщений")
        else:
            print("📭 Нет новых сообщений")
        
        return messages
    except Exception as e:
        print(f"❌ Ошибка получения сообщений: {e}")
        return []

# Использование:
messages = client.receive_messages(queue_url)
for msg in messages:
    process_message(msg['body'])
    client.delete_message(queue_url, msg['receipt_handle'])
```

**Метод решения:** Правильная реализация паттерна обработки очередей с явным подтверждением (acknowledgment).

---

### Проблема 7: Порты LocalStack заняты другим процессом

**Ошибка:** `docker: Error response from daemon: driver failed programming external connectivity`

**Решение:** Добавлена проверка и очистка портов:
```python
def check_port_available(port=4566):
    """Проверяем свободен ли порт"""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', port))
    sock.close()
    
    if result == 0:
        print(f"⚠️ Порт {port} уже занят!")
        print("Останавливаем существующие контейнеры...")
        subprocess.run(["docker-compose", "down"], 
                      stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE)
        time.sleep(2)
        return False
    return True
```

**Метод решения:** Проверка доступности ресурсов перед запуском с автоматической очисткой.

---

### Проблема 8: Отсутствие обработки пустых buckets

**Ошибка:** `KeyError: 'Contents'`

**Решение:** Добавлена проверка наличия ключа:
```python
def list_bucket_files(self, bucket_name):
    """Получаем список файлов в bucket"""
    try:
        response = self.s3_client.list_objects_v2(Bucket=bucket_name)
        if 'Contents' in response:  # Проверка наличия файлов
            files = [obj['Key'] for obj in response['Contents']]
            print(f"📁 Файлы в bucket '{bucket_name}': {files}")
            return files
        else:
            print(f"📁 Bucket '{bucket_name}' пуст")
            return []
    except Exception as e:
        print(f"❌ Ошибка получения списка файлов: {e}")
        return []
```

**Метод решения:** Defensive programming - проверка существования ключей перед доступом.

---

### Проблема 9: Health endpoint не отвечает корректно (ДОПОЛНИТЕЛЬНО)

**Предупреждение:** `⚠️ LocalStack поднялся, но endpoint health не отвечает корректно`

**Причина:** Скрипт проверял только `status_code == 200`, но не анализировал JSON ответ.

**Решение:** Добавлена правильная проверка статуса сервисов:
```python
# Доп. проверка health endpoint
try:
    r = requests.get("http://localhost:4566/_localstack/health", timeout=5)
    if r.status_code == 200:
        health = r.json()
        services = health.get('services', {})
        # Проверяем что нужные сервисы запущены
        s3_status = services.get('s3', 'unknown')
        sqs_status = services.get('sqs', 'unknown')
        
        if s3_status in ['running', 'available'] and sqs_status in ['running', 'available']:
            print(f"✅ LocalStack готов к работе!")
            print(f"   S3: {s3_status}, SQS: {sqs_status}")
            return True
except Exception as e:
    print(f"⚠️ Не удалось проверить health: {e}")
```

**Метод решения:** Правильный парсинг JSON ответа и проверка статуса конкретных сервисов.

## 🚀 Как запустить проект

### Предварительные требования

- Python 3.8+
- Docker Desktop (должен быть запущен!)
- 4GB свободной RAM для LocalStack

### Установка зависимостей

**PowerShell:**
```powershell
cd lab10_cloud_testing
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Запуск LocalStack

**PowerShell:**
```powershell
# Вариант 1: Используя Python скрипт (рекомендуется)
python start_localstack.py

# Вариант 2: Напрямую через docker-compose
    docker-compose up -d
```

**Проверка запуска:**

PowerShell:
```powershell
Invoke-RestMethod -Uri "http://localhost:4566/_localstack/health" | ConvertTo-Json
```

**Ожидаемый ответ:**
```json
{
  "services": {
    "s3": "running",
    "sqs": "running",
    "dynamodb": "available",
    "lambda": "available",
    ...
  },
  "version": "3.6.0"
}
```

### Запуск тестов

**PowerShell:**
```powershell
# Запуск тестов pytest (это нужно для лабораторной)
python -m pytest tests/test_cloud_pipeline.py

# Запуск всех тестов
python -m pytest tests/ -v

# Запуск с coverage
pytest tests/ --cov=. --cov-report=html
```

### Остановка LocalStack

**PowerShell:**
```powershell
docker-compose down
```

## 🔧 Troubleshooting

### LocalStack показывает "⚠️ endpoint health не отвечает корректно"

**Это нормально!** Сообщение появляется когда:
1. LocalStack запустился и порт 4566 доступен ✅
2. Health endpoint возвращает JSON с информацией о сервисах ✅
3. Но скрипт хочет видеть более подробный статус

**Проверка что всё работает:**

PowerShell:
```powershell
# Должен вернуть JSON с "s3": "running" и "sqs": "running"
Invoke-RestMethod -Uri "http://localhost:4566/_localstack/health" | ConvertTo-Json -Depth 3
```

**Что важно в ответе:**
- `"s3": "running"` или `"s3": "available"` ✅
- `"sqs": "running"` или `"sqs": "available"` ✅
- `"version": "3.6.0"` ✅

Если видите эти статусы - LocalStack полностью готов к работе!

### Порт 4566 уже занят

```powershell
# Остановите все контейнеры
docker-compose down

# Проверьте что порт свободен
Test-NetConnection -ComputerName localhost -Port 4566

# Запустите снова
docker-compose up -d
```

### Docker не запускается

1. Убедитесь что **Docker Desktop** запущен
2. В PowerShell проверьте:
```powershell
docker --version
docker ps
```

### LocalStack долго запускается

Это нормально для первого запуска (скачивается образ). Подождите 1-2 минуты.

```powershell
# Следите за логами
docker logs -f localstack_lab10
```

## 📚 Зависимости

```
boto3==1.28.0
pandas==2.0.3
pytest==7.4.0
docker==6.1.0
requests==2.31.0
python-dotenv==1.0.0
```

## 🤝 Авторство

Лабораторная работа выполнена на основе инструкций "Лабораторная работа 10: Cloud Testing" с исправлением ошибок конфигурации LocalStack и добавлением robustness проверок.
