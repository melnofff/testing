from flask import Flask, render_template, jsonify
from data_quality_framework import DataQualityFramework
import json
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def dashboard():
    """Главная страница дашборда"""
    # Запускаем проверку качества данных
    dq = DataQualityFramework()
    report = dq.generate_report()
    dq.create_visualizations()
    
    # Передаем отчет в шаблон
    return render_template('dashboard.html', report=report)

@app.route('/api/metrics')
def api_metrics():
    """API endpoint для получения метрик"""
    dq = DataQualityFramework()
    report = dq.generate_report()
    return jsonify(report)

@app.route('/api/alerts')
def api_alerts():
    """API endpoint для получения алертов"""
    dq = DataQualityFramework()
    report = dq.generate_report()
    return jsonify({'alerts': report['alerts'], 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    print("🚀 Запускаем дашборд качества данных...")
    print("📊 Откройте http://localhost:5000 в браузере")
    app.run(debug=True, host='0.0.0.0', port=5000)
