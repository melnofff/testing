from flask import Flask, request, jsonify
import pandas as pd
from ml_pipeline import MLPipeline
import joblib
import os
from datetime import datetime

app = Flask(__name__)
pipeline = MLPipeline()

# Загружаем модель при старте
def load_model():
    """Загружаем модель при старте приложения"""
    print("🚀 Загружаем ML модель...")
    success = pipeline.load_model('model')
    if success:
        print("✅ Модель готова к работе")
    else:
        print("❌ Не удалось загрузить модель")

# Загружаем модель сразу при импорте модуля
load_model()

@app.route('/health', methods=['GET'])
def health_check():
    """Проверка здоровья API"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'model_loaded': pipeline.model is not None
    })

@app.route('/predict', methods=['POST'])
def predict():
    """Эндпоинт для предсказаний"""
    try:
        # Получаем данные из запроса
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Проверяем что модель загружена
        if pipeline.model is None:
            return jsonify({'error': 'Model not loaded'}), 503

        # Делаем предсказание
        predictions = pipeline.predict(data)

        # Формируем ответ
        response = {
            'predictions': predictions,
            'timestamp': datetime.now().isoformat(),
            'model_version': '1.0'
        }

        return jsonify(response)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/batch_predict', methods=['POST'])
def batch_predict():
    """Эндпоинт для батчевых предсказаний"""
    try:
        data = request.get_json()

        if not data or 'customers' not in data:
            return jsonify({'error': 'No customers data provided'}), 400

        customers = data['customers']

        if not isinstance(customers, list):
            return jsonify({'error': 'Customers should be a list'}), 400

        # Делаем предсказания
        predictions = pipeline.predict(customers)

        response = {
            'predictions': predictions,
            'total_customers': len(customers),
            'timestamp': datetime.now().isoformat()
        }

        return jsonify(response)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/model_info', methods=['GET'])
def model_info():
    """Информация о модели"""
    if pipeline.model is None:
        return jsonify({'error': 'Model not loaded'}), 503

    feature_importance = None
    if hasattr(pipeline.model, 'feature_importances_'):
        feature_importance = dict(zip(pipeline.feature_columns, pipeline.model.feature_importances_))

    return jsonify({
        'feature_columns': pipeline.feature_columns,
        'target_column': pipeline.target_column,
        'feature_importance': feature_importance,
        'model_type': type(pipeline.model).__name__
    })

if __name__ == '__main__':
    print("🎯 Запускаем ML API...")
    print("📚 Доступные эндпоинты:")
    print("   GET  /health        - Проверка здоровья")
    print("   POST /predict       - Предсказание для одного клиента")
    print("   POST /batch_predict - Предсказание для нескольких клиентов")
    print("   GET  /model_info    - Информация о модели")
    print("\n🌐 API доступен по адресу: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
