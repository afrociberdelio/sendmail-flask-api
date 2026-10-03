from flask import Flask, request, jsonify
from flask_mail import Mail, Message
from flask_cors import CORS
import os
import re
import requests

app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": "https://www.saygon.tech", "methods": ["POST"]}})

# Configuração do Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('email')
app.config['MAIL_PASSWORD'] = os.getenv('pass_email')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024  # 16 KB é mais que suficiente para o formulário

mail = Mail(app)

# Cloudflare Turnstile (CAPTCHA) — https://developers.cloudflare.com/turnstile/
TURNSTILE_SECRET_KEY = os.getenv('TURNSTILE_SECRET_KEY')
TURNSTILE_VERIFY_URL = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'
# Hostnames de onde o token pode ter sido gerado, separados por vírgula
ALLOWED_HOSTNAMES = {h.strip() for h in os.getenv('ALLOWED_HOSTNAMES', 'www.saygon.tech,saygon.tech').split(',') if h.strip()}

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def client_ip():
    forwarded = request.headers.get('X-Forwarded-For', '')
    return forwarded.split(',')[0].strip() or request.remote_addr


def verify_turnstile(token):
    if not TURNSTILE_SECRET_KEY or not token:
        return False
    try:
        resp = requests.post(TURNSTILE_VERIFY_URL, data={
            'secret': TURNSTILE_SECRET_KEY,
            'response': token,
            'remoteip': client_ip(),
        }, timeout=5)
        result = resp.json()
    except (requests.RequestException, ValueError):
        return False
    return result.get('success') is True and result.get('hostname') in ALLOWED_HOSTNAMES


@app.route('/', methods=['GET'])
def home():
    return '<h3>Its working<h3>', 200


@app.route('/send-email', methods=['POST'])
def send_email():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Requisição inválida."}), 400

    # Honeypot: campo invisível para humanos. Se veio preenchido, é bot —
    # respondemos sucesso para não dar pistas, mas não enviamos nada.
    if data.get('website'):
        return jsonify({"message": "Email enviado com sucesso!"}), 200

    if not verify_turnstile(data.get('turnstileToken')):
        return jsonify({"error": "Falha na verificação anti-spam."}), 403

    name = str(data.get('name') or '').strip()
    email = str(data.get('email') or '').strip()
    message_body = str(data.get('message') or '').strip()

    if not (1 <= len(name) <= 100):
        return jsonify({"error": "Nome inválido."}), 400
    if len(email) > 254 or not EMAIL_RE.match(email):
        return jsonify({"error": "Email inválido."}), 400
    if not (1 <= len(message_body) <= 5000):
        return jsonify({"error": "Mensagem inválida."}), 400

    try:
        msg = Message(subject="Empresa - Recebemos sua mensagem",
                      sender=app.config['MAIL_USERNAME'],
                      recipients=[os.getenv('email_empresa')],  # Substitua pelo destinatário, lista ['user@mail.com']
                      body=f"Nome: {name}\nEmail: {email}\nMensagem: {message_body}")
        mail.send(msg)
        return jsonify({"message": "Email enviado com sucesso!"}), 200
    except Exception:
        app.logger.exception("Falha ao enviar email")
        return jsonify({"error": "Não foi possível enviar a mensagem."}), 500


if __name__ == "__main__":
    app.run(debug=True)
