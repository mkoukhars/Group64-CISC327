from flask import Blueprint, jsonify, request

from app import store

alerts_bp = Blueprint("alerts", __name__, url_prefix="/alerts")

VALID_SEVERITIES = {"low_stock", "out_of_stock"}


def build_alert(product):
    """Describe a product that is at or below its reorder level (same rule as /products/low-stock)."""
    return {
        "product_id": product.id,
        "name": product.name,
        "sku": product.sku,
        "quantity_on_hand": product.quantity_on_hand,
        "reorder_level": product.reorder_level,
        "shortfall": product.reorder_level - product.quantity_on_hand,
        "severity": "out_of_stock" if product.quantity_on_hand <= 0 else "low_stock",
    }


@alerts_bp.route("", methods=["GET"])
def list_alerts():
    """Return active low-stock alerts, most urgent (largest shortfall) first."""
    severity = request.args.get("severity")
    if severity is not None and severity not in VALID_SEVERITIES:
        return jsonify({"error": "severity must be low_stock or out_of_stock"}), 400

    alerts = [
        build_alert(p)
        for p in store.products.values()
        if p.quantity_on_hand <= p.reorder_level
    ]
    if severity is not None:
        alerts = [a for a in alerts if a["severity"] == severity]
    alerts.sort(key=lambda a: a["shortfall"], reverse=True)
    return jsonify(alerts)


@alerts_bp.route("/<int:product_id>", methods=["GET"])
def get_alert(product_id):
    """Return the active alert for one product, or 404 if it has none."""
    product = store.products.get(product_id)
    if product is None:
        return jsonify({"error": "Product not found"}), 404
    if product.quantity_on_hand > product.reorder_level:
        return jsonify({"error": "No active alert for this product"}), 404
    return jsonify(build_alert(product))