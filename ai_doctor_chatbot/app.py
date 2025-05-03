from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from database import Database
from ai_service import AIService

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

db = Database()
ai = AIService()

def validate_password(password):
    return password and isinstance(password, str) and len(password) >= 8

# Custom template filters
@app.template_filter('format_datetime')
def format_datetime(value, format='%b %d, %Y %I:%M %p'):
    if not value:
        return "No timestamp"
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            return value
    if isinstance(value, datetime):
        return value.strftime(format)
    return str(value)

@app.template_filter('time_ago')
def time_ago_filter(dt):
    if not dt:
        return "never"
    
    if isinstance(dt, str):
        try:
            dt = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            return dt
    
    now = datetime.now()
    diff = now - dt
    
    if diff.days > 365:
        return f"{diff.days // 365} years ago"
    if diff.days > 30:
        return f"{diff.days // 30} months ago"
    if diff.days > 0:
        return f"{diff.days} days ago"
    if diff.seconds > 3600:
        return f"{diff.seconds // 3600} hours ago"
    if diff.seconds > 60:
        return f"{diff.seconds // 60} minutes ago"
    return "just now"

# User class
class User(UserMixin):
    def __init__(self, id, name, is_admin=False):
        self.id = id
        self.name = name
        self.is_admin = is_admin

    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    user_data = db.get_user_by_id(user_id)
    if user_data:
        return User(id=user_data['id'], name=user_data['name'], is_admin=user_data.get('is_admin', False))
    return None

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('patient_dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        password = request.form.get('password', '').strip()
        remember = request.form.get('remember') == 'on'

        if not name or not password:
            flash('Name and password are required', 'danger')
            return redirect(url_for('login'))

        user_data = db.verify_user_by_name(name, password)
        if not user_data:
            flash('Invalid name or password', 'danger')
            return redirect(url_for('login'))

        user = User(id=user_data['id'], name=user_data['name'], is_admin=user_data.get('is_admin', False))
        login_user(user, remember=remember)
        db.update_user_last_active(user.id)
        flash('Login successful!', 'success')

        if user.is_admin:
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('patient_dashboard'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not name:
            flash('Name is required', 'danger')
            return redirect(url_for('register'))

        if len(password) < 8:
            flash('Password must be at least 8 characters', 'danger')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('register'))

        if db.get_user_by_name(name):
            flash('Name already registered', 'danger')
            return redirect(url_for('register'))

        user_id = db.create_user(name, password)
        if user_id:
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))

        flash('Registration failed. Please try again.', 'danger')

    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/patient/dashboard')
@login_required
def patient_dashboard():
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))

    recent_chats = db.get_chat_history(current_user.id, limit=5) or []
    
    # Convert string timestamps to datetime objects if needed
    for chat in recent_chats:
        if isinstance(chat.get('timestamp'), str):
            try:
                chat['timestamp'] = datetime.strptime(chat['timestamp'], '%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                chat['timestamp'] = None
    
    return render_template('patient_dashboard.html', recent_chats=recent_chats)

@app.route('/patient/profile', methods=['GET', 'POST'])
@login_required
def patient_profile():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        dob = request.form.get('dob', '').strip()
        gender = request.form.get('gender', '').strip()
        allergies = request.form.get('allergies', '').strip()
        medications = request.form.get('medications', '').strip()

        if db.update_user_profile(current_user.id, name, dob, gender, allergies, medications):
            flash('Profile updated successfully', 'success')
        else:
            flash('Error updating profile', 'danger')

    return render_template('patient.html', user=current_user)

@app.route('/patient/chat', methods=['GET', 'POST'])
@login_required
def chat():
    if request.method == 'POST':
        message = request.form.get('message', '').strip()

        if not message:
            flash('Message cannot be empty', 'danger')
            return redirect(url_for('chat'))

        try:
            history = db.get_chat_history(current_user.id) or []
            messages = [{
                "role": "system",
                "content": f"You are an AI medical doctor assistant. Patient: {current_user.name}, "
            }]

            for msg in history:
                role = "user" if msg.get('is_user_message') else "assistant"
                content = msg.get('message') if msg.get('is_user_message') else msg.get('response', '')
                if content:
                    messages.append({"role": role, "content": content})

            messages.append({"role": "user", "content": message})
            ai_response = ai.chat_completion(messages) or "I'm sorry, I couldn't process your request."

            db.save_chat_message(current_user.id, message, ai_response, True)
            db.save_chat_message(current_user.id, ai_response, "", False)

            flash('Message sent and AI response received!', 'success')
            return redirect(url_for('chat'))

        except Exception as e:
            flash(f'Error communicating with AI: {str(e)}', 'danger')
            return redirect(url_for('chat'))

    chat_history = db.get_chat_history(current_user.id) or []
    
    # Convert string timestamps to datetime objects if needed
    for chat in chat_history:
        if isinstance(chat.get('timestamp'), str):
            try:
                chat['timestamp'] = datetime.strptime(chat['timestamp'], '%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                chat['timestamp'] = None
    
    return render_template('chat.html', chat_history=chat_history)

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('patient_dashboard'))

    users = db.get_all_users() or []
    return render_template('admin_dashboard.html',
                         users=users,
                         current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

@app.route('/admin/patients')
@login_required
def admin_patients():
    if not current_user.is_admin:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('patient_dashboard'))

    patients = db.get_all_users() or []
    return render_template('admin_patients.html', patients=patients)

@app.route('/admin/patient/create', methods=['GET', 'POST'])
@login_required
def admin_create_patient():
    if not current_user.is_admin:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('patient_dashboard'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        password = request.form.get('password', '').strip()
        dob = request.form.get('dob', '').strip()
        gender = request.form.get('gender', '').strip()

        if not name:
            flash('Name is required', 'danger')
            return redirect(url_for('admin_create_patient'))

        if len(password) < 8:
            flash('Password must be at least 8 characters', 'danger')
            return redirect(url_for('admin_create_patient'))

        if db.get_user_by_name(name):
            flash('User name already exists', 'danger')
            return redirect(url_for('admin_create_patient'))

        user_id = db.create_user(name, password)
        if user_id:
            db.update_user_profile(user_id, name, dob, gender)
            flash('Patient created successfully', 'success')
            return redirect(url_for('admin_patients'))

        flash('Error creating patient', 'danger')

    return render_template('create_patient.html')

@app.route('/admin/patient/<int:user_id>')
@login_required
def admin_view_patient(user_id):
    if not current_user.is_admin:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('patient_dashboard'))

    patient = db.get_user_by_id(user_id)
    if not patient:
        flash('Patient not found', 'danger')
        return redirect(url_for('admin_patients'))

    chat_history = db.get_chat_history(user_id) or []
    
    # Convert string timestamps to datetime objects if needed
    for chat in chat_history:
        if isinstance(chat.get('timestamp'), str):
            try:
                chat['timestamp'] = datetime.strptime(chat['timestamp'], '%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                chat['timestamp'] = None
    
    return render_template('admin_view_patient.html', patient=patient, chat_history=chat_history)

if __name__ == '__main__':
    app.run(debug=True)