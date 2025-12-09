import pytest
import pandas as pd
import numpy as np
from ml_pipeline import MLPipeline
from ml_testing_framework import MLTestingFramework
import os

class TestMLPipeline:
    def setup_method(self):
        """Подготовка перед каждым тестом"""
        self.pipeline = MLPipeline()
        self.tester = MLTestingFramework()
        self.data = self.pipeline.generate_sample_data(500)

    def test_data_generation(self):
        """Тестируем генерацию данных"""
        assert self.data is not None
        assert len(self.data) == 500
        assert 'churn' in self.data.columns
        assert self.data['churn'].dtype == int

        # Проверяем что данные реалистичны
        assert self.data['age'].min() >= 18
        assert self.data['monthly_charges'].min() >= 20
        assert set(self.data['contract_type'].unique()) == {'Monthly', 'Yearly', 'Two-Year'}

    def test_data_preprocessing(self):
        """Тестируем предобработку данных"""
        X, y = self.pipeline.preprocess_data(self.data)

        assert X is not None
        assert y is not None
        assert len(X) == len(y)
        assert len(self.pipeline.feature_columns) > 0

        # Проверяем что категориальные переменные закодированы (остаются в X, но с числовыми значениями)
        assert 'contract_type' in X.columns
        assert 'payment_method' in X.columns
        # Проверяем что значения числовые
        assert X['contract_type'].dtype in [np.int32, np.int64]
        assert X['payment_method'].dtype in [np.int32, np.int64]

    def test_model_training(self):
        """Тестируем обучение модели"""
        X, y = self.pipeline.preprocess_data(self.data)
        X_test, y_test, y_pred = self.pipeline.train_model(X, y)

        assert self.pipeline.model is not None
        assert len(y_pred) == len(y_test)

        # Проверяем что точность разумная
        accuracy = (y_pred == y_test).mean()
        assert accuracy > 0.5  # Должна быть лучше случайного угадывания

    def test_model_saving_loading(self):
        """Тестируем сохранение и загрузку модели"""
        X, y = self.pipeline.preprocess_data(self.data)
        self.pipeline.train_model(X, y)

        # Сохраняем модель
        self.pipeline.save_model('test_model')
        assert os.path.exists('test_model/model.joblib')
        assert os.path.exists('test_model/label_encoders.joblib')

        # Создаем новый pipeline и загружаем модель
        new_pipeline = MLPipeline()
        success = new_pipeline.load_model('test_model')

        assert success
        assert new_pipeline.model is not None
        assert len(new_pipeline.feature_columns) > 0

    def test_predictions(self):
        """Тестируем предсказания модели"""
        X, y = self.pipeline.preprocess_data(self.data)
        self.pipeline.train_model(X, y)

        # Тестовый клиент
        test_customer = {
            'customer_id': 'TEST_001',
            'age': 40,
            'tenure': 24,
            'monthly_charges': 75.0,
            'total_charges': 1800.0,
            'contract_type': 'Monthly',
            'payment_method': 'Credit Card',
            'paperless_billing': 1,
            'dependents': 0,
            'partner': 1,
            'online_security': 1,
            'tech_support': 1,
            'monthly_usage_gb': 300,
            'customer_service_calls': 2
        }

        predictions = self.pipeline.predict(test_customer)

        assert len(predictions) == 1
        assert 'prediction' in predictions[0]
        assert 'probability' in predictions[0]
        assert 0 <= predictions[0]['probability'] <= 1

    def test_batch_predictions(self):
        """Тестируем батчевые предсказания"""
        X, y = self.pipeline.preprocess_data(self.data)
        self.pipeline.train_model(X, y)

        test_customers = [
            {
                'customer_id': 'BATCH_001',
                'age': 35,
                'tenure': 12,
                'monthly_charges': 65.0,
                'total_charges': 780.0,
                'contract_type': 'Monthly',
                'payment_method': 'Electronic Check',
                'paperless_billing': 1,
                'dependents': 0,
                'partner': 0,
                'online_security': 0,
                'tech_support': 0,
                'monthly_usage_gb': 200,
                'customer_service_calls': 5
            },
            {
                'customer_id': 'BATCH_002',
                'age': 50,
                'tenure': 48,
                'monthly_charges': 45.0,
                'total_charges': 2160.0,
                'contract_type': 'Two-Year',
                'payment_method': 'Bank Transfer',
                'paperless_billing': 0,
                'dependents': 1,
                'partner': 1,
                'online_security': 1,
                'tech_support': 1,
                'monthly_usage_gb': 150,
                'customer_service_calls': 0
            }
        ]

        predictions = self.pipeline.predict(test_customers)

        assert len(predictions) == 2
        for pred in predictions:
            assert 'prediction' in pred
            assert 'probability' in pred

    def test_data_quality_checks(self):
        """Тестируем проверки качества данных"""
        self.tester.test_data_quality(self.data)

        # Проверяем что тесты были выполнены
        assert len(self.tester.test_results) > 0

        # Должен быть хотя бы один успешный тест
        successful_tests = [t for t in self.tester.test_results if t['success']]
        assert len(successful_tests) > 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
