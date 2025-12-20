import time
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from ml_pipeline import MLPipeline
from ml_testing_framework import MLTestingFramework
import matplotlib.pyplot as plt
import json
import os

class MLMonitoring:
    def __init__(self):
        self.pipeline = MLPipeline()
        self.tester = MLTestingFramework()
        self.monitoring_data = []
        self.alert_threshold = 0.7  # Порог для алертов

    def collect_monitoring_data(self, days=7, interval_hours=6):
        """Собираем данные мониторинга"""
        print(f"📊 Собираем данные мониторинга за {days} дней...")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        current_date = start_date
        iteration = 0

        while current_date <= end_date:
            iteration += 1
            print(f"\n📅 Итерация {iteration}: {current_date.strftime('%Y-%m-%d %H:%M')}")

            # Генерируем "текущие" данные (в реальности брали бы из продакшена)
            current_data = self.pipeline.generate_sample_data(200)

            # Если у нас уже есть модель, тестируем на новых данных
            if self.pipeline.model is not None:
                # Предсказываем на новых данных
                X_current, y_current = self.pipeline.preprocess_data(current_data)
                current_predictions = self.pipeline.model.predict(X_current)

                # Считаем метрики
                from sklearn.metrics import accuracy_score
                current_accuracy = accuracy_score(y_current, current_predictions)

                # Собираем мониторинговые данные
                monitoring_point = {
                    'timestamp': current_date.isoformat(),
                    'data_size': len(current_data),
                    'accuracy': current_accuracy,
                    'churn_rate': current_data['churn'].mean(),
                    'feature_drift': self.calculate_feature_drift(current_data),
                    'alerts': []
                }

                # Проверяем алерты
                if current_accuracy < self.alert_threshold:
                    monitoring_point['alerts'].append(f"Низкая точность: {current_accuracy:.3f}")

                if monitoring_point['feature_drift'] > 0.1:
                    monitoring_point['alerts'].append(f"Высокий дрифт фич: {monitoring_point['feature_drift']:.3f}")

                self.monitoring_data.append(monitoring_point)

                print(f"   📈 Accuracy: {current_accuracy:.3f}")
                print(f"   📊 Churn rate: {monitoring_point['churn_rate']:.3f}")
                print(f"   📉 Feature drift: {monitoring_point['feature_drift']:.3f}")

                if monitoring_point['alerts']:
                    print(f"   🚨 Alerts: {', '.join(monitoring_point['alerts'])}")

            # "Перемещаемся" вперед во времени
            current_date += timedelta(hours=interval_hours)

        print(f"\n✅ Собрано {len(self.monitoring_data)} точек мониторинга")
        return self.monitoring_data

    def calculate_feature_drift(self, current_data, reference_data=None):
        """Рассчитываем дрифт фичей"""
        if reference_data is None:
            # Используем сгенерированные данные как референс
            reference_data = self.pipeline.generate_sample_data(500)

        # Сравниваем распределения ключевых фичей
        drift_score = 0
        key_features = ['age', 'monthly_charges', 'tenure']

        for feature in key_features:
            # KS test для числовых фичей
            from scipy.stats import ks_2samp
            stat, _ = ks_2samp(reference_data[feature], current_data[feature])
            drift_score += stat

        return drift_score / len(key_features)

    def create_monitoring_dashboard(self):
        """Создаем дашборд мониторинга"""
        if not self.monitoring_data:
            print("❌ Нет данных для дашборда")
            return

        df = pd.DataFrame(self.monitoring_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        print("\n📊 СОЗДАЕМ ДАШБОРД МОНИТОРИНГА")

        # Создаем графики
        plt.figure(figsize=(15, 10))

        # 1. Точность модели во времени
        plt.subplot(2, 2, 1)
        plt.plot(df['timestamp'], df['accuracy'], marker='o', linewidth=2)
        plt.axhline(y=self.alert_threshold, color='red', linestyle='--', label='Порог алерта')
        plt.title('Точность модели во времени')
        plt.xlabel('Время')
        plt.ylabel('Accuracy')
        plt.legend()
        plt.grid(True)
        plt.xticks(rotation=45)

        # 2. Дрифт фичей во времени
        plt.subplot(2, 2, 2)
        plt.plot(df['timestamp'], df['feature_drift'], marker='s', color='orange', linewidth=2)
        plt.axhline(y=0.1, color='red', linestyle='--', label='Порог дрифта')
        plt.title('Дрифт фичей во времени')
        plt.xlabel('Время')
        plt.ylabel('Feature Drift Score')
        plt.legend()
        plt.grid(True)
        plt.xticks(rotation=45)

        # 3. Распределение churn rate
        plt.subplot(2, 2, 3)
        plt.hist(df['churn_rate'], bins=10, alpha=0.7, color='green')
        plt.title('Распределение Churn Rate')
        plt.xlabel('Churn Rate')
        plt.ylabel('Частота')
        plt.grid(True)

        # 4. Количество алертов по времени
        plt.subplot(2, 2, 4)
        alert_counts = df['alerts'].apply(len)
        plt.bar(df['timestamp'], alert_counts, color='red', alpha=0.7)
        plt.title('Количество алертов по времени')
        plt.xlabel('Время')
        plt.ylabel('Количество алертов')
        plt.grid(True)
        plt.xticks(rotation=45)

        plt.tight_layout()
        plt.savefig('ml_monitoring_dashboard.png', dpi=300, bbox_inches='tight')
        plt.close()

        print("✅ Дашборд сохранен в ml_monitoring_dashboard.png")

    def generate_monitoring_report(self):
        """Генерируем отчет мониторинга"""
        if not self.monitoring_data:
            print("❌ Нет данных для отчета")
            return None

        df = pd.DataFrame(self.monitoring_data)

        # Статистика
        total_alerts = df['alerts'].apply(len).sum()
        avg_accuracy = df['accuracy'].mean()
        max_drift = df['feature_drift'].max()

        print("\n📈 ОТЧЕТ МОНИТОРИНГА ML PIPELINE")
        print("=" * 50)
        print(f"📅 Период мониторинга: {len(df)} точек")
        print(f"🎯 Средняя точность: {avg_accuracy:.3f}")
        print(f"📉 Максимальный дрифт: {max_drift:.3f}")
        print(f"🚨 Всего алертов: {total_alerts}")

        # Детали алертов
        if total_alerts > 0:
            print(f"\n🔍 ДЕТАЛИ АЛЕРТОВ:")
            all_alerts = []
            for alerts in df['alerts']:
                all_alerts.extend(alerts)
            alert_counts = pd.Series(all_alerts).value_counts()
            for alert, count in alert_counts.items():
                print(f"  • {alert}: {count} раз")

        # Сохраняем отчет
        report = {
            'timestamp': datetime.now().isoformat(),
            'monitoring_period': int(len(df)),
            'average_accuracy': float(avg_accuracy),
            'max_feature_drift': float(max_drift),
            'total_alerts': int(total_alerts),
            'stability_score': float(self.calculate_stability_score(df)),
            'monitoring_data': df.to_dict('records')
        }

        with open('ml_monitoring_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        print(f"\n✅ Отчет сохранен в ml_monitoring_report.json")

        # Оценка стабильности
        stability = report['stability_score']
        if stability >= 0.8:
            print("🏆 ВЫСОКАЯ СТАБИЛЬНОСТЬ: ML pipeline работает стабильно")
        elif stability >= 0.6:
            print("⚠️  СРЕДНЯЯ СТАБИЛЬНОСТЬ: ML pipeline требует наблюдения")
        else:
            print("🚨 НИЗКАЯ СТАБИЛЬНОСТЬ: ML pipeline нестабилен, нужны действия")

        return report

    def calculate_stability_score(self, df):
        """Рассчитываем оценку стабильности pipeline"""
        # Основано на точности, дрифте и количестве алертов
        accuracy_score = df['accuracy'].mean()
        drift_penalty = min(df['feature_drift'].max() * 2, 0.3)  # Штраф за дрифт
        alert_penalty = min(len(df[df['alerts'].apply(len) > 0]) / len(df), 0.3)  # Штраф за алерты

        stability = accuracy_score - drift_penalty - alert_penalty
        return max(stability, 0)  # Не ниже 0

# Пример использования
if __name__ == "__main__":
    monitor = MLMonitoring()

    print("🎯 ЗАПУСКАЕМ МОНИТОРИНГ ML PIPELINE")
    print("=" * 50)

    # Сначала обучаем модель
    pipeline = MLPipeline()
    data = pipeline.generate_sample_data(1000)
    X, y = pipeline.preprocess_data(data)
    pipeline.train_model(X, y)
    pipeline.save_model()

    # Загружаем модель в мониторинг
    monitor.pipeline.load_model()

    # Собираем данные мониторинга
    monitoring_data = monitor.collect_monitoring_data(days=3, interval_hours=4)

    # Создаем дашборд и отчет
    monitor.create_monitoring_dashboard()
    report = monitor.generate_monitoring_report()
