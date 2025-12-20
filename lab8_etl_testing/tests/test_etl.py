import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))


import pytest
import pandas as pd
import sqlite3
from etl_pipeline import ETLPipeline

class TestETLPipeline:
    def setup_method(self):
        self.pipeline = ETLPipeline()
        self.test_file = 'data/raw_data.csv'

    def test_extract(self):
        data = self.pipeline.extract(self.test_file)
        assert data is not None
        assert len(data) > 0
        expected_columns = ['id', 'name', 'age', 'salary', 'department', 'join_date']
        assert list(data.columns) == expected_columns

    def test_transform(self):
        self.pipeline.extract(self.test_file)
        transformed_data = self.pipeline.transform()
        assert 'experience_years' in transformed_data.columns
        assert 'salary_category' in transformed_data.columns
        names = transformed_data['name'].tolist()
        for name in names:
            assert name == name.strip()
        salary_categories = set(transformed_data['salary_category'].unique())
        expected_categories = {'Низкая', 'Средняя', 'Высокая'}
        assert salary_categories.issubset(expected_categories)

    def test_load(self, tmp_path):
        db_path = tmp_path / 'test_employees.db'
        self.pipeline.extract(self.test_file)
        self.pipeline.transform()
        self.pipeline.load(str(db_path))
        conn = sqlite3.connect(str(db_path))
        db_data = pd.read_sql('SELECT * FROM employees', conn)
        conn.close()
        assert len(db_data) > 0
        assert 'experience_years' in db_data.columns
