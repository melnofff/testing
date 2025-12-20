import subprocess
import time

def start_localstack():
    """Запускает LocalStack через docker-compose, но не падает, если уже работает."""
    print("🚀 Запускаем LocalStack...")

    try:
        # Попытка поднять контейнер (если уже запущен — просто оставляет его)
        result = subprocess.run(
            ["docker", "compose", "up", "-d"],
            capture_output=True,
            text=True
        )
        # Ждем пару секунд, чтобы сервис был готов
        time.sleep(3)

        # Проверяем, есть ли Running контейнер
        ps = subprocess.run(
            ["docker", "ps", "--filter", "name=localstack_lab10", "--filter", "status=running"],
            capture_output=True,
            text=True
        )
        if "localstack_lab10" in ps.stdout:
            print("✅ LocalStack запущен и работает")
            return True
        else:
            print("❌ LocalStack не удалось запустить")
            return False

    except Exception as e:
        print(f"❌ Ошибка запуска LocalStack: {e}")
        return False

def stop_localstack():
    """Останавливает LocalStack."""
    print("🛑 Останавливаем LocalStack...")
    try:
        subprocess.run(["docker", "compose", "down"], check=True)
        print("✅ LocalStack остановлен")
    except Exception as e:
        print(f"❌ Ошибка остановки LocalStack: {e}")
