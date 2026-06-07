import datetime
import sqlite3
from datetime import datetime

from flask import Flask, render_template, request, redirect, session, url_for, flash
import json

app = Flask(__name__)
app.secret_key = 'monkeydory'


@app.route('/')
def home():
    flowers = load_data()
    addons = load_addons()
    cart = session.get('cart', {})
    selected_addons = session.get('selected_addons', {})
    flower_subtotal = sum(item['price'] * item['quantity'] for item in cart.values())
    addon_subtotal = sum(price for price in selected_addons.values())
    # calculate_total returns a tuple so both values must be unpacked
    total, discount_applied = calculate_total(flower_subtotal, addon_subtotal)
    # Get customer name from URL query string if present
    customername = request.args.get('customer_name')
    return render_template('Index.html', flowers=flowers, addons=addons, cart=cart, total=total, selected_addons=selected_addons, flower_subtotal=flower_subtotal, addon_subtotal=addon_subtotal, customer_name=customername, discount_applied=discount_applied)


# Calculate total cost based on cart contents and selected addons
# Returns a tuple: (total, discount_applied)
def calculate_total(flower_subtotal, addon_subtotal):
    total = flower_subtotal + addon_subtotal
    discount_applied = False
    if total > 180:
        total = total * 0.9
        discount_applied = True
    return total, discount_applied


def load_data():
    # try/except used here as the file may be missing or corrupted
    try:
        with open('data/flowers.json') as file:
            flowers = json.load(file)
        return flowers
    except OSError:
        flash("Could not load flower data.")
        return {}


def load_addons():
    # try/except used here as the file may be missing or corrupted
    try:
        with open('data/addons.json') as file:
            addons = json.load(file)
        return addons
    except OSError:
        flash("Could not load addon data.")
        return {}


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/checkout')
def checkout():
    # Renders a blank invoice page - discount_applied defaults to False
    return render_template('invoices.html', discount_applied=False)


@app.route('/orders')
def order_history():
    # Fetch all orders from the database
    with sqlite3.connect('flower_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM orders')
        rows = cursor.fetchall()

    # Convert each row tuple into a dictionary for easier access in the template
    # json.loads() converts the stored JSON strings back into Python dictionaries
    orders = []
    for row in rows:
        orders.append({
            'order_id': row[0],
            'invoice_number': row[1],
            'customer_name': row[2],
            'items': json.loads(row[3]),
            'addons': json.loads(row[4]),
            'total': row[5],
            'date': row[6]
        })

    return render_template('order_history.html', orders=orders)


@app.route("/remove_from_cart")
def remove_from_cart():

    item = request.args.get('item')

    cart = session.get('cart', {})

    if item in cart:

        cart[item]['quantity'] -= 1
        
        flash(f"Removed 1 {item.capitalize()} from the cart.")

        # Remove the item entirely if quantity reaches zero
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

    # Subtract what's already in the cart to get true available stock
    # This prevents adding more than available across multiple submissions
    already_in_cart = cart[item]['quantity'] if item in cart else 0
    available_stock = products[item]['stock'] - already_in_cart

    if quantity > available_stock:
        flash(f"Sorry, only {available_stock} {item}(s) available.")
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
    # Load existing addons so previous selections are not overwritten
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
    # Clear cart and addons from the session
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

        # Clear the cart and addons from the session after confirming
        session.pop('cart', None)
        session.pop('selected_addons', None)
        session.modified = True

        invoice_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Generate a unique invoice number based on the current timestamp
        invoice_number = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Save order to SQLite database
        # json.dumps() converts the cart and addons dictionaries to strings for storage
        with sqlite3.connect('flower_shop.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO orders (invoice_number, customer_name, items, addons, total)
                VALUES (?, ?, ?, ?, ?)
            ''', (invoice_number, customer_name, json.dumps(cart), json.dumps(selected_addons), total))
            conn.commit()

        # Generate invoice text file saved to the Invoices folder
        # try/except used as the file path may be invalid or the folder missing
        invoice_filename = f"Invoices/{invoice_number}.txt"

        try:
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
        except OSError as e:
            flash("Could not generate invoice file.")
            print(f"Error writing invoice: {e}")

        # Update the stock in flowers.json after the order is confirmed
        # try/except used as the file could be open elsewhere or write protected
        try:
            with open('data/flowers.json', 'r') as file:
                flower_data = json.load(file)

            for flower_name, details in cart.items():
                if flower_name in flower_data:
                    flower_data[flower_name]['stock'] -= details['quantity']
                    # Prevent stock going negative
                    if flower_data[flower_name]['stock'] < 0:
                        flower_data[flower_name]['stock'] = 0

            with open('data/flowers.json', 'w') as file:
                json.dump(flower_data, file, indent=4)
        except OSError as e:
            flash("Could not update stock file.")
            print(f"Error updating stock: {e}")

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


@app.route('/cancel_saved_order/<int:order_id>', methods=['POST'])
def cancel_saved_order(order_id):
    # Delete the order from the database using its unique order_id
    # The <int:order_id> in the route captures the ID from the URL
    with sqlite3.connect('flower_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM orders WHERE order_id = ?', (order_id,))
        conn.commit()
    flash("Order cancelled.")
    return redirect(url_for('order_history'))


if __name__ == '__main__':
    initialise_database()
    app.run(debug=True)