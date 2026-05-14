from itertools import product

from flask import Flask, render_template, request, redirect, session, url_for, flash
import json

app = Flask (__name__)
app.secret_key = 'monkeydory'


@app.route('/')
def index():
    flowers = load_data()
    addons = load_addons()
    cart = session.get('cart', {})
    return render_template('index.html', flowers=flowers, addons=addons, cart=cart)

def load_data():
    with open('data/flowers.json') as file:
        flowers = json.load(file)
    return flowers

def load_addons():
    with open('data/addons.json') as file:
        addons = json.load(file)
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
    flowers = load_data()
    addons = load_addons()
    cart = session.get('cart', {})

    return render_template(
        'index1.html',
        flowers=flowers,
        addons=addons,
        cart=cart
    )

# Add selected flower to the shopping cart
@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():

    flower = request.form.get('flower')
    addon = request.form.get('addon')

    item = flower if flower else addon

    quantity = int(request.form['quantity'])

    flowers = load_data()
    addons = load_addons()

    cart = session.get('cart', {})

    # combine both dictionaries
    products = {**flowers, **addons}

    if item not in products:
        flash("Invalid item selected.")
        return redirect(url_for('index1'))

    if item in cart:
        cart[item]['quantity'] += quantity
    else:
        cart[item] = {
            'price': products[item]['price'],
            'quantity': quantity
        }

    session['cart'] = cart
    session.modified = True

    flash(f"{quantity} {item}(s) added to cart.")

    return redirect(url_for('index1'))

if __name__ == '__main__':
    app.run(debug=True)
    