from unittest.mock import patch
from app.routes.transactions import STAFF_EMAIL

import notification_service

def make_test_product(client, **overrides):
    """Create a product for notification integration tests."""
    payload = {
        "name": "Needoh",
        "sku": "NEEDOH-TEST",
        "unit_price": 25.00,
        "quantity_on_hand": 20,
        "reorder_level": 5
    }
    payload.update(overrides)
    resp = client.post("/products", json=payload)
    assert resp.status_code == 201
    return resp.get_json()

def make_supplier(client, name="Meow Supplies", contact_email="contact@meowsupplies.com"):
    """Create a supplier for notification integration tests."""
    resp = client.post("/suppliers", json={"name": name, "contact_email": contact_email})
    assert resp.status_code == 201
    return resp.get_json()

def record_tx(client, product_id, tx_type, quantity,supplier_id=None):
    """Record a transaction for notification integration tests."""
    body = {
        "product_id": product_id,
        "type": tx_type,
        "quantity": quantity
    }
    if supplier_id is not None:
        body["supplier_id"] = supplier_id
    resp = client.post("/transactions", json=body)
    assert resp.status_code == 201 
    return resp.get_json()

PATCH_TARGET = "app.routes.transactions.notification_service.send_notification"

#STUB: send_notification always returns True: success path
def test_low_stock_alert_notification_success(client):
    p = make_test_product(client, name="Needoh", sku="NEEDOH-TEST", quantity_on_hand=10, reorder_level=5)

    with patch(PATCH_TARGET, return_value=True) as mock_send:
        tx = record_tx(client, p["id"],"OUT", 6)

    assert tx["quantity"] == 6
    assert client.get(f"/products/{p['id']}").get_json()["quantity_on_hand"] == 4

    mock_send.assert_called_once_with(
        STAFF_EMAIL,
        "Low stock: Needoh",
        notification_service.build_low_stock_message("Needoh", 4, 5)
    )

#MOCK 
def test_low_stock_alert_goes_to_supplier_email_when_supplier_given(client):
    supplier = make_supplier(client, "Meow Supplies", "contact@meowsupplies.com")
    p = make_test_product(client, name="Needoh", sku="NEEDOH-TEST",
                     quantity_on_hand=8, reorder_level=5)

    with patch(PATCH_TARGET, return_value=True) as mock_send:
        tx = record_tx(client, p["id"], "OUT", 4, supplier_id=supplier["id"])  # 8 -> 4

    assert tx["quantity"] == 4
    assert client.get(f"/products/{p['id']}").get_json()["quantity_on_hand"] == 4

    mock_send.assert_called_once_with(
        "contact@meowsupplies.com",
        "Low stock: Needoh",
        notification_service.build_low_stock_message("Needoh", 4, 5),
    )