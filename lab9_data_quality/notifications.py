import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
from datetime import datetime
from data_quality_framework import DataQualityFramework

class NotificationSystem:
    def __init__(self):
        self.config = self.load_config()
    
    def load_config(self):
        """Загружаем конфигурацию уведомлений"""
        try:
            with open('config.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Конфигурация по умолчанию
            return {
                'email': {
                    'enabled': False,
                    'smtp_server': 'smtp.gmail.com',
                    'smtp_port': 587,
                    'sender_email': 'your_email@gmail.com',
                    'sender_password': 'your_password',
                    'recipient_emails': ['admin@company.com']
                },
                'slack': {
                    'enabled': False,
                    'webhook_url': 'your_slack_webhook'
                }
            }
    
    def send_email_alert(self, report):
        """Отправляем email уведомление"""
        if not self.config['email']['enabled']:
            print("📧 Email уведомления отключены в конфигурации")
            return
        
        try:
            # Создаем сообщение
            msg = MimeMultipart()
            msg['From'] = self.config['email']['sender_email']
            msg['To'] = ', '.join(self.config['email']['recipient_emails'])
            msg['Subject'] = f'🚨 Data Quality Alert - {datetime.now().strftime("%Y-%m-%d %H:%M")}'
            
            # Создаем тело сообщения
            body = f"""
            <h2>Data Quality Report</h2>
            <p><strong>Overall Score:</strong> {report['overall_score']:.1f}%</p>
            <p><strong>Passed Checks:</strong> {report['passed_checks']}/{report['total_checks']}</p>
            
            <h3>Alerts:</h3>
            <ul>
            """
            
            for alert in report['alerts']:
                body += f"<li>{alert}</li>"
            
            body += "</ul>"
            
            msg.attach(MimeText(body, 'html'))
            
            # Отправляем email
            server = smtplib.SMTP(self.config['email']['smtp_server'], self.config['email']['smtp_port'])
            server.starttls()
            server.login(self.config['email']['sender_email'], self.config['email']['sender_password'])
            server.send_message(msg)
            server.quit()
            
            print("✅ Email уведомление отправлено")
            
        except Exception as e:
            print(f"❌ Ошибка отправки email: {e}")
    
    def send_console_alert(self, report):
        """Выводим уведомление в консоль"""
        print("\n" + "="*50)
        print("🚨 DATA QUALITY ALERT")
        print("="*50)
        print(f"Overall Score: {report['overall_score']:.1f}%")
        print(f"Passed Checks: {report['passed_checks']}/{report['total_checks']}")
        
        if report['alerts']:
            print("\nAlerts:")
            for alert in report['alerts']:
                print(f"  • {alert}")
        else:
            print("\n✅ No alerts - data quality is good!")
        
        print("="*50)
    
    def check_and_notify(self):
        """Проверяем качество данных и отправляем уведомления"""
        dq = DataQualityFramework()
        report = dq.generate_report()
        
        # Всегда показываем в консоли
        self.send_console_alert(report)
        
        # Отправляем email если есть алерты и email включен
        if report['alerts'] and self.config['email']['enabled']:
            self.send_email_alert(report)

if __name__ == "__main__":
    notifier = NotificationSystem()
    notifier.check_and_notify()
