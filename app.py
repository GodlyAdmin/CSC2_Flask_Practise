import datetime
import sqlite3
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
    total, discount_applied = calculate_total(flower_subtotal, addon_subtotal)
    customername = request.args.get('customer_name')
    return render_template('Index.html', flowers=flowers, addons=addons, cart=cart, total=total, selected_addons=selected_addons, flower_subtotal=flower_subtotal, addon_subtotal=addon_subtotal, customer_name=customername, discount_applied=discount_applied)

# Calculate total cost based on cart contents and selected addons
def calculate_total(flower_subtotal, addon_subtotal):
    total = flower_subtotal + addon_subtotal
    discount_applied = False 
    if total > 180:
        total = total * 0.9
        discount_applied = True
    return total, discount_applied

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
    return render_template('invoices.html', discount_applied=False)

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

    selected_addons = session.get('selected_addons', {})

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
    cart = session.get('cart')
    if not customer_name:
        flash("Please enter your name to confirm the order.")
        return redirect(url_for('home'))

    if not cart:
        flash("Your cart is empty. Please add items before confirming the order.")
        return redirect(url_for('home'))
    else:

        cart = session.get('cart', {})
        selected_addons = session.get('selected_addons', {})
        flower_subtotal = sum(item['price'] * item['quantity'] for item in cart.values())
        addon_subtotal = sum(price for price in selected_addons.values())
        total, discount_applied = calculate_total(flower_subtotal, addon_subtotal)

        flash(f"Thank you {customer_name}! Your order has been confirmed. Total: ${total}")

        session.pop('cart', None)
        session.pop('selected_addons', None)
        session.modified = True

        invoice_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        invoice_number = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        #Save order to SQLite database
        with sqlite3.connect('flower_shop.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO orders (invoice_number, customer_name, items, addons, total)
                VALUES (?, ?, ?, ?, ?)
            ''', (invoice_number, customer_name, json.dumps(cart), json.dumps(selected_addons), total))
            conn.commit()
        #generate invoice file
        invoice_filename = f"Invoices/{invoice_number}.txt"

        with open(invoice_filename, 'w') as f:
            f.write(f"Invoice Number: {invoice_number}\n")
            f.write(f"Customer Name: {customer_name}\n")
            f.write(f"Invoice Date: {invoice_date}\n\n")
            f.write("Items:\n")
            for item, details in cart.items():
                f.write(f"{item}: {details['quantity']} x ${details['price']} = ${details['quantity'] * details['price']}\n")
            f.write("\nAdd-ons:\n")
            for addon, price in selected_addons.items():
                f.write(f"{addon}: ${price}\n")
            f.write(f"\nSubtotal Flowers: ${flower_subtotal:.2f}\n")
            f.write(f"Subtotal Add-ons: ${addon_subtotal:.2f}\n")
            if discount_applied:
                f.write("10% discount applied.\n")
            f.write(f"Total: ${total:.2f}\n")

        # Update the stock in flowers.json
        with open('data/flowers.json', 'r') as file:
            flower_data = json.load(file)

            for flower_name, details in cart.items():
                if flower_name in flower_data:
                    flower_data[flower_name]['stock'] -= details['quantity']
                    if flower_data[flower_name]['stock'] < 0:
                        flower_data[flower_name]['stock'] = 0  # prevent negative stock

            with open('data/flowers.json', 'w') as file:
                json.dump(flower_data, file, indent=4)
        return render_template('invoices.html', invoice_number=invoice_number, customer_name=customer_name, invoice_date=invoice_date, cart=cart, selected_addons=selected_addons, flower_subtotal=flower_subtotal, addon_subtotal=addon_subtotal, total=total, discount_applied=discount_applied)

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