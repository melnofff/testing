import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import os

class DataQualityFramework:
    def __init__(self, db_path='employees.db'):
        self.db_path = db_path
        self.metrics = {}
        self.alerts = []
        
    def load_data(self):
        """Загружаем данные из базы"""
        conn = sqlite3.connect(self.db_path)
        self.data = pd.read_sql('SELECT * FROM employees', conn)
        conn.close()
        return self.data
    
    def check_completeness(self):
        """Проверяем полноту данных"""
        print("🔍 Проверяем полноту данных...")
        
        completeness_metrics = {}
        total_rows = len(self.data)
        
        for column in self.data.columns:
            # Процент заполненных значений
            non_null_count = self.data[column].notna().sum()
            completeness_percent = (non_null_count / total_rows) * 100
            
            completeness_metrics[column] = {
                'completeness_percent': completeness_percent,
                'missing_count': total_rows - non_null_count,
                'status': 'PASS' if completeness_percent >= 95 else 'FAIL'
            }
            
            # Создаем алерт если много пропущенных значений
            if completeness_percent < 95:
                self.alerts.append(f"❌ В колонке {column} только {completeness_percent:.1f}% данных")
        
        self.metrics['completeness'] = completeness_metrics
        return completeness_metrics
    
    def check_accuracy(self):
        """Проверяем точность данных"""
        print("🎯 Проверяем точность данных...")
        
        accuracy_metrics = {}
        
        # Проверяем возраст (должен быть от 18 до 70)
        valid_age_count = self.data['age'].between(18, 70).sum()
        age_accuracy = (valid_age_count / len(self.data)) * 100
        accuracy_metrics['age'] = {
            'accuracy_percent': age_accuracy,
            'invalid_count': len(self.data) - valid_age_count,
            'status': 'PASS' if age_accuracy >= 98 else 'FAIL'
        }
        
        # Проверяем зарплату (должна быть положительной)
        valid_salary_count = (self.data['salary'] > 0).sum()
        salary_accuracy = (valid_salary_count / len(self.data)) * 100
        accuracy_metrics['salary'] = {
            'accuracy_percent': salary_accuracy,
            'invalid_count': len(self.data) - valid_salary_count,
            'status': 'PASS' if salary_accuracy >= 98 else 'FAIL'
        }
        
        # Проверяем департаменты (должны быть из списка)
        valid_departments = ['IT', 'HR', 'Finance']
        valid_dept_count = self.data['department'].isin(valid_departments).sum()
        dept_accuracy = (valid_dept_count / len(self.data)) * 100
        accuracy_metrics['department'] = {
            'accuracy_percent': dept_accuracy,
            'invalid_count': len(self.data) - valid_dept_count,
            'status': 'PASS' if dept_accuracy >= 98 else 'FAIL'
        }
        
        # Добавляем алерты
        for field, metrics in accuracy_metrics.items():
            if metrics['status'] == 'FAIL':
                self.alerts.append(f"❌ В поле {field} {100 - metrics['accuracy_percent']:.1f}% некорректных данных")
        
        self.metrics['accuracy'] = accuracy_metrics
        return accuracy_metrics
    
    def check_consistency(self):
        """Проверяем консистентность данных"""
        print("🔄 Проверяем консистентность данных...")
        
        consistency_metrics = {}
        
        # Проверяем что опыт работы не отрицательный
        negative_experience = (self.data['experience_years'] < 0).sum()
        consistency_metrics['experience'] = {
            'negative_count': negative_experience,
            'status': 'PASS' if negative_experience == 0 else 'FAIL'
        }
        
        # Проверяем консистентность категорий зарплат
        salary_consistency_errors = 0
        for _, row in self.data.iterrows():
            salary = row['salary']
            category = row['salary_category']
            
            # Проверяем что категория соответствует зарплате
            if salary < 50000 and category != 'Низкая':
                salary_consistency_errors += 1
            elif 50000 <= salary < 60000 and category != 'Средняя':
                salary_consistency_errors += 1
            elif salary >= 60000 and category != 'Высокая':
                salary_consistency_errors += 1
        
        consistency_metrics['salary_categories'] = {
            'inconsistency_count': salary_consistency_errors,
            'status': 'PASS' if salary_consistency_errors == 0 else 'FAIL'
        }
        
        # Добавляем алерты
        if negative_experience > 0:
            self.alerts.append(f"❌ Найдено {negative_experience} записей с отрицательным опытом работы")
        
        if salary_consistency_errors > 0:
            self.alerts.append(f"❌ Найдено {salary_consistency_errors} неконсистентных категорий зарплат")
        
        self.metrics['consistency'] = consistency_metrics
        return consistency_metrics
    
    def detect_data_drift(self, reference_data=None):
        """Обнаруживаем дрифт данных (изменение распределения)"""
        print("📊 Проверяем дрифт данных...")
        
        drift_metrics = {}
        
        if reference_data is None:
            # Используем текущие данные как референс (для демо)
            reference_data = self.data
        
        # Проверяем дрифт в возрасте
        current_age_mean = self.data['age'].mean()
        reference_age_mean = reference_data['age'].mean()
        age_drift = abs(current_age_mean - reference_age_mean)
        
        drift_metrics['age'] = {
            'current_mean': current_age_mean,
            'reference_mean': reference_age_mean,
            'drift_amount': age_drift,
            'status': 'PASS' if age_drift < 5 else 'FAIL'  # Дрифт меньше 5 лет
        }
        
        # Проверяем дрифт в зарплате
        current_salary_mean = self.data['salary'].mean()
        reference_salary_mean = reference_data['salary'].mean()
        salary_drift = abs(current_salary_mean - reference_salary_mean)
        
        drift_metrics['salary'] = {
            'current_mean': current_salary_mean,
            'reference_mean': reference_salary_mean,
            'drift_amount': salary_drift,
            'status': 'PASS' if salary_drift < 10000 else 'FAIL'  # Дрифт меньше 10000
        }
        
        # Проверяем дрифт в распределении департаментов
        current_dept_dist = self.data['department'].value_counts(normalize=True)
        reference_dept_dist = reference_data['department'].value_counts(normalize=True)
        
        # Объединяем все возможные департаменты
        all_departments = set(current_dept_dist.index) | set(reference_dept_dist.index)
        dept_drift = 0
        
        for dept in all_departments:
            current_pct = current_dept_dist.get(dept, 0)
            reference_pct = reference_dept_dist.get(dept, 0)
            dept_drift += abs(current_pct - reference_pct)
        
        drift_metrics['department_distribution'] = {
            'drift_amount': dept_drift,
            'status': 'PASS' if dept_drift < 0.3 else 'FAIL'  # Суммарный дрифт меньше 30%
        }
        
        # Добавляем алерты
        for field, metrics in drift_metrics.items():
            if metrics['status'] == 'FAIL':
                self.alerts.append(f"📈 Обнаружен дрифт в {field}: {metrics['drift_amount']:.2f}")
        
        self.metrics['drift'] = drift_metrics
        return drift_metrics
    
    def generate_report(self):
        """Генерируем отчет о качестве данных"""
        print("📄 Генерируем отчет...")
        
        # Загружаем данные если еще не загружены
        if not hasattr(self, 'data'):
            self.load_data()
        
        # Запускаем все проверки
        self.check_completeness()
        self.check_accuracy()
        self.check_consistency()
        self.detect_data_drift()
        
        # Создаем сводный отчет
        total_checks = 0
        passed_checks = 0
        
        for category, metrics in self.metrics.items():
            for field, field_metrics in metrics.items():
                total_checks += 1
                if field_metrics.get('status') == 'PASS':
                    passed_checks += 1
        
        overall_score = (passed_checks / total_checks) * 100 if total_checks > 0 else 0
        
        report = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'overall_score': overall_score,
            'total_checks': total_checks,
            'passed_checks': passed_checks,
            'failed_checks': total_checks - passed_checks,
            'alerts': self.alerts,
            'metrics': self.metrics
        }
        
        print(f"🎯 Общий результат: {overall_score:.1f}% ({passed_checks}/{total_checks})")
        
        if self.alerts:
            print("🚨 Аллерты:")
            for alert in self.alerts:
                print(f"   {alert}")
        
        return report
    
    def create_visualizations(self):
        """Создаем визуализации для отчета"""
        print("📊 Создаем визуализации...")
        
        # Создаем папку для графиков если ее нет
        os.makedirs('static', exist_ok=True)
        
        # 1. График полноты данных
        completeness_data = []
        for column, metrics in self.metrics['completeness'].items():
            completeness_data.append({
                'column': column,
                'completeness': metrics['completeness_percent']
            })
        
        comp_df = pd.DataFrame(completeness_data)
        plt.figure(figsize=(10, 6))
        plt.bar(comp_df['column'], comp_df['completeness'])
        plt.title('Полнота данных по колонкам')
        plt.xticks(rotation=45)
        plt.ylabel('Процент заполнения')
        plt.ylim(0, 100)
        plt.tight_layout()
        plt.savefig('static/completeness.png')
        plt.close()
        
        # 2. График распределения возрастов
        plt.figure(figsize=(10, 6))
        plt.hist(self.data['age'], bins=10, alpha=0.7, color='skyblue')
        plt.title('Распределение возраста сотрудников')
        plt.xlabel('Возраст')
        plt.ylabel('Количество')
        plt.tight_layout()
        plt.savefig('static/age_distribution.png')
        plt.close()
        
        # 3. График распределения зарплат по департаментам
        plt.figure(figsize=(10, 6))
        department_groups = self.data.groupby('department')
        departments = []
        avg_salaries = []
        
        for dept, group in department_groups:
            departments.append(dept)
            avg_salaries.append(group['salary'].mean())
        
        plt.bar(departments, avg_salaries, color=['red', 'blue', 'green'])
        plt.title('Средняя зарплата по департаментам')
        plt.xlabel('Департамент')
        plt.ylabel('Средняя зарплата')
        plt.tight_layout()
        plt.savefig('static/salary_by_department.png')
        plt.close()
        
        print("✅ Визуализации сохранены в папку static/")

# Пример использования
if __name__ == "__main__":
    # Создаем и запускаем фреймворк
    dq = DataQualityFramework()
    report = dq.generate_report()
    dq.create_visualizations()
    
    print("\n🎉 Data Quality Framework успешно запущен!")
    print(f"📊 Общий показатель качества: {report['overall_score']:.1f}%")
