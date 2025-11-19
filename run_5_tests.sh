#!/bin/bash

# Run transaction explorer tests 5 times
echo "======================================================================="
echo "  RUNNING TRANSACTION EXPLORER TESTS - 5 ROUNDS"
echo "======================================================================="

FIREBASE_SERVICE_ACCOUNT="./firebase-service-account.json"

for i in {1..5}
do
    echo ""
    echo "======================================================================="
    echo "  TEST ROUND $i of 5"
    echo "======================================================================="

    .venv/bin/python test_transaction_explorer.py 2>&1 | tail -20

    echo ""
    echo "Completed Round $i"
    echo ""
    sleep 2
done

echo "======================================================================="
echo "  ALL 5 TEST ROUNDS COMPLETED"
echo "======================================================================="
