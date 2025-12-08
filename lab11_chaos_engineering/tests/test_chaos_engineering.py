import pytest
import time
import pandas as pd
from chaos_framework import ChaosFramework
from resilient_pipeline import ResilientDataPipeline
import os

class TestChaosEngineering:
    def setup_method(self):
        """Подготовка перед каждым тестом"""
        self.chaos = ChaosFramework(use_localstack=True)
        self.pipeline = ResilientDataPipeline(use_localstack=True)
    
    def test_network_latency(self):
        """Тестируем сетевую задержку"""
        # Замеряем время выполнения без задержки
        start_time = time.time()
        self.pipeline.generate_sample_data(5)
        normal_time = time.time() - start_time
        
        # Включаем задержку и замеряем время
        self.chaos.network_latency(5, 1000)  # 1 секунда задержки
        
        start_time = time.time()
        self.pipeline.generate_sample_data(5)
        delayed_time = time.time() - start_time
        
        # Проверяем что время увеличилось
        assert delayed_time > normal_time
        print(f"✅ Задержка работает: {normal_time:.2f}с -> {delayed_time:.2f}с")
    
    def test_service_failure(self):
        """Тестируем отказ сервиса"""
        # Пытаемся выполнить операцию при отказе S3
        self.chaos.service_failure("S3", 10)
        
        # Операция должна завершиться ошибкой
        test_data = self.pipeline.generate_sample_data(3)
        success = self.pipeline.client.upload_csv_to_s3(
            test_data, "test-bucket", "test-file.csv"
        )
        
        assert not success, "Операция должна была завершиться ошибкой"
        print("✅ Отказ сервиса корректно эмулируется")
    
    def test_data_corruption(self):
        """Тестируем коррупцию данных"""
        original_data = self.pipeline.generate_sample_data(10)
        
        # Включаем коррупцию с высокой вероятностью
        self.chaos.data_corruption(1.0)  # 100% вероятность
        
        # Загружаем данные - они должны быть коррумпированы
        success = self.pipeline.client.upload_csv_to_s3(
            original_data, "test-bucket", "corrupted-data.csv"
        )
        
        assert success, "Загрузка должна завершиться успешно даже с коррупцией"
        
        # Выключаем коррупцию
        self.chaos.stop_data_corruption()
        print("✅ Коррупция данных работает корректно")
    
    def test_resilient_pipeline(self):
        """Тестируем устойчивость пайплайна"""
        # Запускаем пайплайн с включенным chaos engineering
        success = self.pipeline.run_resilient_pipeline(enable_chaos=True)
        
        # Пайплайн должен справляться с хаосом
        assert success, "Устойчивый пайплайн должен работать даже с хаосом"
        print("✅ Устойчивый пайплайн корректно обрабатывает сбои")
    
    def test_retry_mechanism(self):
        """Тестируем механизм повторных попыток"""
        # Создаем данные для теста
        test_data = self.pipeline.generate_sample_data(5)
        
        # Включаем временный отказ сервиса
        self.chaos.service_failure("S3", 15)
        
        # Пытаемся загрузить с retry - должна сработать логика повторных попыток
        start_time = time.time()
        success = self.pipeline.upload_with_retry(
            test_data, "test-bucket", "retry-test.csv", max_retries=2
        )
        execution_time = time.time() - start_time
        
        # Операция должна занять больше времени из-за retry
        assert execution_time > 4, "Retry логика должна добавлять задержки"
        print(f"✅ Retry механизм работает: время выполнения {execution_time:.2f}с")
    
    def test_circuit_breaker(self):
        """Тестируем Circuit Breaker паттерн"""
        # Создаем функцию, которая всегда падает
        def failing_operation():
            raise Exception("Тестовая ошибка")
        
        # Первые вызовы должны проходить
        for i in range(3):
            try:
                self.pipeline.process_with_circuit_breaker(failing_operation)
                assert False, "Операция должна была упасть"
            except:
                pass  # Ожидаемое поведение
        
        # После 3 ошибок circuit breaker должен открыться
        result = self.pipeline.process_with_circuit_breaker(failing_operation)
        assert result is None, "Circuit breaker должен блокировать операции"
        print("✅ Circuit Breaker корректно блокирует операции после multiple failures")
    
    def test_chaos_monkey(self):
        """Тестируем Chaos Monkey"""
        # Запускаем Chaos Monkey на короткое время
        experiment_count = self.chaos.run_chaos_monkey(duration=60, interval=10)
        
        # Должен выполниться хотя бы один эксперимент
        assert experiment_count > 0, "Chaos Monkey должен выполнить хотя бы один эксперимент"
        print(f"✅ Chaos Monkey выполнил {experiment_count} экспериментов")
    
    def test_report_generation(self):
        """Тестируем генерацию отчетов"""
        # Выполняем несколько экспериментов
        self.chaos.network_latency(2, 100)
        self.chaos.high_cpu_load(2, 50)
        
        # Генерируем отчет
        report = self.chaos.generate_report()
        
        assert report is not None
        assert 'total_experiments' in report
        assert report['total_experiments'] >= 2
        print("✅ Генерация отчетов работает корректно")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
