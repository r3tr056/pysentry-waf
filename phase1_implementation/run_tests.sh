#!/bin/bash
# Phase 1 Test Runner Script

set -e

echo "======================================"
echo "Phase 1: Testing All Components"
echo "======================================"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

echo ""
echo "======================================"
echo "Running Tests"
echo "======================================"
echo ""

# Run tests with coverage
python -m pytest tests/ -v --tb=short --color=yes --disable-warnings

echo ""
echo "======================================"
echo "Test Summary"
echo "======================================"
echo "✅ Phase 1 Component Testing Complete"
echo "======================================"
