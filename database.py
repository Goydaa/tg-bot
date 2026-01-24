import sqlite3
import os
from datetime import datetime

class Database:
    def __init__(self, db_name='bot.db'):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                full_name TEXT,
                contact_type TEXT,
                contact_data TEXT,
                application_type TEXT,
                message_text TEXT,
                appointment_date TEXT,
                appointment_time TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'new'
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                application_id INTEGER,
                reminder_date TEXT,
                reminder_sent BOOLEAN DEFAULT 0,
                FOREIGN KEY (application_id) REFERENCES applications (id)
            )
        ''')
        
        self.conn.commit()
    
    def add_application(self, user_id, username, full_name, contact_type, 
                       contact_data, app_type, message, appointment_date=None, appointment_time=None):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO applications 
            (user_id, username, full_name, contact_type, contact_data, 
             application_type, message_text, appointment_date, appointment_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, full_name, contact_type, contact_data, 
              app_type, message, appointment_date, appointment_time))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_applications(self, status='new'):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM applications 
            WHERE status = ? 
            ORDER BY created_at DESC
        ''', (status,))
        return cursor.fetchall()
    
    def get_all_applications(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM applications ORDER BY created_at DESC')
        return cursor.fetchall()
    
    def get_application_by_id(self, app_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM applications WHERE id = ?', (app_id,))
        return cursor.fetchone()
    
    def update_status(self, app_id, status):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE applications SET status = ? WHERE id = ?', (status, app_id))
        self.conn.commit()
    
    def get_stats(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM applications')
        total = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM applications WHERE status = "new"')
        new = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM applications WHERE status = "processed"')
        processed = cursor.fetchone()[0]
        
        return {'total': total, 'new': new, 'processed': processed}
    
    def add_reminder(self, application_id, reminder_date):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO reminders (application_id, reminder_date)
            VALUES (?, ?)
        ''', (application_id, reminder_date))
        self.conn.commit()
    
    def get_due_reminders(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT r.*, a.user_id, a.username 
            FROM reminders r
            JOIN applications a ON r.application_id = a.id
            WHERE r.reminder_sent = 0 
            AND DATE(r.reminder_date) <= DATE('now')
        ''')
        return cursor.fetchall()
    
    def mark_reminder_sent(self, reminder_id):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE reminders SET reminder_sent = 1 WHERE id = ?', (reminder_id,))
        self.conn.commit()
    
    def close(self):
        self.conn.close()