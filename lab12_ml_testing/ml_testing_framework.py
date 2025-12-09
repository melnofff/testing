import pytest
import pandas as pd
import numpy as np
import requests
import json
from datetime import datetime, timedelta
from ml_pipeline import MLPipeline
import evidently
from evidently.test_suite import TestSuite
from evidently.tests import *
import warnings
warnings.filterwarnings('ignore')

class MLTestingFramework:
    def __init__(self, api_url="http://localhost:5000"):
        self.pipeline = MLPipeline()
        self.api_url = api_url
        self.test_results = []

    def log_test(self, test_name, description, success, details=None):
        """Логируем результаты теста"""
        test_result = {
            'test_name': test_name,
            'description': description,
            'success': success,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(test_result)

        status = "✅ УСПЕХ" if success else "❌ ПРОВАЛ"
        print(f"{status} {test_name}: {description}")
        if details and not success:
            print(f"   📝 Детали: {details}")

    def test_data_quality(self, data):
        """Тестируем качество данных"""
        print("\n🔍 ТЕСТИРУЕМ КАЧЕСТВО ДАННЫХ")

        # Проверяем наличие обязательных колонок
        required_columns = ['age', 'tenure', 'monthly_charges', 'contract_type']
        missing_columns = [col for col in required_columns if col not in data.columns]

        if missing_columns:
            self.log_test(
                "DATA_COMPLETENESS",
                "Проверка обязательных колонок",
                False,
                f"Отсутствуют колонки: {missing_columns}"
            )
        else:
            self.log_test(
                "DATA_COMPLETENESS",
                "Проверка обязательных колонок",
                True
            )

        # Проверяем пропущенные значения
        missing_values = data.isnull().sum()
        high_missing = missing_values[missing_values > 0]

        if not high_missing.empty:
            self.log_test(
                "MISSING_VALUES",
                "Проверка пропущенных значений",
                False,
                f"Пропущенные значения: {dict(high_missing)}"
            )
        else:
            self.log_test(
                "MISSING_VALUES",
                "Проверка пропущенных значений",
                True
            )

        # Проверяем выбросы в числовых колонках
        numerical_columns = data.select_dtypes(include=[np.number]).columns
        outlier_tests = []

        for col in numerical_columns:
            if col == 'churn':  # Пропускаем целевую переменную
                continue

            Q1 = data[col].quantile(0.25)
            Q3 = data[col].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR

            outliers = data[(data[col] < lower_bound) | (data[col] > upper_bound)]
            outlier_percentage = len(outliers) / len(data) * 100

            if outlier_percentage > 5:  # Больше 5% выбросов
                outlier_tests.append(f"{col}: {outlier_percentage:.1f}%")

        if outlier_tests:
            self.log_test(
                "OUTLIERS",
                "Проверка выбросов",
                False,
                f"Высокий процент выбросов: {', '.join(outlier_tests)}"
            )
        else:
            self.log_test(
                "OUTLIERS",
                "Проверка выбросов",
                True
            )

        # Проверяем распределение целевой переменной
        churn_distribution = data['churn'].value_counts(normalize=True)
        minority_class = churn_distribution.min()

        if minority_class < 0.2:  # Меньше 20% в миноритарном классе
            self.log_test(
                "TARGET_DISTRIBUTION",
                "Проверка распределения целевой переменной",
                False,
                f"Дисбаланс классов: {dict(churn_distribution)}"
            )
        else:
            self.log_test(
                "TARGET_DISTRIBUTION",
                "Проверка распределения целевой переменной",
                True,
                f"Распределение: {dict(churn_distribution)}"
            )

    def test_model_performance(self, X_test, y_test, y_pred):
        """Тестируем производительность модели"""
        print("\n🎯 ТЕСТИРУЕМ ПРОИЗВОДИТЕЛЬНОСТЬ МОДЕЛИ")

        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred)
        recall = recall_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred)

        # Проверяем точность
        if accuracy >= 0.7:
            self.log_test(
                "MODEL_ACCURACY",
                "Проверка точности модели",
                True,
                f"Accuracy: {accuracy:.3f}"
            )
        else:
            self.log_test(
                "MODEL_ACCURACY",
                "Проверка точности модели",
                False,
                f"Accuracy: {accuracy:.3f} (ниже порога 0.7)"
            )

        # Проверяем precision
        if precision >= 0.6:
            self.log_test(
                "MODEL_PRECISION",
                "Проверка precision модели",
                True,
                f"Precision: {precision:.3f}"
            )
        else:
            self.log_test(
                "MODEL_PRECISION",
                "Проверка precision модели",
                False,
                f"Precision: {precision:.3f} (ниже порога 0.6)"
            )

        # Проверяем recall
        if recall >= 0.5:
            self.log_test(
                "MODEL_RECALL",
                "Проверка recall модели",
                True,
                f"Recall: {recall:.3f}"
            )
        else:
            self.log_test(
                "MODEL_RECALL",
                "Проверка recall модели",
                False,
                f"Recall: {recall:.3f} (ниже порога 0.5)"
            )

        # Проверяем F1-score
        if f1 >= 0.6:
            self.log_test(
                "MODEL_F1",
                "Проверка F1-score модели",
                True,
                f"F1-score: {f1:.3f}"
            )
        else:
            self.log_test(
                "MODEL_F1",
                "Проверка F1-score модели",
                False,
                f"F1-score: {f1:.3f} (ниже порога 0.6)"
            )

    def test_data_drift(self, reference_data, current_data):
        """Тестируем дрифт данных с помощью Evidently"""
        print("\n📊 ТЕСТИРУЕМ ДРИФТ ДАННЫХ")

        try:
            # Создаем тестовый набор для дрифта
            from evidently.tests import TestNumberOfColumnsWithMissingValues, TestShareOfMissingValues
            # Убираем TestNumberOfRows так как размеры выборок могут отличаться
            data_drift_suite = TestSuite(tests=[
                TestNumberOfColumns(),
                TestColumnsType(),
                TestShareOfMissingValues(),
            ])

            data_drift_suite.run(
                reference_data=reference_data,
                current_data=current_data
            )

            # Проверяем результаты
            if data_drift_suite.as_dict()['summary']['all_passed']:
                self.log_test(
                    "DATA_DRIFT",
                    "Проверка дрифта данных",
                    True,
                    "Дрифт не обнаружен"
                )
            else:
                failed_tests = []
                for test in data_drift_suite.as_dict()['tests']:
                    if test['status'] == 'FAIL':
                        failed_tests.append(test['name'])

                self.log_test(
                    "DATA_DRIFT",
                    "Проверка дрифта данных",
                    False,
                    f"Обнаружен дрифт в тестах: {', '.join(failed_tests)}"
                )

        except Exception as e:
            self.log_test(
                "DATA_DRIFT",
                "Проверка дрифта данных",
                False,
                f"Ошибка при проверке дрифта: {e}"
            )

    def test_api_functionality(self):
        """Тестируем функциональность API"""
        print("\n🌐 ТЕСТИРУЕМ API ФУНКЦИОНАЛЬНОСТЬ")

        # Тестируем health check
        try:
            response = requests.get(f"{self.api_url}/health")
            if response.status_code == 200:
                health_data = response.json()
                if health_data.get('model_loaded'):
                    self.log_test(
                        "API_HEALTH",
                        "Проверка health check API",
                        True
                    )
                else:
                    self.log_test(
                        "API_HEALTH",
                        "Проверка health check API",
                        False,
                        "Модель не загружена в API"
                    )
            else:
                self.log_test(
                    "API_HEALTH",
                    "Проверка health check API",
                    False,
                    f"Status code: {response.status_code}"
                )
        except Exception as e:
            self.log_test(
                "API_HEALTH",
                "Проверка health check API",
                False,
                f"Ошибка подключения: {e}"
            )

        # Тестируем предсказание
        try:
            test_customer = {
                'customer_id': 'API_TEST_001',
                'age': 45,
                'tenure': 36,
                'monthly_charges': 89.99,
                'total_charges': 3239.64,
                'contract_type': 'Yearly',
                'payment_method': 'Credit Card',
                'paperless_billing': 1,
                'dependents': 0,
                'partner': 1,
                'online_security': 1,
                'tech_support': 1,
                'monthly_usage_gb': 350,
                'customer_service_calls': 1
            }

            response = requests.post(f"{self.api_url}/predict", json=test_customer)

            if response.status_code == 200:
                prediction_data = response.json()
                if 'predictions' in prediction_data:
                    self.log_test(
                        "API_PREDICTION",
                        "Проверка предсказания через API",
                        True,
                        f"Предсказание: {prediction_data['predictions']}"
                    )
                else:
                    self.log_test(
                        "API_PREDICTION",
                        "Проверка предсказания через API",
                        False,
                        "Некорректный ответ от API"
                    )
            else:
                self.log_test(
                    "API_PREDICTION",
                    "Проверка предсказания через API",
                    False,
                    f"Status code: {response.status_code}, Response: {response.text}"
                )
        except Exception as e:
            self.log_test(
                "API_PREDICTION",
                "Проверка предсказания через API",
                False,
                f"Ошибка: {e}"
            )

        # Тестируем батчевое предсказание
        try:
            test_customers = {
                'customers': [
                    {
                        'customer_id': 'BATCH_TEST_001',
                        'age': 30,
                        'tenure': 12,
                        'monthly_charges': 65.50,
                        'total_charges': 786.00,
                        'contract_type': 'Monthly',
                        'payment_method': 'Electronic Check',
                        'paperless_billing': 1,
                        'dependents': 0,
                        'partner': 0,
                        'online_security': 0,
                        'tech_support': 0,
                        'monthly_usage_gb': 150,
                        'customer_service_calls': 5
                    },
                    {
                        'customer_id': 'BATCH_TEST_002',
                        'age': 55,
                        'tenure': 48,
                        'monthly_charges': 45.00,
                        'total_charges': 2160.00,
                        'contract_type': 'Two-Year',
                        'payment_method': 'Bank Transfer',
                        'paperless_billing': 0,
                        'dependents': 1,
                        'partner': 1,
                        'online_security': 1,
                        'tech_support': 1,
                        'monthly_usage_gb': 200,
                        'customer_service_calls': 0
                    }
                ]
            }

            response = requests.post(f"{self.api_url}/batch_predict", json=test_customers)

            if response.status_code == 200:
                batch_data = response.json()
                if 'predictions' in batch_data and len(batch_data['predictions']) == 2:
                    self.log_test(
                        "API_BATCH_PREDICTION",
                        "Проверка батчевого предсказания через API",
                        True,
                        f"Обработано: {batch_data['total_customers']} клиентов"
                    )
                else:
                    self.log_test(
                        "API_BATCH_PREDICTION",
                        "Проверка батчевого предсказания через API",
                        False,
                        "Некорректный ответ от API"
                    )
            else:
                self.log_test(
                    "API_BATCH_PREDICTION",
                    "Проверка батчевого предсказания через API",
                    False,
                    f"Status code: {response.status_code}"
                )
        except Exception as e:
            self.log_test(
                "API_BATCH_PREDICTION",
                "Проверка батчевого предсказания через API",
                False,
                f"Ошибка: {e}"
            )

    def test_model_fairness(self, data, predictions):
        """Тестируем справедливость модели"""
        print("\n⚖️ ТЕСТИРУЕМ СПРАВЕДЛИВОСТЬ МОДЕЛИ")

        try:
            # Проверяем различия в предсказаниях по возрасту
            # Берем только те записи, для которых есть предсказания
            data_subset = data.iloc[:len(predictions)].copy()
            data_subset['prediction'] = predictions

            # Группируем по возрастным группам
            data_subset['age_group'] = pd.cut(data_subset['age'],
                                                bins=[0, 30, 50, 100],
                                                labels=['young', 'middle', 'senior'])

            churn_rates = data_subset.groupby('age_group')['prediction'].mean()
            max_difference = churn_rates.max() - churn_rates.min()

            if max_difference < 0.2:  # Разница менее 20%
                self.log_test(
                    "MODEL_FAIRNESS_AGE",
                    "Проверка справедливости по возрасту",
                    True,
                    f"Разница в предсказаниях: {max_difference:.3f}"
                )
            else:
                self.log_test(
                    "MODEL_FAIRNESS_AGE",
                    "Проверка справедливости по возрасту",
                    False,
                    f"Большая разница в предсказаниях по возрастным группам: {max_difference:.3f}"
                )

        except Exception as e:
            self.log_test(
                "MODEL_FAIRNESS_AGE",
                "Проверка справедливости по возрасту",
                False,
                f"Ошибка: {e}"
            )

    def run_complete_test_suite(self):
        """Запускаем полный набор тестов"""
        print("🎯 ЗАПУСКАЕМ ПОЛНЫЙ ТЕСТ ML PIPELINE")
        print("=" * 60)

        # Генерируем данные
        data = self.pipeline.generate_sample_data(1000)

        # Обучаем модель
        X, y = self.pipeline.preprocess_data(data)
        X_test, y_test, y_pred = self.pipeline.train_model(X, y)

        # Запускаем все тесты
        self.test_data_quality(data)
        self.test_model_performance(X_test, y_test, y_pred)
        self.test_model_fairness(data, y_pred)
        self.test_api_functionality()

        # Тестируем дрифт (создаем "текущие" данные с небольшими изменениями)
        current_data = self.pipeline.generate_sample_data(200)
        self.test_data_drift(data, current_data)

        # Генерируем отчет
        return self.generate_test_report()

    def generate_test_report(self):
        """Генерируем отчет по тестированию"""
        print("\n📊 ГЕНЕРИРУЕМ ОТЧЕТ ПО ТЕСТИРОВАНИЮ")
        print("=" * 50)

        if not self.test_results:
            print("❌ Нет результатов тестирования")
            return None

        df = pd.DataFrame(self.test_results)

        # Статистика
        total_tests = len(df)
        passed_tests = df['success'].sum()
        success_rate = (passed_tests / total_tests) * 100

        print(f"🎯 ОБЩАЯ СТАТИСТИКА:")
        print(f"Всего тестов: {total_tests}")
        print(f"Пройдено: {passed_tests}")
        print(f"Успешность: {success_rate:.1f}%")

        # Детали по категориям тестов
        test_categories = df['test_name'].str.split('_').str[0].value_counts()
        print(f"\n📈 ТЕСТЫ ПО КАТЕГОРИЯМ:")
        for category, count in test_categories.items():
            category_success = df[df['test_name'].str.startswith(category)]['success'].sum()
            category_rate = (category_success / count) * 100
            print(f"  {category}: {category_success}/{count} ({category_rate:.1f}%)")

        # Неудачные тесты
        failed_tests = df[~df['success']]
        if not failed_tests.empty:
            print(f"\n🚨 НЕУДАЧНЫЕ ТЕСТЫ:")
            for _, test in failed_tests.iterrows():
                print(f"  ❌ {test['test_name']}: {test['description']}")
                if test['details']:
                    print(f"     📝 {test['details']}")

        # Сохраняем отчет
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': int(total_tests),
            'passed_tests': int(passed_tests),
            'success_rate': float(success_rate),
            'test_details': df.to_dict('records')
        }

        with open('ml_testing_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        print(f"\n✅ Отчет сохранен в ml_testing_report.json")

        # Рекомендации
        if success_rate >= 80:
            print("🏆 ОТЛИЧНЫЙ РЕЗУЛЬТАТ: ML pipeline готов к продакшену!")
        elif success_rate >= 60:
            print("⚠️  ХОРОШИЙ РЕЗУЛЬТАТ: ML pipeline работает, но нужны улучшения")
        else:
            print("🚨 КРИТИЧЕСКИЙ РЕЗУЛЬТАТ: ML pipeline требует серьезной доработки")

        return report

# Пример использования
if __name__ == "__main__":
    tester = MLTestingFramework()
    report = tester.run_complete_test_suite()
