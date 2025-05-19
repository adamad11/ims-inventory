import psycopg2
from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user

# --- Flask Login Setup ---
login_manager = LoginManager()
login_manager.login_view = 'main.login'

class Admin(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return Admin(user_id)

# --- Blueprint Setup ---
main = Blueprint('main', __name__)

# --- PostgreSQL Connection ---
def get_connection():
    return psycopg2.connect(
        host="localhost",
        database="Adam_K_D_BSDS_GRP_A",  # Replace with your actual DB
        user="postgres",
        password="ims123"
    )

# ================= ROUTES =================

# --- Login ---
@main.route('/login', methods=['GET', 'POST'])
def login():
    error = ""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'admin' and password == 'ims123':
            user = Admin(id=1)
            login_user(user)
            return redirect(url_for('main.dashboard'))
        else:
            error = "❌ Invalid credentials"
    return render_template('login.html', error=error)

# --- Logout ---
@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))

# --- Home → Redirect to dashboard ---
@main.route('/')
@login_required
def home():
    return redirect(url_for('main.dashboard'))

# --- Dashboard ---
@main.route('/dashboard')
@login_required
def dashboard():
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM view_low_stock;")
        low_stock_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM Items;")
        total_items = cur.fetchone()[0]

        cur.execute("SELECT Item_description, total_orders FROM mv_top_ordered_items LIMIT 5;")
        top_items = cur.fetchall()

        cur.execute("SELECT OrderNo, Date_Completed FROM mv_recent_completed_orders LIMIT 5;")
        recent_orders = cur.fetchall()

        cur.close()
        conn.close()

        return render_template(
            'dashboard.html',
            low_stock_count=low_stock_count,
            total_items=total_items,
            top_items=top_items,
            recent_orders=recent_orders
        )
    except Exception as e:
        return f"❌ Dashboard Query Error: {str(e)}"

# --- Items Page ---
@main.route('/items')
@login_required
def items():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Items ORDER BY ItemNo;")
    items_data = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('items.html', items=items_data)

# --- Inventory Page ---
@main.route('/inventory')
@login_required
def inventory():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT inv.InventoryID, i.Item_description, inv.Quantity
        FROM Inventory inv
        JOIN Items i ON inv.ItemID = i.ItemNo
        ORDER BY inv.InventoryID;
    """)
    inventory_data = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('inventory.html', inventory=inventory_data)

# --- Orders Page ---
@main.route('/orders', methods=['GET', 'POST'])
@login_required
def orders():
    conn = get_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        order_no = request.form.get('order_no')
        try:
            cur.execute("CALL complete_order(%s);", (order_no,))
            conn.commit()
        except Exception as e:
            conn.rollback()
            return f"❌ Failed to complete order {order_no}: {str(e)}"

    cur.execute("""
        SELECT OrderNo, Date_Required, Date_Completed, ShipmentNo
        FROM Orders
        ORDER BY OrderNo DESC;
    """)
    orders = cur.fetchall()

    cur.close()
    conn.close()
    return render_template('orders.html', orders=orders)

# --- Shipments Page ---
@main.route('/shipments', methods=['GET', 'POST'])
@login_required
def shipments():
    conn = get_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        date = request.form.get('shipment_date')
        try:
            cur.execute("CALL add_shipment(%s);", (date,))
            conn.commit()
        except Exception as e:
            conn.rollback()
            return f"❌ Failed to add shipment: {str(e)}"

    cur.execute("SELECT ShipmentNo, ShipmentDate FROM Shipments ORDER BY ShipmentNo DESC;")
    shipments = cur.fetchall()

    cur.close()
    conn.close()
    return render_template('shipments.html', shipments=shipments)

# --- Stored Procedures Page ---
@main.route('/procedures', methods=['GET', 'POST'])
@login_required
def procedures():
    message = ""
    conn = get_connection()
    cur = conn.cursor()

    try:
        if request.method == 'POST':
            action = request.form.get('action')

            if action == 'replenish':
                item_id = int(request.form.get('item_id'))
                quantity = int(request.form.get('quantity'))
                cur.execute("CALL replenish_inventory(%s, %s);", (item_id, quantity))
                conn.commit()
                message = f"✅ Stock replenished for Item #{item_id}"

            elif action == 'discount':
                order_no = int(request.form.get('order_no'))
                discount = float(request.form.get('discount'))
                cur.execute("CALL apply_order_discount(%s, %s);", (order_no, discount))
                conn.commit()
                message = f"✅ Discount applied to Order #{order_no}"

            elif action == 'log_low_stock':
                threshold = int(request.form.get('threshold'))
                cur.execute("CALL log_low_stock(%s);", (threshold,))
                conn.commit()
                message = f"✅ Low stock logged for all items below {threshold}"

    except Exception as e:
        conn.rollback()
        message = f"❌ Error: {str(e)}"

    cur.close()
    conn.close()
    return render_template("procedures.html", message=message)

