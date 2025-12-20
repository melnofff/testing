import subprocess
import time
import requests
import socket

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


def start_localstack():
    """Запуск LocalStack через docker compose"""
    print("🚀 Запускаем LocalStack...")

    # Проверяем Docker
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
    except:
        print("❌ Docker Desktop не установлен или не запущен")
        return False

    print("📦 Запускаем контейнеры LocalStack...")

    process = subprocess.Popen(
        ["docker-compose", "up", "-d"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = process.communicate()

    if process.returncode != 0:
        print("❌ Ошибка docker-compose:")
        print(stderr.decode())
        return False

    # Ждём доступности порта
    if not wait_for_localstack():
        return False

    # Доп. проверка health endpoint
    try:
        r = requests.get("http://localhost:4566/_localstack/health", timeout=30)
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
            else:
                print(f"⚠️ Сервисы ещё запускаются - S3: {s3_status}, SQS: {sqs_status}")
                return True
    except Exception as e:
        print(f"⚠️ Не удалось проверить health: {e}")
        pass

    print("⚠️ LocalStack поднялся, но endpoint health не отвечает корректно")
    return True


def stop_localstack():
    """Остановка LocalStack"""
    print("🛑 Останавливаем LocalStack...")
    try:
        subprocess.run(["docker-compose", "down"], check=True)
        print("✅ LocalStack остановлен")
    except Exception as e:
        print(f"❌ Ошибка остановки: {e}")


# Точка входа для ручного запуска
if __name__ == "__main__":
    start_localstack()
