from itertools import product

from flask import Flask, render_template, request, redirect, session, url_for, flash
import json

app = Flask (__name__)
app.secret_key = 'your_secret_key'


@app.route('/')
def index():
    flowers = load_data()
    addons = load_addons()
    return render_template('index.html', flowers=flowers, addons=addons)
def load_data():
    with open('data/flowers.json') as file:
        flowers = json.load(file)
    return flowers

def load_addons():
    with open('data/addons.json') as file:
        addons = json.load(file)
    
    for product_name, product in addons.items():
        if product.get('stock', 0) == 0:
            push_to_website = f"{product_name} is out of stock"
            flash(push_to_website, 'error')    

    return addons

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/checkout')
def checkout():
    return render_template('invoice.html')

@app.route('/orders')
def order_history():
    return render_template('order_history.html')

@app.route('/index1')
def index1():
    return render_template('index1.html')

# Add selected flower to the shopping cart
@app. route('/add_to_cart', methods=['POST' ] )
def add_to_cart():
    flower = request. form['flower'] # get selected flower name
    quantity = int(request.form['quantity']) # convert quantity to a number
    flowers = load_data() # get flower data from file
    cart = session.get('cart', {}) # get cart from session or start fresh

    if flower not in flowers:
        flash("Invalid flower selected.")
        return redirect(url_for('index1'))

    if flower in cart:
        cart [flower] ['quantity'] += quantity # add existing quantity
    else:
        cart [flower] = {
            'price': flowers [flower] [ 'price' ],
            'quantity': quantity
        }

    session['cart'] = cart # update session
    session.modified = True # force Flask to save it
    flash(f"{quantity} {flowers} (s) added to cart.")
    return redirect(url_for('index1'))

if __name__ == '__main__':
    app.run(debug=True)
    