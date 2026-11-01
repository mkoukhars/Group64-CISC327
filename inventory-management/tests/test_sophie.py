
#Sophie Liang Test File

# helper functions to help with functions

def make_product(client, **overrides):
    payload = {
        "name": "Widget",
        "sku": "W-1",
        "unit_price": 9.99,
        "quantity_on_hand": 10,
        "reorder_level": 5,
    }
    payload.update(overrides)
    resp = client.post("/products", json=payload)
    assert resp.status_code == 201
    return resp.get_json()


def make_supplier(client, name="Acme", email="acme@test.com"):
    resp = client.post("/suppliers", json={"name": name, "contact_email": email})
    assert resp.status_code == 201
    return resp.get_json()


def record_tx(client, product_id, tx_type, quantity, supplier_id=None):
    body = {"product_id": product_id, "type": tx_type, "quantity": quantity}
    if supplier_id is not None:
        body["supplier_id"] = supplier_id
    resp = client.post("/transactions", json=body)
    assert resp.status_code == 201
    return resp.get_json()


# ---------------------------------------------------------------------------
# Feature 1: List products
# ---------------------------------------------------------------------------

def test_list_products_returns_all_fields_and_excludes_deleted(client):
    # Empty store -> empty list
    assert client.get("/products").get_json() == []

    keep = make_product(client, name="Widget", sku="W-1")
    drop = make_product(client, name="Gadget", sku="G-1")

    products = client.get("/products").get_json()
    assert len(products) == 2
    for p in products:
        assert set(p) == {"id", "name", "sku", "unit_price", "quantity_on_hand", "reorder_level"}

    # A deleted product no longer appears
    client.delete(f"/products/{drop['id']}")
    ids = [p["id"] for p in client.get("/products").get_json()]
    assert ids == [keep["id"]]


# ---------------------------------------------------------------------------
# Feature 2: Create product
# ---------------------------------------------------------------------------

def test_create_product_returns_fields_applies_defaults_and_is_retrievable(client):
    resp = client.post("/products", json={
        "name": "Gadget", "sku": "G-1", "unit_price": 5,
        "quantity_on_hand": 2, "reorder_level": 5,
    })
    assert resp.status_code == 201
    created = resp.get_json()
    assert created["name"] == "Gadget"
    assert created["sku"] == "G-1"
    assert created["unit_price"] == 5
    assert created["quantity_on_hand"] == 2
    assert created["reorder_level"] == 5

    # Persistent state: a later GET returns the same data
    assert client.get(f"/products/{created['id']}").get_json() == created

    # Optional fields default to 0, and ids are unique
    bare = client.post("/products", json={"name": "Bare", "sku": "B-1"}).get_json()
    assert bare["unit_price"] == 0.0
    assert bare["quantity_on_hand"] == 0
    assert bare["reorder_level"] == 0
    assert bare["id"] != created["id"]


# ---------------------------------------------------------------------------
# Feature 3: Get one product
# ---------------------------------------------------------------------------

def test_get_product_returns_correct_one_and_404_for_unknown_id(client):
    make_product(client, name="One", sku="1")
    second = make_product(client, name="Two", sku="2", quantity_on_hand=7)

    resp = client.get(f"/products/{second['id']}")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["name"] == "Two"
    assert body["quantity_on_hand"] == 7

    missing = client.get("/products/999")
    assert missing.status_code == 404
    assert missing.get_json() == {"error": "Product not found"}


# ---------------------------------------------------------------------------
# Feature 4: Update product / correct stock count
# ---------------------------------------------------------------------------

def test_update_product_corrects_count_keeps_other_fields_and_404_for_unknown(client):
    p = make_product(client, name="Old", sku="O-1", unit_price=4.5, quantity_on_hand=15)

    # R1: correct a wrongly entered count (15 -> 12); other fields untouched
    resp = client.put(f"/products/{p['id']}", json={"quantity_on_hand": 12})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["quantity_on_hand"] == 12
    assert body["name"] == "Old"
    assert body["sku"] == "O-1"
    assert body["unit_price"] == 4.5

    # The correction persists and is visible through other endpoints
    assert client.get(f"/products/{p['id']}/stock-level").get_json()["quantity_on_hand"] == 12
    assert client.get(f"/products/{p['id']}").get_json()["quantity_on_hand"] == 12

    # Updating a product that doesn't exist
    missing = client.put("/products/999", json={"name": "Ghost"})
    assert missing.status_code == 404
    assert missing.get_json() == {"error": "Product not found"}


# ---------------------------------------------------------------------------
# Feature 5: Delete product
# ---------------------------------------------------------------------------

def test_delete_product_removes_it_and_repeat_delete_returns_404(client):
    a = make_product(client, name="A", sku="A")
    b = make_product(client, name="B", sku="B")

    resp = client.delete(f"/products/{a['id']}")
    assert resp.status_code == 204
    assert resp.data == b""

    # Gone from direct lookup and from the list; other products unaffected
    assert client.get(f"/products/{a['id']}").status_code == 404
    assert [p["id"] for p in client.get("/products").get_json()] == [b["id"]]

    # Repeated action
    again = client.delete(f"/products/{a['id']}")
    assert again.status_code == 404
    assert again.get_json() == {"error": "Product not found"}