import requests
import sys

BASE_URL = "http://localhost:8000"

def test_endpoint(path, expected_status=401):
    url = f"{BASE_URL}{path}"
    try:
        response = requests.get(url)
        if response.status_code == expected_status:
            print(f"✅ {path}: {response.status_code} (Expected)")
            return True
        else:
            print(f"❌ {path}: {response.status_code} (Expected {expected_status})")
            print(f"   Response: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection refused to {BASE_URL}. Is the server running?")
        return False

def main():
    print("Testing Backend Auth Protection...")
    
    # Public endpoints
    success = True
    success &= test_endpoint("/health", 200)
    success &= test_endpoint("/", 200)
    
    # Protected endpoints
    success &= test_endpoint("/api/dag/", 401)
    success &= test_endpoint("/api/projects/", 401)
    
    if success:
        print("\nAll auth checks passed!")
        sys.exit(0)
    else:
        print("\nSome checks failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
