from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
import uuid
from sqlalchemy.dialects.postgresql import UUID
import re
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://pawan:pawan@139.59.77.208:5432/runpharmacy'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Customer(db.Model):
    __tablename__ = 'customer'
    __table_args__ = {'schema': 'dev'}

    customer_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_first_name = db.Column(db.String(100), nullable=False)
    customer_last_name = db.Column(db.String(100), nullable=False)
    customer_dob = db.Column(db.Date, nullable=False)
    customer_email_id = db.Column(db.String(100), unique=True, nullable=False)
    customer_mobile_no = db.Column(db.String(10), unique=True, nullable=False)
    is_email_id_verified = db.Column(db.String(1), nullable=False)
    is_phone_no_verified = db.Column(db.String(1), nullable=False)
    customer_address = db.Column(db.JSON, nullable=False)
    created_on = db.Column(db.TIMESTAMP(timezone=True), default=db.func.now())
    created_by = db.Column(db.String(100))
    updated_on = db.Column(db.TIMESTAMP(timezone=True), default=db.func.now(), onupdate=db.func.now())
    updated_by = db.Column(db.String(100))
    customer_password = db.Column(db.String(100), nullable=True)

@app.route('/customers', methods=['GET'])
def get_customers():
    customers = Customer.query.all()
    customer_list = [
        {
            'customer_id': str(customer.customer_id),
            'customer_first_name': customer.customer_first_name,
            'customer_last_name': customer.customer_last_name,
            'customer_dob': customer.customer_dob.isoformat(),
            'customer_email_id': customer.customer_email_id,
            'customer_mobile_no': customer.customer_mobile_no,
            'is_email_id_verified': customer.is_email_id_verified,
            'is_phone_no_verified': customer.is_phone_no_verified,
            'customer_address': customer.customer_address,
            'created_on': customer.created_on.isoformat(),
            'created_by': customer.created_by,
            'updated_on': customer.updated_on.isoformat(),
            'updated_by': customer.updated_by,
            'customer_password': customer.customer_password
        }
        for customer in customers
    ]
    return jsonify({'customers': customer_list})

@app.route('/customers/<uuid:customer_id>', methods=['GET'])
def get_customer(customer_id):
    customer = Customer.query.get(customer_id)
    if customer:
        return jsonify({
            'customer_id': str(customer.customer_id),
            'customer_first_name': customer.customer_first_name,
            'customer_last_name': customer.customer_last_name,
            'customer_dob': customer.customer_dob.isoformat(),
            'customer_email_id': customer.customer_email_id,
            'customer_mobile_no': customer.customer_mobile_no,
            'is_email_id_verified': customer.is_email_id_verified,
            'is_phone_no_verified': customer.is_phone_no_verified,
            'customer_address': customer.customer_address,
            'created_on': customer.created_on.isoformat(),
            'created_by': customer.created_by,
            'updated_on': customer.updated_on.isoformat(),
            'updated_by': customer.updated_by,
            'customer_password': customer.customer_password
        })
    else:
        return jsonify({'error': 'Customer not found'}), 404

@app.route('/customers', methods=['POST'])
def create_customer():
    if request.content_type != 'application/json':
        return jsonify({'error': 'Content-Type must be application/json'}), 415

    data = request.get_json()
    required_fields = [
        'customer_first_name', 'customer_last_name', 'customer_dob',
        'customer_email_id', 'customer_mobile_no',
        'is_email_id_verified', 'is_phone_no_verified', 'customer_address'
    ]

    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400

    try:
        customer_dob = datetime.strptime(data['customer_dob'], '%Y-%m-%d').date()
        if customer_dob > datetime.now().date() - timedelta(days=16*365):
            return jsonify({'error': 'Customer must be at least 16 years old'}), 400

        if not re.match(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$', data['customer_email_id']):
            return jsonify({'error': 'Invalid email format'}), 400

        if not re.match(r'^[0-9]{10}$', data['customer_mobile_no']):
            return jsonify({'error': 'Mobile number must be 10 digits long'}), 400

        if data['is_email_id_verified'] not in ['Y', 'N']:
            return jsonify({'error': 'is_email_id_verified must be either "Y" or "N"'}), 400

        if data['is_phone_no_verified'] not in ['Y', 'N']:
            return jsonify({'error': 'is_phone_no_verified must be either "Y" or "N"'}), 400

        # Address validation: Limit to 5 elements
        if not isinstance(data['customer_address'], list) or len(data['customer_address']) > 5:
            return jsonify({'error': 'Customer address should not have more than 5 elements'}), 400

        new_customer = Customer(
            customer_first_name=data['customer_first_name'],
            customer_last_name=data['customer_last_name'],
            customer_dob=customer_dob,
            customer_email_id=data['customer_email_id'],
            customer_mobile_no=data['customer_mobile_no'],
            is_email_id_verified=data['is_email_id_verified'],
            is_phone_no_verified=data['is_phone_no_verified'],
            customer_address=data['customer_address'],
            created_by=data.get('created_by'),
            updated_by=data.get('updated_by'),
            customer_password=data.get('customer_password')
        )
        db.session.add(new_customer)
        db.session.commit()
        return jsonify({'message': 'Customer created successfully'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/customers/<uuid:customer_id>', methods=['PUT'])
def update_customer(customer_id):
    if request.content_type != 'application/json':
        return jsonify({'error': 'Content-Type must be application/json'}), 415

    data = request.get_json()
    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({'error': 'Customer not found'}), 404

    # Update fields if provided
    customer.customer_first_name = data.get('customer_first_name', customer.customer_first_name)
    customer.customer_last_name = data.get('customer_last_name', customer.customer_last_name)
    customer.customer_dob = data.get('customer_dob', customer.customer_dob)
    customer.customer_email_id = data.get('customer_email_id', customer.customer_email_id)
    customer.customer_mobile_no = data.get('customer_mobile_no', customer.customer_mobile_no)
    customer.is_email_id_verified = data.get('is_email_id_verified', customer.is_email_id_verified)
    customer.is_phone_no_verified = data.get('is_phone_no_verified', customer.is_phone_no_verified)
    customer.customer_address = data.get('customer_address', customer.customer_address)
    customer.created_by = data.get('created_by', customer.created_by)
    customer.updated_by = data.get('updated_by', customer.updated_by)
    customer.customer_password = data.get('customer_password', customer.customer_password)
    customer.updated_on = datetime.now()

    db.session.commit()
    return jsonify({'message': 'Customer updated successfully'}), 200

@app.route('/customers/<uuid:customer_id>', methods=['DELETE'])
def delete_customer(customer_id):
    customer = Customer.query.get(customer_id)
    if customer:
        db.session.delete(customer)
        db.session.commit()
        return jsonify({'message': 'Customer deleted successfully'}), 200
    else:
        return jsonify({'error': 'Customer not found'}), 404

if __name__ == '__main__':
    app.run(debug=True)
