"""
Простой скрипт для обучения модели без проблем с кодировкой
"""
import sys
import io

# Настройка UTF-8 для stdout и stderr
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from ml_pipeline import MLPipeline

if __name__ == "__main__":
    # Создаем и обучаем модель
    pipeline = MLPipeline()

    # Генерируем данные
    data = pipeline.generate_sample_data(1000)

    # Обучаем модель
    X, y = pipeline.preprocess_data(data)
    pipeline.train_model(X, y)

    # Сохраняем модель
    pipeline.save_model()

    # Тестируем предсказание
    test_customer = {
        'customer_id': 'TEST_001',
        'age': 35,
        'tenure': 24,
        'monthly_charges': 75.50,
        'total_charges': 1812.00,
        'contract_type': 'Monthly',
        'payment_method': 'Credit Card',
        'paperless_billing': 1,
        'dependents': 0,
        'partner': 1,
        'online_security': 1,
        'tech_support': 1,
        'monthly_usage_gb': 250,
        'customer_service_calls': 2
    }

    prediction = pipeline.predict(test_customer)
    print(f"\nTesting prediction: {prediction}")
    print("\nModel training completed successfully!")
