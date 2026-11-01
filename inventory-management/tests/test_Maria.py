# F12–F16: Supplier tests
def test_create_supplier(client):
    """A supplier can be created and its details are returned."""

    payload = {
        "name": "Example Supplies",
        "contact_email": "supplies@example.com"
    }

    response = client.post("/suppliers", json=payload)

    assert response.status_code == 201

    supplier = response.get_json()

    assert supplier["name"] == "Example Supplies"
    assert supplier["contact_email"] == "supplies@example.com"
    assert "id" in supplier


def test_get_one_supplier(client):
    """A supplier that has been created can be retrieved by its ID."""

    payload = {
        "name": "Example Supplies",
        "contact_email": "supplies@example.com"
    }

    create_response = client.post("/suppliers", json=payload)
    supplier_id = create_response.get_json()["id"]

    response = client.get(f"/suppliers/{supplier_id}")

    assert response.status_code == 200

    supplier = response.get_json()

    assert supplier["id"] == supplier_id
    assert supplier["name"] == "Example Supplies"
    assert supplier["contact_email"] == "supplies@example.com"


def test_update_supplier(client):
    """A supplier's name and contact email can be updated."""

    payload = {
        "name": "Example Supplies",
        "contact_email": "supplies@example.com"
    }

    create_response = client.post("/suppliers", json=payload)
    supplier_id = create_response.get_json()["id"]

    update_payload = {
        "name": "Example Updated Supplies",
        "contact_email": "updated@example.com"
    }

    update_response = client.put(
        f"/suppliers/{supplier_id}",
        json=update_payload
    )

    assert update_response.status_code == 200

    supplier = update_response.get_json()

    assert supplier["name"] == "Example Updated Supplies"
    assert supplier["contact_email"] == "updated@example.com"

    get_response = client.get(f"/suppliers/{supplier_id}")

    assert get_response.status_code == 200
    assert get_response.get_json()["name"] == "Example Updated Supplies"
    assert get_response.get_json()["contact_email"] == "updated@example.com"


def test_delete_supplier(client):
    """A supplier can be deleted and can no longer be retrieved."""

    payload = {
        "name": "Example Supplies",
        "contact_email": "supplies@example.com"
    }

    create_response = client.post("/suppliers", json=payload)
    supplier_id = create_response.get_json()["id"]

    delete_response = client.delete(f"/suppliers/{supplier_id}")

    assert delete_response.status_code == 204

    get_response = client.get(f"/suppliers/{supplier_id}")

    assert get_response.status_code == 404


def test_list_products_received_from_supplier(client):
    """Products received from a supplier are included in that supplier's product list."""

    supplier_payload = {
        "name": "Example Supplies",
        "contact_email": "supplies@example.com"
    }

    supplier_response = client.post("/suppliers", json=supplier_payload)
    supplier_id = supplier_response.get_json()["id"]

    product_payload = {
        "name": "Keyboard",
        "sku": "KEY-001",
        "unit_price": 50.00,
        "quantity_on_hand": 10,
        "reorder_level": 2
    }

    product_response = client.post("/products", json=product_payload)
    product_id = product_response.get_json()["id"]

    transaction_payload = {
        "product_id": product_id,
        "supplier_id": supplier_id,
        "type": "IN",
        "quantity": 10
    }

    transaction_response = client.post(
        "/transactions",
        json=transaction_payload
    )

    assert transaction_response.status_code == 201

    response = client.get(f"/suppliers/{supplier_id}/products")

    assert response.status_code == 200

    products = response.get_json()

    assert len(products) == 1
    assert products[0]["id"] == product_id
    assert products[0]["name"] == "Keyboard"


# F17: Stock transaction tests

def test_record_stock_in_and_out_transactions(client):
    """IN transactions increase stock and OUT transactions decrease stock."""

    product_payload = {
        "name": "Keyboard",
        "sku": "KEY-001",
        "unit_price": 50.00,
        "quantity_on_hand": 20,
        "reorder_level": 5
    }

    product_response = client.post("/products", json=product_payload)
    product_id = product_response.get_json()["id"]

    stock_in_payload = {
        "product_id": product_id,
        "type": "IN",
        "quantity": 10
    }

    stock_in_response = client.post(
        "/transactions",
        json=stock_in_payload
    )

    assert stock_in_response.status_code == 201
    assert stock_in_response.get_json()["type"] == "IN"
    assert stock_in_response.get_json()["quantity"] == 10

    stock_response = client.get(f"/products/{product_id}/stock-level")

    assert stock_response.status_code == 200
    assert stock_response.get_json()["quantity_on_hand"] == 30

    stock_out_payload = {
        "product_id": product_id,
        "type": "OUT",
        "quantity": 5
    }

    stock_out_response = client.post(
        "/transactions",
        json=stock_out_payload
    )

    assert stock_out_response.status_code == 201
    assert stock_out_response.get_json()["type"] == "OUT"
    assert stock_out_response.get_json()["quantity"] == 5

    stock_response = client.get(f"/products/{product_id}/stock-level")

    assert stock_response.status_code == 200
    assert stock_response.get_json()["quantity_on_hand"] == 25

def test_filter_transactions_by_product_id(client):
    """Filtering transactions by product ID returns only that product's transactions."""

    supplier_one_payload = {
        "name": "Supplier One",
        "contact_email": "one@example.com"
    }

    supplier_one_response = client.post(
        "/suppliers",
        json=supplier_one_payload
    )
    supplier_one_id = supplier_one_response.get_json()["id"]

    supplier_two_payload = {
        "name": "Supplier Two",
        "contact_email": "two@example.com"
    }

    supplier_two_response = client.post(
        "/suppliers",
        json=supplier_two_payload
    )
    supplier_two_id = supplier_two_response.get_json()["id"]

    product_one_payload = {
        "name": "Keyboard",
        "sku": "KEY-001",
        "unit_price": 50.00,
        "quantity_on_hand": 10,
        "reorder_level": 2
    }

    product_one_response = client.post(
        "/products",
        json=product_one_payload
    )
    product_one_id = product_one_response.get_json()["id"]

    product_two_payload = {
        "name": "Mouse",
        "sku": "MOU-001",
        "unit_price": 25.00,
        "quantity_on_hand": 10,
        "reorder_level": 2
    }

    product_two_response = client.post(
        "/products",
        json=product_two_payload
    )
    product_two_id = product_two_response.get_json()["id"]

    first_transaction_payload = {
        "product_id": product_one_id,
        "supplier_id": supplier_two_id,
        "type": "IN",
        "quantity": 5
    }

    client.post("/transactions", json=first_transaction_payload)

    second_transaction_payload = {
        "product_id": product_two_id,
        "supplier_id": supplier_one_id,
        "type": "IN",
        "quantity": 8
    }

    client.post("/transactions", json=second_transaction_payload)

    response = client.get(f"/transactions?product_id={product_one_id}")

    assert response.status_code == 200

    transactions = response.get_json()

    assert len(transactions) == 1
    assert transactions[0]["product_id"] == product_one_id



# F18–F21: Purchase order tests
def test_create_purchase_order(client):
    """A purchase order can be created with a supplier, product and quantity."""

    supplier_payload = {
        "name": "Example Supplies",
        "contact_email": "supplies@example.com"
    }

    supplier_response = client.post("/suppliers", json=supplier_payload)
    supplier_id = supplier_response.get_json()["id"]

    product_payload = {
        "name": "Keyboard",
        "sku": "KEY-001",
        "unit_price": 50.00,
        "quantity_on_hand": 20,
        "reorder_level": 5
    }

    product_response = client.post("/products", json=product_payload)
    product_id = product_response.get_json()["id"]

    purchase_order_payload = {
        "supplier_id": supplier_id,
        "product_id": product_id,
        "quantity_ordered": 50
    }

    response = client.post(
        "/purchase-orders",
        json=purchase_order_payload
    )

    assert response.status_code == 201

    purchase_order = response.get_json()

    assert purchase_order["supplier_id"] == supplier_id
    assert purchase_order["product_id"] == product_id
    assert purchase_order["quantity_ordered"] == 50
    assert purchase_order["status"] == "pending"


def test_list_purchase_orders(client):
    """All created purchase orders are returned when requesting the purchase order list."""

    supplier_payload = {
        "name": "Example Supplies",
        "contact_email": "supplies@example.com"
    }

    supplier_response = client.post("/suppliers", json=supplier_payload)
    supplier_id = supplier_response.get_json()["id"]

    product_payload = {
        "name": "Keyboard",
        "sku": "KEY-001",
        "unit_price": 50.00,
        "quantity_on_hand": 20,
        "reorder_level": 5
    }

    product_response = client.post("/products", json=product_payload)
    product_id = product_response.get_json()["id"]

    first_order_payload = {
        "supplier_id": supplier_id,
        "product_id": product_id,
        "quantity_ordered": 10
    }

    second_order_payload = {
        "supplier_id": supplier_id,
        "product_id": product_id,
        "quantity_ordered": 20
    }

    first_response = client.post(
        "/purchase-orders",
        json=first_order_payload
    )

    second_response = client.post(
        "/purchase-orders",
        json=second_order_payload
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    response = client.get("/purchase-orders")

    assert response.status_code == 200

    purchase_orders = response.get_json()

    assert len(purchase_orders) == 2
    assert purchase_orders[0]["quantity_ordered"] == 10
    assert purchase_orders[1]["quantity_ordered"] == 20


def test_get_one_purchase_order(client):
    """A purchase order can be retrieved by its ID with its correct details."""

    supplier_payload = {
        "name": "Example Supplies",
        "contact_email": "supplies@example.com"
    }

    supplier_response = client.post("/suppliers", json=supplier_payload)
    supplier_id = supplier_response.get_json()["id"]

    product_payload = {
        "name": "Keyboard",
        "sku": "KEY-001",
        "unit_price": 50.00,
        "quantity_on_hand": 20,
        "reorder_level": 5
    }

    product_response = client.post("/products", json=product_payload)
    product_id = product_response.get_json()["id"]

    purchase_order_payload = {
        "supplier_id": supplier_id,
        "product_id": product_id,
        "quantity_ordered": 50
    }

    create_response = client.post(
        "/purchase-orders",
        json=purchase_order_payload
    )

    purchase_order_id = create_response.get_json()["id"]

    response = client.get(f"/purchase-orders/{purchase_order_id}")

    assert response.status_code == 200

    purchase_order = response.get_json()

    assert purchase_order["id"] == purchase_order_id
    assert purchase_order["supplier_id"] == supplier_id
    assert purchase_order["product_id"] == product_id
    assert purchase_order["quantity_ordered"] == 50
    assert purchase_order["status"] == "pending"


def test_receive_purchase_order(client):
    """Receiving a purchase order updates its status, records a transaction and increases stock."""

    supplier_payload = {
        "name": "Example Supplies",
        "contact_email": "supplies@example.com"
    }

    supplier_response = client.post("/suppliers", json=supplier_payload)
    supplier_id = supplier_response.get_json()["id"]

    product_payload = {
        "name": "Keyboard",
        "sku": "KEY-001",
        "unit_price": 50.00,
        "quantity_on_hand": 20,
        "reorder_level": 5
    }

    product_response = client.post("/products", json=product_payload)
    product_id = product_response.get_json()["id"]

    purchase_order_payload = {
        "supplier_id": supplier_id,
        "product_id": product_id,
        "quantity_ordered": 50
    }

    create_response = client.post(
        "/purchase-orders",
        json=purchase_order_payload
    )

    purchase_order_id = create_response.get_json()["id"]

    receive_response = client.put(
        f"/purchase-orders/{purchase_order_id}/receive"
    )

    assert receive_response.status_code == 200

    purchase_order = receive_response.get_json()

    assert purchase_order["status"] == "received"
    assert purchase_order["received_date"] is not None

    transaction_response = client.get("/transactions")

    assert transaction_response.status_code == 200

    transactions = transaction_response.get_json()

    assert len(transactions) == 1
    assert transactions[0]["product_id"] == product_id
    assert transactions[0]["supplier_id"] == supplier_id
    assert transactions[0]["type"] == "IN"
    assert transactions[0]["quantity"] == 50

    stock_response = client.get(f"/products/{product_id}/stock-level")

    assert stock_response.status_code == 200
    assert stock_response.get_json()["quantity_on_hand"] == 70

    

# F22: Web interface transaction tests
def test_record_and_view_transactions_through_web_ui(client):
    """Stock transactions can be recorded through the web UI and viewed on the transactions page."""

    supplier_payload = {
        "name": "Example Supplies",
        "contact_email": "supplies@example.com"
    }

    supplier_response = client.post("/suppliers", json=supplier_payload)
    supplier_id = supplier_response.get_json()["id"]

    product_payload = {
        "name": "Keyboard",
        "sku": "KEY-001",
        "unit_price": 50.00,
        "quantity_on_hand": 10,
        "reorder_level": 2
    }

    product_response = client.post("/products", json=product_payload)
    product_id = product_response.get_json()["id"]

    page_response = client.get("/ui/transactions")

    assert page_response.status_code == 200
    assert b"Transactions" in page_response.data

    stock_in_response = client.post(
        "/ui/transactions",
        data={
            "product_id": str(product_id),
            "type": "IN",
            "quantity": "5",
            "supplier_id": str(supplier_id)
        }
    )

    assert stock_in_response.status_code == 302

    stock_out_response = client.post(
        "/ui/transactions",
        data={
            "product_id": str(product_id),
            "type": "OUT",
            "quantity": "3"
        }
    )

    assert stock_out_response.status_code == 302

    stock_response = client.get(f"/products/{product_id}/stock-level")

    assert stock_response.status_code == 200
    assert stock_response.get_json()["quantity_on_hand"] == 12

    page_response = client.get("/ui/transactions")

    assert page_response.status_code == 200
    assert b"IN" in page_response.data
    assert b"OUT" in page_response.data
    assert b"5" in page_response.data
    assert b"3" in page_response.data
