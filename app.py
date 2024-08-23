from flask import Flask, request, jsonify
import psycopg2
import re
import datetime
import json
from uuid import uuid4

app = Flask(__name__)

# Function to connect to the PostgreSQL database
def connect_db():
    try:
        conn = psycopg2.connect(
            dbname="runpharmacy",
            user="pawan",
            password="pawan",
            host="139.59.77.208",
            port="5432"
        )
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

# Function to add a new customer
def add_customer(conn, data):
    cur = conn.cursor()

    # Generate UUID for user_id
    user_id = str(uuid4())

    # Extract and split name into first and last names
    full_name = data.get('name', '')
    name_parts = full_name.split(' ', 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ''

    dob = data.get('dob')
    email = data.get('email')
    phone = data.get('phone')
    is_email_verified = data.get('verified', 'N')
    is_phone_verified = data.get('active', 'N')
    address_list = data.get('address', [])
    created_by = data.get('created_by', 'System')
    updated_by = data.get('updated_by', 'System')

    # Check if address_list is a list and has at least one entry
    if not isinstance(address_list, list) or len(address_list) == 0:
        return "Address is required and must be a list with at least one entry."

    # Extract address details from the first address entry
    address = address_list[0]
    address_city = address.get('Address_City')
    address_state = address.get('Address_State')
    address_pincode = address.get('Address_Pincode')

    # Validate that address details are provided
    if not address_pincode:
        return "Pincode is required."

    # Step 1: Calculate age and validate
    today = datetime.date.today()
    try:
        birth_date = datetime.datetime.strptime(dob, '%Y-%m-%d').date()
    except ValueError:
        return "Invalid date of birth format. Use YYYY-MM-DD."
    
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    
    if age < 18:
        return "Age must be 18 or older"

    # Step 2: Validate email format
    email_pattern = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
    if not re.match(email_pattern, email):
        return "Invalid email format"

    # Step 3: Check if email exists
    cur.execute('SELECT 1 FROM dev.customer WHERE customer_email_id = %s', (email,))
    if cur.fetchone():
        return "Email already exists"

    # Step 4: Validate mobile number format
    if not re.match(r'^[0-9]{10}$', phone):
        return "Invalid phone number format"

    # Step 5: Check if mobile number exists
    cur.execute('SELECT 1 FROM dev.customer WHERE customer_mobile_no = %s', (phone,))
    if cur.fetchone():
        return "Phone number already exists"

    # Step 6: Check if pincode exists in the Pincode table
    try:
        cur.execute("""
            SELECT "Division Name", "Region Name", "Circle Name", "statename"
            FROM dev.pincode 
            WHERE pincode = %s
        """, (address_pincode,))
        
        pincode_data = cur.fetchone()

        if pincode_data is None:
            return "Invalid pincode. Please enter a valid pincode."

        # Debugging statement
        print("Pincode Data:", pincode_data)

        # Ensure pincode_data is a tuple
        if not isinstance(pincode_data, tuple) or len(pincode_data) != 4:
            return "Unexpected format of pincode data."

        # Extract details from pincode data
        division_name, region_name, circle_name, state_name = pincode_data

    except Exception as e:
        return f"Error querying pincode data: {str(e)}"

    # Populate address details
    address_json = {
        "Circle_Name": circle_name,
        "Region_Name": region_name,
        "Pincode": address_pincode,
        "District": address_city,  # Assuming District = City
        "StateName": state_name,
        "Address_Line_1": address.get('Address_Line_1'),
        "Address_Line_2": address.get('Address_Line_2'),
        "Address_City": address_city,
        "Address_State": address_state,
        "Address_Nick_Name": address.get('Address_Nick_Name'),
        "Is_Default_address": address.get('Is_Default_address'),
        "Latitude": address.get('Address_Lat'),
        "Longitude": address.get('Address_Long')
    }

    # Set dates and user
    created_date = updated_date = datetime.datetime.now()

    # Insert the record
    try:
        cur.execute("""
            INSERT INTO dev.customer 
            (customer_id, customer_first_name, customer_last_name, customer_dob, customer_email_id, 
            customer_mobile_no, is_email_id_verified, is_phone_no_verified, customer_address, 
            created_on, created_by, updated_on, updated_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            user_id, first_name, last_name, dob, email, phone, is_email_verified, 
            is_phone_verified, json.dumps([address_json]), created_date, created_by, 
            updated_date, updated_by
        ))

        conn.commit()
        return user_id  # Return customer_id for reference

    except Exception as e:
        conn.rollback()
        return f"Failure: {str(e)}"

    finally:
        cur.close()

# API endpoint to add a new customer
@app.route('/add_customer', methods=['POST'])
def api_add_customer():
    conn = connect_db()
    if not conn:
        return jsonify({"status": "failure", "message": "Database connection error"}), 500

    # Get data from request
    data = request.json

    # Call add_customer function
    result = add_customer(conn, data)

    conn.close()

    if result.startswith("Failure"):
        return jsonify({"status": "failure", "message": result}), 400
    else:
        return jsonify({"status": "success", "message": "Customer added successfully", "customer_id": result}), 201

# API endpoint to verify email
@app.route('/verify_email', methods=['POST'])
def verify_email():
    conn = connect_db()
    if not conn:
        return jsonify({"status": "failure", "message": "Database connection error"}), 500

    data = request.json
    email = data.get('email')
    sysuser = data.get('updated_by', 'System')

    if not email:
        return jsonify({"status": "failure", "message": "Email is required"}), 400

    cur = conn.cursor()

    # Check if the email exists
    cur.execute('SELECT customer_id FROM dev.customer WHERE customer_email_id = %s', (email,))
    result = cur.fetchone()

    if result is None:
        conn.close()
        return jsonify({"status": "failure", "message": "Invalid Email"}), 400

    customer_id = result[0]
    
    # Update email verified column and metadata
    updated_date = datetime.datetime.now()

    try:
        cur.execute("""
            UPDATE dev.customer
            SET is_email_id_verified = %s, updated_on = %s, updated_by = %s
            WHERE customer_id = %s
        """, ('Y', updated_date, sysuser, customer_id))

        conn.commit()
        return jsonify({"status": "success", "message": "Email verification updated successfully"}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"status": "failure", "message": f"Failure: {str(e)}"}), 500

    finally:
        cur.close()
        conn.close()

# API endpoint to verify phone number
@app.route('/verify_phone', methods=['POST'])
def verify_phone():
    conn = connect_db()
    if not conn:
        return jsonify({"status": "failure", "message": "Database connection error"}), 500

    data = request.json
    email = data.get('email')
    phone = data.get('phone')
    sysuser = data.get('updated_by', 'System')

    if not email:
        return jsonify({"status": "failure", "message": "Email is required"}), 400

    if not phone:
        return jsonify({"status": "failure", "message": "Phone number is required"}), 400

    cur = conn.cursor()

    # Check if the email exists
    cur.execute('SELECT customer_id, customer_mobile_no FROM dev.customer WHERE customer_email_id = %s', (email,))
    result = cur.fetchone()

    if result is None:
        conn.close()
        return jsonify({"status": "failure", "message": "Invalid Email"}), 400

    customer_id = result[0]
    existing_phone = result[1]

    # Check if the provided phone number matches the existing one
    if phone != existing_phone:
        conn.close()
        return jsonify({"status": "failure", "message": "Invalid Phone_No"}), 400

    # Update phone verified column and metadata
    updated_date = datetime.datetime.now()

    try:
        cur.execute("""
            UPDATE dev.customer
            SET is_phone_no_verified = %s, updated_on = %s, updated_by = %s
            WHERE customer_id = %s
        """, ('Y', updated_date, sysuser, customer_id))

        conn.commit()
        return jsonify({"status": "success", "message": "Phone verification updated successfully"}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"status": "failure", "message": f"Failure: {str(e)}"}), 500

    finally:
        cur.close()
        conn.close()

# API endpoint to add an address
@app.route('/add_address', methods=['POST'])
def add_address():
    conn = connect_db()
    if not conn:
        return jsonify({"status": "failure", "message": "Database connection error"}), 500

    data = request.json
    email = data.get('email')
    address = data.get('address', {})
    sysuser = data.get('updated_by', 'System')

    if not email:
        return jsonify({"status": "failure", "message": "Email is required"}), 400

    cur = conn.cursor()

    # Check if the email exists
    cur.execute('SELECT customer_id, customer_address FROM dev.customer WHERE customer_email_id = %s', (email,))
    result = cur.fetchone()

    if result is None:
        conn.close()
        return jsonify({"status": "failure", "message": "Invalid Email"}), 400

    customer_id = result[0]
    existing_addresses = result[1]

    # If `customer_address` is a string, parse it as JSON
    if isinstance(existing_addresses, str):
        existing_addresses = json.loads(existing_addresses)
    elif existing_addresses is None:
        existing_addresses = []

    # Check the number of addresses for the customer
    if len(existing_addresses) >= 5:
        conn.close()
        return jsonify({"status": "failure", "message": "Maximum of 5 addresses allowed"}), 400

    # Check if address Nick name exists
    address_nick_name = address.get('Address_Nick_Name')
    if any(addr.get('Address_Nick_Name') == address_nick_name for addr in existing_addresses):
        conn.close()
        return jsonify({"status": "failure", "message": "Address nickname already exists"}), 400

    # Validate pincode
    address_pincode = address.get('Address_Pincode')
    cur.execute("""
        SELECT "Division Name", "Region Name", "Circle Name", "statename"
        FROM dev.pincode 
        WHERE pincode = %s
    """, (address_pincode,))
    
    pincode_data = cur.fetchone()

    if pincode_data is None:
        conn.close()
        return jsonify({"status": "failure", "message": "Invalid pincode. Please enter a valid pincode."}), 400

    # Extract details from pincode data
    division_name, region_name, circle_name, state_name = pincode_data

    # Populate address details
    new_address = {
        "Circle_Name": circle_name,
        "Region_Name": region_name,
        "Pincode": address_pincode,
        "District": address.get('Address_City'),  # Assuming District = City
        "StateName": state_name,
        "Address_Line_1": address.get('Address_Line_1'),
        "Address_Line_2": address.get('Address_Line_2'),
        "Address_City": address.get('Address_City'),
        "Address_State": address.get('Address_State'),
        "Address_Nick_Name": address_nick_name,
        "Is_Default_address": address.get('Is_Default_address'),
        "Latitude": address.get('Address_Lat'),
        "Longitude": address.get('Address_Long')
    }

    # Add new address to the list
    existing_addresses.append(new_address)

    # Update the customer record
    updated_date = datetime.datetime.now()

    try:
        cur.execute("""
            UPDATE dev.customer
            SET customer_address = %s, updated_on = %s, updated_by = %s
            WHERE customer_id = %s
        """, (json.dumps(existing_addresses), updated_date, sysuser, customer_id))

        conn.commit()
        return jsonify({"status": "success", "message": "Address added successfully"}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"status": "failure", "message": f"Failure: {str(e)}"}), 500

    finally:
        cur.close()
        conn.close()

# API endpoint to delete an address
@app.route('/delete_address', methods=['DELETE'])
def delete_address():
    conn = connect_db()
    if not conn:
        return jsonify({"status": "failure", "message": "Database connection error"}), 500

    data = request.json
    email = data.get('email')
    address_nick_name = data.get('address_nick_name')
    sysuser = data.get('updated_by', 'System')

    if not email:
        return jsonify({"status": "failure", "message": "Email is required"}), 400

    if not address_nick_name:
        return jsonify({"status": "failure", "message": "Address nickname is required"}), 400

    cur = conn.cursor()

    try:
        # Check if the email exists
        cur.execute('SELECT customer_id, customer_address FROM dev.customer WHERE customer_email_id = %s', (email,))
        result = cur.fetchone()

        if result is None:
            return jsonify({"status": "failure", "message": "Invalid Email"}), 400

        customer_id = result[0]
        existing_addresses = result[1]

        # If `customer_address` is a string, parse it as JSON
        if isinstance(existing_addresses, str):
            existing_addresses = json.loads(existing_addresses)
        elif existing_addresses is None:
            existing_addresses = []

        # Filter out the address to be deleted
        updated_addresses = [addr for addr in existing_addresses if addr.get('Address_Nick_Name') != address_nick_name]

        if len(updated_addresses) == len(existing_addresses):
            return jsonify({"status": "failure", "message": "Address nickname not found"}), 400

        # Update the customer record
        updated_date = datetime.datetime.now()

        cur.execute("""
            UPDATE dev.customer
            SET customer_address = %s, updated_on = %s, updated_by = %s
            WHERE customer_id = %s
        """, (json.dumps(updated_addresses), updated_date, sysuser, customer_id))

        conn.commit()
        return jsonify({"status": "success", "message": "Address deleted successfully"}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"status": "failure", "message": f"Failure: {str(e)}"}), 500

    finally:
        cur.close()
        conn.close()

# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True)
