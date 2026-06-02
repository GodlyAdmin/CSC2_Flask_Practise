from ast import Add
import datetime
from dbm import sqlite3
from itertools import product
from datetime import datetime

from flask import Flask, render_template, request, redirect, session, url_for, flash
import json

app = Flask (__name__)
app.secret_key = 'monkeydory'


@app.route('/')
def home():
    flowers = load_data()
    addons = load_addons()
    cart = session.get('cart', {})
    selected_addons = session.get('selected_addons', {}) 
    flower_subtotal = sum(item['price'] * item['quantity'] for item in cart.values())
    addon_subtotal = sum(price for price in selected_addons.values())
    total = calculate_total(flower_subtotal, addon_subtotal)
    customername = request.args.get('customer_name')
    return render_template('Index.html', flowers=flowers, addons=addons, cart=cart, total=total, selected_addons=selected_addons, flower_subtotal=flower_subtotal, addon_subtotal=addon_subtotal, customer_name=customername)

# Calculate total cost based on cart contents and selected addons
def calculate_total(flower_subtotal, addon_subtotal):
    total = flower_subtotal + addon_subtotal
    return total

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
    return render_template('invoices.html')

@app.route('/orders')
def order_history():
    return render_template('order_history.html')

@app.route("/remove_from_cart")
def remove_from_cart():

    item = request.args.get('item')

    cart = session.get('cart', {})

    if item in cart:

        cart[item]['quantity'] -= 1

        flash(f"Removed 1 {item.capitalize()} from the cart.")

        if cart[item]['quantity'] <= 0:
            del cart[item]

        session['cart'] = cart
        session.modified = True

    return redirect(url_for('home'))

# Add selected flower to the shopping cart
@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():

    flower = request.form.get('flower')

    item = flower if flower else None

    quantity = int(request.form['quantity'])

    flowers = load_data()

    cart = session.get('cart', {})

    products = {**flowers}

    if item not in products:
        flash("Invalid item selected.")
        return redirect(url_for('home'))

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

    return redirect(url_for('home'))

# Add selected addons to the session
@app.route('/select_addon', methods=['POST'])
def select_addon():

    addons = load_addons()
    selected_keys = request.form.getlist('addons')
    
    selected_addons = session.get('selected_addons', {})  # load existing
    
    for addon in selected_keys:
        if addon in addons:
            selected_addons[addon] = float(addons[addon]['price'])

    session['selected_addons'] = selected_addons
    session.modified = True
    flash(f"{len(selected_keys)} add-on(s) added to cart.")
    return redirect(url_for('home'))

@app.route('/cancel_order', methods=['POST'])
def cancel_order():
    session.pop('cart', None)
    session.pop('selected_addons', None)
    session.modified = True
    flash("Order cancelled.")
    return redirect(url_for('home'))

@app.route('/confirm_order', methods=['POST'])
def confirm_order():
    customer_name = request.form.get('customer_name')
    if not customer_name:
        flash("Please enter your name to confirm the order.")
        return redirect(url_for('home'))

    if cart := session.get('cart') is None:
        flash("Your cart is empty. Please add items before confirming the order.")
        return redirect(url_for('home'))
    else:

        cart = session.get('cart', {})
        selected_addons = session.get('selected_addons', {})
        flower_subtotal = sum(item['price'] * item['quantity'] for item in cart.values())
        addon_subtotal = sum(price for price in selected_addons.values())
        total = calculate_total(flower_subtotal, addon_subtotal)

        flash(f"Thank you {customer_name}! Your order has been confirmed. Total: ${total}")

        session.pop('cart', None)
        session.pop('selected_addons', None)
        session.modified = True
    
        invoice_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        invoice_number = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        return render_template('invoices.html', customer_name=customer_name, cart=cart, selected_addons=selected_addons, total=total, invoice_date=invoice_date, invoice_number=invoice_number, flower_subtotal=flower_subtotal, addon_subtotal=addon_subtotal)
    
def initialise_database():
    with sqlite3.connect('flower_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT,
                customer_name TEXT,
                items TEXT,
                addons TEXT,
                total REAL,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
if __name__ == '__main__':
    initialise_database()
    app.run(debug=True)