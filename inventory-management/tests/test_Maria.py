# F12–F16: Supplier tests
def test_create_supplier(client):
    """A supplier can be created and its details are returned."""

    payload = {
        "name": "ABC Supplies",
        "contact_email": "abc@example.com"
    }

    response = client.post("/suppliers", json=payload)

    assert response.status_code == 201

    supplier = response.get_json()

    assert supplier["name"] == "ABC Supplies"
    assert supplier["contact_email"] == "abc@example.com"
    assert "id" in supplier


def test_get_one_supplier(client):
    """A supplier that has been created can be retrieved by its ID."""

    payload = {
        "name": "ABC Supplies",
        "contact_email": "abc@example.com"
    }

    create_response = client.post("/suppliers", json=payload)
    supplier_id = create_response.get_json()["id"]

    response = client.get(f"/suppliers/{supplier_id}")

    assert response.status_code == 200

    supplier = response.get_json()

    assert supplier["id"] == supplier_id
    assert supplier["name"] == "ABC Supplies"
    assert supplier["contact_email"] == "abc@example.com"


def test_update_supplier(client):
    """A supplier's name and contact email can be updated."""

    payload = {
        "name": "ABC Supplies",
        "contact_email": "abc@example.com"
    }

    create_response = client.post("/suppliers", json=payload)
    supplier_id = create_response.get_json()["id"]

    update_payload = {
        "name": "ABC Updated Supplies",
        "contact_email": "updated@example.com"
    }

    update_response = client.put(
        f"/suppliers/{supplier_id}",
        json=update_payload
    )

    assert update_response.status_code == 200

    supplier = update_response.get_json()

    assert supplier["name"] == "ABC Updated Supplies"
    assert supplier["contact_email"] == "updated@example.com"

    get_response = client.get(f"/suppliers/{supplier_id}")

    assert get_response.status_code == 200
    assert get_response.get_json()["name"] == "ABC Updated Supplies"
    assert get_response.get_json()["contact_email"] == "updated@example.com"


def test_delete_supplier(client):
    """A supplier can be deleted and can no longer be retrieved."""

    payload = {
        "name": "ABC Supplies",
        "contact_email": "abc@example.com"
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
        "name": "ABC Supplies",
        "contact_email": "abc@example.com"
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


