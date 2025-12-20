# Lab 5: Nonfunctional Testing

Лабораторная работа по нефункциональному тестированию, включающая тестирование надежности, масштабируемости, совместимости и восстановления.

---

## Структура проекта

```
lab5_nonfunctional_testing/
|
├── README.md                          # Этот файл
├── requirements.txt                   # Зависимости Python
|
├── reliability/                       # Часть 1: Надежность (3 балла)
|   ├── chaos_testing/
|   |   ├── database_failure_test.py   # Тест отказа БД
|   |   ├── memory_stress_test.py      # Тест стресса памяти
|   |   ├── cpu_stress_test.py         # Тест стресса CPU
|   |   ├── network_failure_test.py    # Тест сетевого отказа
|   |   └── network_test.jmx           # JMeter конфигурация
|   |
|   └── longevity_testing/
|       └── longevity_test.py          # Долгосрочный тест стабильности
|
├── scalability/                       # Часть 2: Масштабируемость (3 балла)
|   ├── horizontal_scaling/
|   |   ├── scaling_test.py            # Тест горизонтального масштабирования
|   |   ├── docker-compose.scale.yml   # Docker Swarm конфигурация
|   |   └── docker-compose.fixed.yml   # Фиксированная конфигурация
|   |
|   └── load_spike/
|       └── spike_test.py              # Тест всплесков нагрузки
|
├── compatibility/                     # Часть 3: Совместимость (2 балла)
|   ├── api_reliability/
|   |   └── api_reliability_test.py    # Тест надежности API
|   |
|   └── cross_environment/
|       └── environment_test.py        # Тест кросс-платформенности
|
└── recovery/                          # Часть 4: Восстановление (2 балла)
    ├── disaster_recovery/
    |   └── disaster_recovery_test.sql # Тест восстановления после сбоя
    |
    └── data_integrity/
        └── data_integrity_test.sql    # Тест целостности данных (ACID)
```

---

## Как запустить тесты

### Шаг 1: Установка зависимостей

```powershell
cd lab5_nonfunctional_testing

# Создать виртуальное окружение
python -m venv venv

# Активировать (Windows PowerShell)
.\venv\Scripts\Activate

# Установить зависимости
pip install -r requirements.txt
```

---

### Шаг 2: Запуск тестов по частям

#### Часть 1: Надежность

```powershell
# Database failure test
python reliability\chaos_testing\database_failure_test.py

# Memory stress test (500 MB)
python reliability\chaos_testing\memory_stress_test.py 500

# CPU stress test (60 секунд, 80% нагрузка)
python reliability\chaos_testing\cpu_stress_test.py 60 80

# Longevity test - быстрая версия (6 минут)
python reliability\longevity_testing\longevity_test.py 0.1

# Network failure test (Python)
python reliability\chaos_testing\network_failure_test.py

# Network test (JMeter) - требует запущенного Docker Swarm
jmeter -n -t reliability\chaos_testing\network_test.jmx -l network_results.jtl -e -o network_report
start network_report\index.html
```

---

#### Часть 2: Масштабируемость (требует Docker)

**Подготовка:**
```powershell
# Инициализировать Docker Swarm
docker swarm init

# Развернуть тестовое окружение
docker stack deploy -c scalability\horizontal_scaling\docker-compose.scale.yml testapp

# Проверить что сервисы запущены (должно быть 1/1)
docker service ls

# Проверить что loadbalancer доступен
curl http://localhost:80
```

**Запуск тестов:**
```powershell
# Horizontal scaling test
python scalability\horizontal_scaling\scaling_test.py http://localhost:80

# Load spike test
python scalability\load_spike\spike_test.py http://localhost:80
```

**Очистка после тестов:**
```powershell
# Остановить stack
docker stack rm testapp

# Выйти из swarm (опционально)
docker swarm leave --force
```

---

#### Часть 3: Совместимость

```powershell
# API reliability test
python compatibility\api_reliability\api_reliability_test.py

# Cross-environment compatibility test
python compatibility\cross_environment\environment_test.py
```

---

#### Часть 4: Восстановление (требует MySQL через Docker)

```powershell
# Запустить MySQL в Docker
docker run -d -p 3306:3306 -e MYSQL_ROOT_PASSWORD=root --name mysql-test mysql:8.0

# Подождать 15 секунд для инициализации
Start-Sleep -Seconds 15

# Disaster recovery test
Get-Content recovery\disaster_recovery\disaster_recovery_test.sql | docker exec -i mysql-test mysql -uroot -proot

# Data integrity test
Get-Content recovery\data_integrity\data_integrity_test.sql | docker exec -i mysql-test mysql -uroot -proot

# Остановить MySQL
docker stop mysql-test
docker rm mysql-test
```

---

### Шаг 3: Проверка результатов

```powershell
# Просмотр логов
Get-ChildItem *.log

# Просмотр JSON метрик
Get-ChildItem *.json

# Чтение лога
Get-Content database_failure_*.log
```

---

## Результаты выполнения

### Успешно выполнено (10 тестов)

1. **database_failure_test.py** - MTTR: 539ms, Failure Rate: 25.93%
2. **memory_stress_test.py** - Memory leak: 10.05 MB (< 50 MB)
3. **cpu_stress_test.py** - Performance degradation: 7.7% (< 50%)
4. **longevity_test.py** - No memory/connection leaks
5. **network_failure_test.py** - 4/4 tests passed (Timeout, Connection Refused, Intermittent, Recovery)
6. **api_reliability_test.py** - Circuit breaker: 80% protection
7. **environment_test.py** - Python 3.8-3.12 compatible
8. **spike_test.py** - All patterns tested
9. **scaling_test.py** - Horizontal scaling verified
10. **SQL tests** - ACID compliance verified

---

## Системные требования

- **OS:** Windows 10/11
- **Python:** 3.8 или выше
- **RAM:** Минимум 4 GB (рекомендуется 8 GB)
- **Docker Desktop:** 20.10+
- **JMeter:** 5.6+ (для network_test.jmx)

---

## Зависимости Python

```
requests>=2.31.0
psutil>=5.9.6
urllib3>=2.1.0
certifi>=2023.11.17
```

Установка: `pip install -r requirements.txt`

---

## Полезные команды

### Просмотр запущенных тестов
```powershell
# Все процессы Python
Get-Process python

# Все Docker контейнеры
docker ps

# Все Docker сервисы
docker service ls
```

### Остановка тестов
```powershell
# Остановить Python тест - нажать Ctrl+C

# Остановить Docker stack
docker stack rm testapp

# Остановить MySQL
docker stop mysql-test
```

### Очистка
```powershell
# Удалить все логи и метрики
Remove-Item *.log, *.json

# Очистка Docker
docker system prune -a

# Деактивировать venv
deactivate
```

---

**Дата создания:** 2025-12-10
**Версия:** 1.0
