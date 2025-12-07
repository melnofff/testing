import pytest
import pandas as pd
import sqlite3
from data_quality_framework import DataQualityFramework
import os

class TestDataQualityFramework:
    def setup_method(self):
        """Подготовка перед каждым тестом"""
        self.dq = DataQualityFramework('employees.db')
        self.dq.load_data()
    
    def test_data_loading(self):
        """Тестируем загрузку данных"""
        data = self.dq.load_data()
        assert data is not None
        assert len(data) > 0
        assert 'id' in data.columns
        assert 'name' in data.columns
    
    def test_completeness_check(self):
        """Тестируем проверку полноты"""
        completeness = self.dq.check_completeness()
        assert completeness is not None
        
        # Проверяем что все основные колонки есть в отчете
        expected_columns = ['id', 'name', 'age', 'salary', 'department']
        for col in expected_columns:
            assert col in completeness
        
        # Проверяем что проценты в разумных пределах
        for metrics in completeness.values():
            assert 0 <= metrics['completeness_percent'] <= 100
    
    def test_accuracy_check(self):
        """Тестируем проверку точности"""
        accuracy = self.dq.check_accuracy()
        assert accuracy is not None
        assert 'age' in accuracy
        assert 'salary' in accuracy
        assert 'department' in accuracy
        
        # Проверяем что проценты точности в разумных пределах
        for metrics in accuracy.values():
            assert 0 <= metrics['accuracy_percent'] <= 100
    
    def test_consistency_check(self):
        """Тестируем проверку консистентности"""
        consistency = self.dq.check_consistency()
        assert consistency is not None
        assert 'experience' in consistency
        assert 'salary_categories' in consistency
    
    def test_drift_detection(self):
        """Тестируем обнаружение дрифта"""
        drift = self.dq.detect_data_drift()
        assert drift is not None
        assert 'age' in drift
        assert 'salary' in drift
        assert 'department_distribution' in drift
    
    def test_report_generation(self):
        """Тестируем генерацию отчета"""
        report = self.dq.generate_report()
        
        assert report is not None
        assert 'overall_score' in report
        assert 'total_checks' in report
        assert 'passed_checks' in report
        assert 'alerts' in report
        assert 'metrics' in report
        
        # Проверяем что общий счет в разумных пределах
        assert 0 <= report['overall_score'] <= 100
    
    def test_visualizations_creation(self):
        """Тестируем создание визуализаций"""
        self.dq.generate_report()
        self.dq.create_visualizations()
        
        # Проверяем что файлы созданы
        assert os.path.exists('static/completeness.png')
        assert os.path.exists('static/age_distribution.png')
        assert os.path.exists('static/salary_by_department.png')

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
