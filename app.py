from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret.key = 'TheSecretKey'

if __name__ == '__main__':
    app.run(debug=True)

@app.route('/')
def index():
    return render_template('index.html')