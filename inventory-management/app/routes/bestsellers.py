
from flask import Blueprint, jsonify, request
from datetime import date, timedelta

from app import store

bestsellers_bp = Blueprint("bestsellers", __name__, url_prefix="/reports")

@bestsellers_bp.route("/bestsellers", methods=["GET"])



def get_bestsellers():
    days = request.args.get("days", default=30, type=int) #days parameter is optional, defaulting to 30 if not provided

    if days <= 0:
        return jsonify({"error": "days must be greater than 0"}), 400

    cutoff_date = date.today() - timedelta(days=days - 1) #determines the first date to consider for sales based on the number of days specified

    sales = {}

    for transaction in store.transactions.values():
        if transaction.type != "OUT": #ignores transactions that are not sales (i.e., "OUT" transactions)
            continue

        if transaction.transaction_date < cutoff_date:
            continue

        product = store.products.get(transaction.product_id)
        if product is None:
            continue

        sales[product.id] = sales.get(product.id, 0) + transaction.quantity #units sold for each product are accumulated in the sales dictionary, with the product ID as the key and the total units sold as the value.

    results = []

    for product_id, units_sold in sales.items():
        product = store.products[product_id]

        results.append({
            "product_id": product.id,
            "product_name": product.name,
            "units_sold": units_sold,
            "sales_rate": round(units_sold / days, 2) #calculates the average daily sales rate for each product by dividing the total units sold by the number of days specified, rounding to two decimal places
        })

    results.sort(key=lambda item: item["sales_rate"], reverse=True) #puts the products with the highest sales rate at the top of the list

    return jsonify(results)
