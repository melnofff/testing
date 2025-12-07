import pandas as pd
import sqlite3
from datetime import datetime

class ETLPipeline:
    def __init__(self):
        self.raw_data = None
        self.transformed_data = None

    def extract(self, file_path):
        """Извлекаем данные из CSV файла"""
        print("🔍 Извлекаем данные...")
        self.raw_data = pd.read_csv(file_path)
        return self.raw_data

    def transform(self):
        """Преобразуем данные"""
        print("🔄 Преобразуем данные...")
        if self.raw_data is None:
            raise ValueError('Нет данных для преобразования. Вызовите extract первым.')

        self.transformed_data = self.raw_data.copy()

        # 1. Добавляем поле опыта (используем 2024 как базовый год)
        self.transformed_data['experience_years'] = 2024 - pd.to_datetime(
            self.transformed_data['join_date']
        ).dt.year

        # 2. Категория зарплаты
        def salary_category(salary):
            if salary < 50000:
                return 'Низкая'
            elif salary < 60000:
                return 'Средняя'
            else:
                return 'Высокая'

        self.transformed_data['salary_category'] = self.transformed_data['salary'].apply(salary_category)

        # 3. Очистка имён от лишних пробелов
        self.transformed_data['name'] = self.transformed_data['name'].str.strip()

        print(f"✅ Преобразовано {len(self.transformed_data)} записей")
        return self.transformed_data

    def load(self, db_path='employees.db'):
        """Загружаем данные в базу SQLite"""
        print("💾 Загружаем данные в базу...")
        if self.transformed_data is None:
            raise ValueError('Нет преобразованных данных для загрузки. Вызовите transform первым.')

        conn = sqlite3.connect(db_path)
        self.transformed_data.to_sql('employees', conn, if_exists='replace', index=False)
        conn.close()
        print("✅ Данные успешно загружены!")

    def run_pipeline(self, input_file):
        self.extract(input_file)
        self.transform()
        self.load()
        return self.transformed_data

if __name__ == "__main__":
    pipeline = ETLPipeline()
    pipeline.run_pipeline('data/raw_data.csv')
    print("🎉 ETL процесс завершен!")
