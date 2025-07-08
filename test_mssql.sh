#!/bin/bash

# Test MS SQL connection using virtual environment

echo "Testing MS SQL Server connection..."
echo "================================="
echo ""

# Navigate to the script directory
cd "$(dirname "$0")"

# Activate virtual environment and run test
if [ -d "venv" ]; then
    echo "Using virtual environment..."
    ./venv/bin/python test_mssql_connection.py
else
    echo "No virtual environment found, using system Python..."
    python3 test_mssql_connection.py
fi