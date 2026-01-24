#!/bin/bash

BASE_URL="http://localhost:8000"

test_endpoint() {
    path=$1
    expected_status=$2
    
    status=$(curl -o /dev/null -s -w "%{http_code}\n" "$BASE_URL$path")
    
    if [ "$status" -eq "$expected_status" ]; then
        echo "✅ $path: $status (Expected)"
        return 0
    else
        echo "❌ $path: $status (Expected $expected_status)"
        return 1
    fi
}

echo "Testing Backend Auth Protection..."

failure=0

# Public endpoints
test_endpoint "/health" 200 || failure=1
test_endpoint "/" 200 || failure=1

# Protected endpoints
test_endpoint "/api/dag/" 401 || failure=1
test_endpoint "/api/projects/" 401 || failure=1

if [ "$failure" -eq 0 ]; then
    echo -e "\nAll auth checks passed!"
    exit 0
else
    echo -e "\nSome checks failed."
    exit 1
fi
