import requests
import json

def test_backend():
    base_url = "https://playto-community-backend-production.up.railway.app"
    
    # Test health endpoint
    try:
        response = requests.get(f"{base_url}/api/health/", timeout=10)
        print(f"Health check: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"Health check failed: {e}")
    
    # Test registration endpoint
    try:
        test_user = {
            "username": "testuser123",
            "email": "test@example.com",
            "password": "testpass123",
            "first_name": "Test",
            "last_name": "User"
        }
        
        response = requests.post(
            f"{base_url}/api/auth/register/", 
            json=test_user,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        print(f"Registration test: {response.status_code}")
        if response.status_code != 201:
            print(f"Registration error: {response.text}")
        else:
            print("Registration successful!")
            
    except Exception as e:
        print(f"Registration test failed: {e}")

if __name__ == "__main__":
    test_backend()