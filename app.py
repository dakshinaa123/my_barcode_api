from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import logging

# 1. Configure Flask to Use SQLAlchemy
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///products.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 2. Define Database Models
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    barcode = db.Column(db.String(12), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "barcode": self.barcode,
            "name": self.name,
            "price": self.price
        }

# 3. Initialize the Database
with app.app_context():
    db.create_all()

# 4. Regular Product Addition (Unprotected)
@app.route('/api/products', methods=['POST'], endpoint='create_product')
def add_product():
    data = request.json
    if not data.get('barcode') or not data.get('name') or not data.get('price'):
        return jsonify({"error": "Missing required fields"}), 400

    product = Product(barcode=data['barcode'], name=data['name'], price=data['price'])
    db.session.add(product)
    db.session.commit()
    return jsonify(product.to_dict()), 201

# 5. JWT Protected Product Addition
@app.route('/api/products/protected', methods=['POST'])
@jwt_required()
def add_product_protected():
    current_user = get_jwt_identity()
    if current_user['username'] != 'admin':
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    product = Product(barcode=data['barcode'], name=data['name'], price=data['price'])
    db.session.add(product)
    db.session.commit()
    return jsonify(product.to_dict()), 201

# 6. Other CRUD Operations
@app.route('/api/products/<int:id>', methods=['GET'])
def get_product(id):
    product = Product.query.get_or_404(id)
    return jsonify(product.to_dict())

@app.route('/api/products/<int:id>', methods=['PUT'])
def update_product(id):
    product = Product.query.get_or_404(id)
    data = request.json
    product.name = data.get('name', product.name)
    product.price = data.get('price', product.price)
    db.session.commit()
    return jsonify(product.to_dict())

@app.route('/api/products/<int:id>', methods=['DELETE'])
def delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    return jsonify({"message": "Product deleted"})

# 7. Search and Pagination
@app.route('/api/products/search', methods=['GET'])
def search_products():
    query = request.args.get('query')
    products = Product.query.filter(Product.name.contains(query) | Product.barcode.contains(query)).all()
    return jsonify([product.to_dict() for product in products])

@app.route('/api/products', methods=['GET'])
def get_products():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    products = Product.query.paginate(page, per_page, error_out=False)
    return jsonify({
        "products": [product.to_dict() for product in products.items],
        "total": products.total,
        "pages": products.pages,
        "current_page": products.page
    })

# 8. Handle Complex Business Rules
@app.route('/api/products/sell/<int:id>', methods=['POST'])
def sell_product(id):
    product = Product.query.get_or_404(id)
    quantity = request.json.get('quantity', 1)
    if product.stock < quantity:
        return jsonify({"error": "Not enough stock"}), 400
    product.stock -= quantity
    db.session.commit()
    return jsonify(product.to_dict())

# 9. Error Handling and Logging
logging.basicConfig(level=logging.ERROR)

@app.errorhandler(Exception)
def handle_exception(e):
    app.logger.error(f"Error occurred: {e}")
    return jsonify({"error": "An error occurred"}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Resource not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

# 10. Configure JWT
app.config['JWT_SECRET_KEY'] = 'your_jwt_secret_key'
jwt = JWTManager(app)

# 11. User Login
@app.route('/login', methods=['POST'])
def login():
    username = request.json.get('username')
    password = request.json.get('password')

    if username == 'admin' and password == 'password':
        access_token = create_access_token(identity={'username': username})
        return jsonify(access_token=access_token)
    return jsonify({"error": "Invalid credentials"}), 401

# 12. Run the Flask Application
if __name__ == '__main__':
    app.run(debug=True)
