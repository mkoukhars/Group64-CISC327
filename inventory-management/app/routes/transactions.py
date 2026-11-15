
from flask import Blueprint, jsonify, request

from app import store
from app.models.transaction import Transaction
import notification_service

transactions_bp = Blueprint("transactions", __name__, url_prefix="/transactions")

STAFF_EMAIL = "inventory-manager@example.com"

# ... list_transactions unchanged ...
@transactions_bp.route("", methods=["GET"])
def list_transactions():
    results = list(store.transactions.values())

    product_id = request.args.get("product_id", type=int)
    supplier_id = request.args.get("supplier_id", type=int)

    if product_id is not None:
        results = [
            t for t in results
            if t.product_id == product_id
        ]

    if supplier_id is not None:
        results = [
            t for t in results
            if t.supplier_id == supplier_id
        ]

    return jsonify([t.to_dict() for t in results])

@transactions_bp.route("", methods=["POST"])
def create_transaction():
    data = request.get_json()
    product = store.products.get(data["product_id"])
    if product is None:
        return jsonify({"error": "Product not found"}), 404

    quantity = data["quantity"]
    tx_type = data["type"]

    if tx_type == "IN":
        product.quantity_on_hand += quantity
    elif tx_type == "OUT":
        product.quantity_on_hand -= quantity
    else:
        return jsonify({"error": "type must be IN or OUT"}), 400

    transaction_id = store.next_id("transaction")
    transaction = Transaction(
        id=transaction_id,
        product_id=data["product_id"],
        supplier_id=data.get("supplier_id"),
        type=tx_type,
        quantity=quantity,
    )
    store.transactions[transaction_id] = transaction

    if tx_type == "OUT" and product.quantity_on_hand <= product.reorder_level:
        recipient = STAFF_EMAIL
        supplier = store.suppliers.get(transaction.supplier_id)
        if supplier is not None and supplier.contact_email:
            recipient = supplier.contact_email

        sent = notification_service.send_notification(
            recipient,
            f"Low stock: {product.name}",
            notification_service.build_low_stock_message(
                product.name, product.quantity_on_hand, product.reorder_level),
        )
        if not sent:
            # Failure policy: the transaction still succeeds; we just warn.
            print(f"Warning: low-stock alert for {product.name} could not be sent.")

    return jsonify(transaction.to_dict()), 201
