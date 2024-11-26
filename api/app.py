from flask import Flask, request, jsonify
from flask_mail import Mail, Message
from flask_cors import CORS
import os

app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": "https://www.saygon.tech", "methods": ["POST"]}})

# Configuração do Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('email')
app.config['MAIL_PASSWORD'] = os.getenv('pass_email')

mail = Mail(app)


@app.route('/', methods=['GET'])
def home():
    return '<h3>Its working<h3>', 200


@app.route('/send-email', methods=['POST'])
def send_email():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    message_body = data.get('message')

    try:
        msg = Message(subject="Empresa - Recebemos sua mensagem",
                      sender=app.config['MAIL_USERNAME'],
                      recipients=[os.getenv('email_empresa')],  # Substitua pelo destinatário, lista ['user@mail.com']
                      body=f"Nome: {name}\nEmail: {email}\nMensagem: {message_body}")
        mail.send(msg)
        return jsonify({"message": "Email enviado com sucesso!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}, email, app.config['MAIL_PASSWORD']), 500


if __name__ == "__main__":
    app.run(debug=True)
