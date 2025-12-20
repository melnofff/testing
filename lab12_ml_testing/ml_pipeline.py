import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import LabelEncoder
import joblib
from datetime import datetime
import os

class MLPipeline:
    def __init__(self):
        self.model = None
        self.label_encoders = {}
        self.feature_columns = []
        self.target_column = 'churn'

    def generate_sample_data(self, num_samples=1000):
        """Генерируем тестовые данные для бинарной классификации"""
        print(f"📊 Генерируем {num_samples} тестовых записей...")

        np.random.seed(42)
        data = []

        for i in range(num_samples):
            record = {
                'customer_id': f"CUST_{i:06d}",
                'age': np.random.randint(18, 70),
                'tenure': np.random.randint(1, 60),  # месяцев
                'monthly_charges': round(np.random.uniform(20, 100), 2),
                'total_charges': round(np.random.uniform(50, 5000), 2),
                'contract_type': np.random.choice(['Monthly', 'Yearly', 'Two-Year'], p=[0.4, 0.4, 0.2]),
                'payment_method': np.random.choice(['Credit Card', 'Bank Transfer', 'Electronic Check'], p=[0.3, 0.3, 0.4]),
                'paperless_billing': np.random.choice([0, 1], p=[0.4, 0.6]),
                'dependents': np.random.choice([0, 1], p=[0.7, 0.3]),
                'partner': np.random.choice([0, 1], p=[0.6, 0.4]),
                'online_security': np.random.choice([0, 1], p=[0.5, 0.5]),
                'tech_support': np.random.choice([0, 1], p=[0.5, 0.5]),
                'monthly_usage_gb': np.random.randint(50, 500),
                'customer_service_calls': np.random.randint(0, 10),
                'churn': 0  # Будем вычислять ниже
            }
            data.append(record)

        df = pd.DataFrame(data)

        # Создаем реалистичную целевую переменную
        # Клиенты с большей вероятностью уходят при:
        # - высоких monthly_charges
        # - много звонков в поддержку
        # - месячный контракт
        # - нет online_security и tech_support
        churn_probability = (
            df['monthly_charges'] / 100 * 0.3 +
            df['customer_service_calls'] / 10 * 0.3 +
            (df['contract_type'] == 'Monthly').astype(int) * 0.2 +
            (df['online_security'] == 0).astype(int) * 0.1 +
            (df['tech_support'] == 0).astype(int) * 0.1
        )

        # Добавляем случайность
        churn_probability += np.random.normal(0, 0.1, len(df))

        # Преобразуем в бинарную переменную
        df['churn'] = (churn_probability > 0.5).astype(int)

        print(f"✅ Сгенерировано {len(df)} записей")
        print(f"📈 Распределение целевой переменной:")
        print(df['churn'].value_counts(normalize=True))

        return df

    def preprocess_data(self, df):
        """Предобрабатываем данные для модели"""
        print("🔧 Предобрабатываем данные...")

        # Копируем данные
        processed_df = df.copy()

        # Кодируем категориальные переменные
        categorical_columns = ['contract_type', 'payment_method']

        for col in categorical_columns:
            if col not in self.label_encoders:
                self.label_encoders[col] = LabelEncoder()
                processed_df[col] = self.label_encoders[col].fit_transform(processed_df[col])
            else:
                processed_df[col] = self.label_encoders[col].transform(processed_df[col])

        # Определяем фичи и таргет
        self.feature_columns = [col for col in processed_df.columns
                               if col not in ['customer_id', self.target_column]]

        X = processed_df[self.feature_columns]
        y = processed_df[self.target_column]

        print(f"✅ Данные подготовлены: {len(self.feature_columns)} фичей")

        return X, y

    def train_model(self, X, y, test_size=0.2):
        """Обучаем модель"""
        print("🎯 Обучаем модель...")

        # Разделяем данные
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )

        # Создаем и обучаем модель
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )

        self.model.fit(X_train, y_train)

        # Оцениваем модель
        train_score = self.model.score(X_train, y_train)
        test_score = self.model.score(X_test, y_test)

        print(f"✅ Модель обучена")
        print(f"📊 Точность на обучении: {train_score:.3f}")
        print(f"📊 Точность на тесте: {test_score:.3f}")

        # Детальная оценка
        y_pred = self.model.predict(X_test)
        print("\n📈 Детальный отчет:")
        print(classification_report(y_test, y_pred))

        return X_test, y_test, y_pred

    def save_model(self, path='model'):
        """Сохраняем модель и энкодеры"""
        print("💾 Сохраняем модель...")
        os.makedirs(path, exist_ok=True)

        # Сохраняем модель
        joblib.dump(self.model, f'{path}/model.joblib')

        # Сохраняем энкодеры
        joblib.dump(self.label_encoders, f'{path}/label_encoders.joblib')

        # Сохраняем информацию о фичах
        feature_info = {
            'feature_columns': self.feature_columns,
            'target_column': self.target_column,
            'timestamp': datetime.now().isoformat()
        }
        joblib.dump(feature_info, f'{path}/feature_info.joblib')

        print(f"✅ Модель сохранена в папку {path}")

    def load_model(self, path='model'):
        """Загружаем модель и энкодеры"""
        print("📂 Загружаем модель...")
        try:
            self.model = joblib.load(f'{path}/model.joblib')
            self.label_encoders = joblib.load(f'{path}/label_encoders.joblib')
            feature_info = joblib.load(f'{path}/feature_info.joblib')
            self.feature_columns = feature_info['feature_columns']
            self.target_column = feature_info['target_column']
            print("✅ Модель загружена")
            return True
        except Exception as e:
            print(f"❌ Ошибка загрузки модели: {e}")
            return False

    def predict(self, input_data):
        """Делаем предсказание для новых данных"""
        if self.model is None:
            raise Exception("Модель не загружена")

        # Преобразуем входные данные
        if isinstance(input_data, dict):
            # Одна запись
            input_df = pd.DataFrame([input_data])
        else:
            # Несколько записей
            input_df = pd.DataFrame(input_data)

        # Предобрабатываем данные
        processed_df = input_df.copy()

        for col in self.label_encoders:
            if col in processed_df.columns:
                # Для новых категорий используем наиболее частую категорию
                unknown_categories = ~processed_df[col].isin(self.label_encoders[col].classes_)
                if unknown_categories.any():
                    most_frequent = self.label_encoders[col].classes_[0]
                    processed_df.loc[unknown_categories, col] = most_frequent

                processed_df[col] = self.label_encoders[col].transform(processed_df[col])

        # Убедимся что все фичи присутствуют
        for col in self.feature_columns:
            if col not in processed_df.columns:
                processed_df[col] = 0  # Заполняем нулями отсутствующие фичи

        # Делаем предсказание
        X = processed_df[self.feature_columns]
        predictions = self.model.predict(X)
        probabilities = self.model.predict_proba(X)

        # Формируем результат
        results = []
        for i, (pred, prob) in enumerate(zip(predictions, probabilities)):
            result = {
                'prediction': int(pred),
                'probability': float(prob[1]),  # Вероятность класса 1 (churn)
                'customer_id': input_df.iloc[i]['customer_id'] if 'customer_id' in input_df.columns else f"cust_{i}"
            }
            results.append(result)

        return results

# Пример использования
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
    print(f"\n🎯 Тестовое предсказание: {prediction}")
