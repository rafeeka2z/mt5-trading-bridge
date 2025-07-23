from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return '''
    <html>
    <head><title>MT5 Trading Bridge</title></head>
    <body style="font-family: Arial; padding: 50px; background: #1a1a1a; color: white;">
        <h1>🚀 MT5 Trading Bridge is Running!</h1>
        <p>✅ Heroku deployment successful</p>
        <p>📍 Your webhook URL: <code>https://a2ztrading-a7c73d7225ba.herokuapp.com/webhook/test</code></p>
        <p>🔧 Login credentials: ramshad / Trading@123</p>
        <hr>
        <p>Next steps: Add authentication and trading features</p>
    </body>
    </html>
    '''

@app.route('/webhook/<key>', methods=['POST', 'GET'])
def webhook(key):
    return {"status": "success", "message": f"Webhook {key} received", "app": "running"}

if __name__ == '__main__':
    import os
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
