from flask import Flask, render_template, request, redirect, url_for, flash
import json

app = Flask (__name__)
app.secret_key = 'your_secret_key'


@app.route('/')
def index():
    flowers = load_data()
    return render_template('index.html', flowers=flowers)
def load_data():
    with open('data/flowers.json') as file:
        flowers = json.load(file)
    return flowers
@app.route('/about')
def about():
    return render_template('about.html')
@app.route('/checkout')
def checkout():
    return render_template('invoice.html')
@app.route('/orders')
def order_history():
    return render_template('order_history.html')

if __name__ == '__main__':
    app.run(debug=True)
    