
def make_test_product(client, **overrides):
    payload = {"name": "Needoh", "sku": "NEEDOH-TEST", "unit_price": 25.00, "quantity_on_hand": 20, "reorder_level": 5}
    payload.update(overrides)
    resp = client.post("/products", json=payload)
    assert resp.status_code == 201
    return resp.get_json()

def stock(client, product_id):
    return client.get(f"/products/{product_id}").get_json()["quantity_on_hand"]

# Error path

def test_transaction_unknown_product_404(client):
    resp = client.post("/transactions", json={"product_id": 999, "type": "OUT", "quantity": 1})
    assert resp.status_code == 404
    assert resp.get_json() == {"error": "Product not found"}
    assert client.get("/transactions").get_json() == []

def test_transaction_invalid_type_400(client):
    p = make_test_product(client, quantity_on_hand=10)
    resp = client.post("/transactions", json={"product_id": p["id"], "type": "SIDEWAYS", "quantity": 3})
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "type must be IN or OUT"}
    assert stock(client, p["id"]) == 10

# normal path

def test_transaction_increases_stock(client):
    p = make_test_product(client, quantity_on_hand=10)
    resp = client.post("/transactions", json={"product_id": p["id"], "type": "IN", "quantity": 4})
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["type"] == "IN" and body["quantity"] == 4
    assert stock(client, p["id"]) == 14
    assert len(client.get("/transactions").get_json()) == 1

def test_transaction_decreases_stock(client):
    p = make_test_product(client, quantity_on_hand=10)
    resp = client.post("/transactions", json={"product_id": p["id"], "type": "OUT", "quantity": 3})
    assert resp.status_code == 201
    assert stock(client, p["id"]) == 7

def test_transaction_decreases_stock_to_zero(client):
    p = make_test_product(client, quantity_on_hand=5, reorder_level=0)
    resp = client.post("/transactions", json={"product_id": p["id"], "type": "OUT", "quantity": 5})
    assert resp.status_code == 201
    assert stock(client, p["id"]) == 0