def test_register(client, test_user):
    response = client.post("/api/v1/auth/register", json=test_user)
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()

def test_login(client, test_user):
    # Register first
    client.post("/api/v1/auth/register", json=test_user)
    
    # Login
    response = client.post("/api/v1/auth/login", json={
        "email": test_user["email"],
        "password": test_user["password"]
    })
    assert response.status_code == 200
    assert "access_token" in response.json()