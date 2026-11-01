
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

# ---------------------------------------------------------------------------
# Feature 6: View stock level
# ---------------------------------------------------------------------------

def test_stock_level_reflects_transactions_reaches_zero_and_404_for_unknown(client):
    p = make_product(client, quantity_on_hand=10)
    url = f"/products/{p['id']}/stock-level"

    resp = client.get(url)
    assert resp.status_code == 200
    assert resp.get_json() == {"product_id": p["id"], "quantity_on_hand": 10}

    # Chained workflow: 10 + 5 - 3 = 12
    record_tx(client, p["id"], "IN", 5)
    record_tx(client, p["id"], "OUT", 3)
    assert client.get(url).get_json()["quantity_on_hand"] == 12

    # Boundary: exactly zero
    record_tx(client, p["id"], "OUT", 12)
    assert client.get(url).get_json()["quantity_on_hand"] == 0

    missing = client.get("/products/999/stock-level")
    assert missing.status_code == 404
    assert missing.get_json() == {"error": "Product not found"}


# ---------------------------------------------------------------------------
# Feature 7: List low-stock products
# ---------------------------------------------------------------------------

def test_low_stock_list_boundary_and_changes_after_transactions(client):
    assert client.get("/products/low-stock").get_json() == []

    below = make_product(client, name="Below", sku="B", quantity_on_hand=2, reorder_level=5)
    at = make_product(client, name="At", sku="A", quantity_on_hand=5, reorder_level=5)
    above = make_product(client, name="Above", sku="C", quantity_on_hand=6, reorder_level=5)

    # At-or-below the threshold is flagged; above is not
    ids = {p["id"] for p in client.get("/products/low-stock").get_json()}
    assert ids == {below["id"], at["id"]}

    # Selling the "above" product down to its threshold flags it (6 -> 4)
    record_tx(client, above["id"], "OUT", 2)
    ids = {p["id"] for p in client.get("/products/low-stock").get_json()}
    assert above["id"] in ids

    # Restocking removes a product from the list (2 -> 22)
    record_tx(client, below["id"], "IN", 20)
    ids = {p["id"] for p in client.get("/products/low-stock").get_json()}
    assert below["id"] not in ids


# ---------------------------------------------------------------------------
# Feature 8: List / filter transactions
# ---------------------------------------------------------------------------

def test_list_transactions_returns_dated_records_and_filters_by_supplier_and_product(client):
    assert client.get("/transactions").get_json() == []

    supplier = make_supplier(client)
    a = make_product(client, name="A", sku="A")
    b = make_product(client, name="B", sku="B")
    record_tx(client, a["id"], "IN", 5, supplier_id=supplier["id"])
    record_tx(client, b["id"], "IN", 9)

    # Every movement is listed with type, quantity and a date (R5)
    txs = client.get("/transactions").get_json()
    assert len(txs) == 2
    assert [t["quantity"] for t in txs] == [5, 9]
    assert all(t["transaction_date"] for t in txs)

    # Supplier filter works
    by_supplier = client.get(f"/transactions?supplier_id={supplier['id']}").get_json()
    assert len(by_supplier) == 1
    assert by_supplier[0]["product_id"] == a["id"]

    # EXPECTED TO FAIL: README documents ?product_id=, but the code compares it
    # with t.supplier_id, so this returns [] instead of product B's transaction.
    by_product = client.get(f"/transactions?product_id={b['id']}").get_json()
    assert len(by_product) == 1
    assert by_product[0]["product_id"] == b["id"]


# ---------------------------------------------------------------------------
# Feature 9: Manage products via web UI
# ---------------------------------------------------------------------------

def test_ui_products_add_and_delete_forms_update_store_and_page(client):
    assert client.get("/ui/products").status_code == 200

    resp = client.post("/ui/products", data={
        "name": "UI Widget", "sku": "UI-1", "unit_price": "3.50", "quantity_on_hand": "8",
    })
    assert resp.status_code == 302  # redirect back to the products page

    products = client.get("/products").get_json()
    assert len(products) == 1
    assert products[0]["name"] == "UI Widget"
    assert products[0]["unit_price"] == 3.5
    assert products[0]["quantity_on_hand"] == 8
    assert products[0]["reorder_level"] == 0  # the form has no reorder_level field
    assert b"UI Widget" in client.get("/ui/products").data

    # Delete via the UI
    pid = products[0]["id"]
    assert client.post(f"/ui/products/{pid}/delete").status_code == 302
    assert client.get(f"/products/{pid}").status_code == 404
    assert b"UI Widget" not in client.get("/ui/products").data

    # Deleting a nonexistent product does not crash
    assert client.post("/ui/products/999/delete").status_code == 302


# ---------------------------------------------------------------------------
# Feature 10: Manage suppliers via web UI
# ---------------------------------------------------------------------------

def test_ui_suppliers_add_and_delete_forms_update_store_and_page(client):
    assert client.get("/ui/suppliers").status_code == 200

    resp = client.post("/ui/suppliers", data={
        "name": "UI Supplier", "contact_email": "ui@test.com",
    })
    assert resp.status_code == 302

    suppliers = client.get("/suppliers").get_json()
    assert len(suppliers) == 1
    assert suppliers[0]["name"] == "UI Supplier"
    assert suppliers[0]["contact_email"] == "ui@test.com"

    # Contact info is visible to staff on the page (R6)
    page = client.get("/ui/suppliers").data
    assert b"UI Supplier" in page
    assert b"ui@test.com" in page

    # Delete via the UI
    sid = suppliers[0]["id"]
    assert client.post(f"/ui/suppliers/{sid}/delete").status_code == 302
    assert client.get(f"/suppliers/{sid}").status_code == 404
    assert client.get("/suppliers").get_json() == []

    # Deleting a nonexistent supplier does not crash
    assert client.post("/ui/suppliers/999/delete").status_code == 302


# ---------------------------------------------------------------------------
# Feature 11: List suppliers
# ---------------------------------------------------------------------------

def test_list_suppliers_returns_contact_details_and_excludes_deleted(client):
    assert client.get("/suppliers").get_json() == []

    keep = make_supplier(client, "Acme", "acme@test.com")
    drop = make_supplier(client, "Globex", "globex@test.com")

    resp = client.get("/suppliers")
    assert resp.status_code == 200
    suppliers = resp.get_json()
    assert len(suppliers) == 2
    by_name = {s["name"]: s for s in suppliers}
    assert by_name["Acme"]["contact_email"] == "acme@test.com"
    assert by_name["Globex"]["contact_email"] == "globex@test.com"
    assert all(set(s) == {"id", "name", "contact_email"} for s in suppliers)

    assert client.delete(f"/suppliers/{drop['id']}").status_code == 204
    assert [s["id"] for s in client.get("/suppliers").get_json()] == [keep["id"]]