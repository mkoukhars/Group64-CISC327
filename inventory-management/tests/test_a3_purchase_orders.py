
def make_product(client, **overrides):
    payload = {"name": "Needoh", "sku": "NEEDOH-TEST", "unit_price": 9.99,
               "quantity_on_hand": 10, "reorder_level": 5}
    payload.update(overrides)
    resp = client.post("/products", json=payload)
    assert resp.status_code == 201
    return resp.get_json()


def make_supplier(client, name="Meow Supplies", email="contact@meowsupplies.com"):
    resp = client.post("/suppliers", json={"name": name, "contact_email": email})
    assert resp.status_code == 201
    return resp.get_json()


def make_po(client, supplier_id, product_id, quantity_ordered=50):
    resp = client.post("/purchase-orders", json={
        "supplier_id": supplier_id,
        "product_id": product_id,
        "quantity_ordered": quantity_ordered,
    })
    assert resp.status_code == 201
    return resp.get_json()


def stock(client, product_id):
    return client.get(f"/products/{product_id}").get_json()["quantity_on_hand"]


# ---- normal case ----

def test_create_and_receive_purchase_order_adds_needoh_stock_and_records_in_transaction(client):
    supplier = make_supplier(client)
    p = make_product(client, quantity_on_hand=10)
    po = make_po(client, supplier["id"], p["id"], 50)
    assert po["status"] == "pending"
    assert stock(client, p["id"]) == 10          # not received yet

    resp = client.put(f"/purchase-orders/{po['id']}/receive")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "received"
    assert stock(client, p["id"]) == 60          # 10 + 50

    txs = client.get("/transactions").get_json()
    assert len(txs) == 1
    assert txs[0]["type"] == "IN" and txs[0]["quantity"] == 50
    assert txs[0]["product_id"] == p["id"]
    assert txs[0]["supplier_id"] == supplier["id"]


# ---- error cases (lines 22, 25, 43, 51, 53) ----

def test_create_purchase_order_unknown_supplier_returns_404(client):
    p = make_product(client)
    resp = client.post("/purchase-orders", json={
        "supplier_id": 999, "product_id": p["id"], "quantity_ordered": 5})
    assert resp.status_code == 404
    assert resp.get_json() == {"error": "Supplier not found"}
    assert client.get("/purchase-orders").get_json() == []


def test_create_purchase_order_unknown_product_returns_404(client):
    supplier = make_supplier(client)
    resp = client.post("/purchase-orders", json={
        "supplier_id": supplier["id"], "product_id": 999, "quantity_ordered": 5})
    assert resp.status_code == 404
    assert resp.get_json() == {"error":"Product not found"}
    assert client.get("/purchase-orders").get_json() == []


def test_get_unknown_purchase_order_returns_404(client):
    resp = client.get("/purchase-orders/999")
    assert resp.status_code == 404
    assert resp.get_json() == {"error": "Purchase order not found"}


def test_receive_unknown_purchase_order_returns_404(client):
    resp = client.put("/purchase-orders/999/receive")
    assert resp.status_code == 404
    assert resp.get_json() == {"error": "Purchase order not found"}


def test_receive_purchase_order_twice_returns_400_and_stock_added_once(client):
    supplier = make_supplier(client)
    p = make_product(client, quantity_on_hand=10)
    po = make_po(client, supplier["id"], p["id"], 50)

    assert client.put(f"/purchase-orders/{po['id']}/receive").status_code == 200
    again = client.put(f"/purchase-orders/{po['id']}/receive")

    assert again.status_code == 400
    assert again.get_json() == {"error": "Purchase order already received"}
    assert stock(client, p["id"]) == 60                      # not 110
    assert len(client.get("/transactions").get_json()) == 1