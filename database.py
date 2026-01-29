import sqlite3
from datetime import datetime

class Database:
    def __init__(self, db_name='applications.db'):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.init_db()
    
    def init_db(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                full_name TEXT,
                contact_data TEXT,
                app_type TEXT,
                message TEXT,
                appointment_date TEXT,
                appointment_time TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'new'
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                application_id INTEGER,
                reminder_date TEXT,
                sent INTEGER DEFAULT 0
            )
        ''')
        self.conn.commit()
    
    def add_application(self, user_id, username, full_name, contact_data, app_type, message, appointment_date=None, appointment_time=None):
        try:
            self.cursor.execute('''
                INSERT INTO applications 
                (user_id, username, full_name, contact_data, app_type, message, appointment_date, appointment_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, username, full_name, contact_data, app_type, message, appointment_date, appointment_time))
            self.conn.commit()
            return self.cursor.lastrowid
        except:
            return None
    
    def add_reminder(self, app_id, reminder_date):
        try:
            self.cursor.execute('INSERT INTO reminders (application_id, reminder_date) VALUES (?, ?)', (app_id, reminder_date))
            self.conn.commit()
        except:
            pass
    
    def mark_reminder_sent(self, reminder_id):
        """Пометить напоминание как отправленное"""
        try:
            self.cursor.execute('UPDATE reminders SET sent = 1 WHERE id = ?', (reminder_id,))
            self.conn.commit()
            return True
        except:
            return False
    
    def get_due_reminders(self):
        """Получить непосланные напоминания на сегодня или ранее"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            self.cursor.execute('''
                SELECT a.id, r.id, a.user_id, a.username 
                FROM reminders r
                JOIN applications a ON r.application_id = a.id
                WHERE r.reminder_date <= ? AND r.sent = 0 AND a.appointment_date IS NOT NULL
            ''', (today,))
            return self.cursor.fetchall()
        except:
            return []
    
    def get_applications(self, status='new'):
        self.cursor.execute('SELECT * FROM applications WHERE status = ? ORDER BY created_at DESC', (status,))
        return self.cursor.fetchall()
    
    def get_all_applications(self):
        self.cursor.execute('SELECT * FROM applications ORDER BY created_at DESC')
        return self.cursor.fetchall()
    
    def get_application_by_id(self, app_id):
        self.cursor.execute('SELECT * FROM applications WHERE id = ?', (app_id,))
        return self.cursor.fetchone()
    
    def update_status(self, app_id, status):
        self.cursor.execute('UPDATE applications SET status = ? WHERE id = ?', (status, app_id))
        self.conn.commit()
    
    def delete_application(self, app_id):
        self.cursor.execute('DELETE FROM reminders WHERE application_id = ?', (app_id,))
        self.cursor.execute('DELETE FROM applications WHERE id = ?', (app_id,))
        self.conn.commit()
    
    def get_stats(self):
        self.cursor.execute('SELECT COUNT(*) FROM applications')
        total = self.cursor.fetchone()[0]
        self.cursor.execute("SELECT COUNT(*) FROM applications WHERE status = 'new'")
        new = self.cursor.fetchone()[0]
        processed = total - new
        return {'total': total, 'new': new, 'processed': processed}
