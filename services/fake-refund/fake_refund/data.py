"""Seed data for the fake-refund demo MCP server.

Transactions are copied verbatim (ID, date, amount, method, status) from the
sample transaction reports in `sample-data/awesome_client_transaction_report.pdf`
and `sample-data/happy_client_transaction_report.pdf`, so a chatbot session that
has ingested those PDFs can cross-reference real-looking transaction IDs.

State lives only in this in-memory list for the lifetime of the container
process: refunds issued during a demo reset on container restart, and there is
no locking around mutation (fine for a single-user demo, not safe for
concurrent refund calls).
"""

TRANSACTIONS: list[dict] = [
    # --- Awesome Client Inc. (AC-2023-0034) ---
    {"transaction_id": "SP-AC-200441", "client_id": "AC-2023-0034", "client_name": "Awesome Client Inc.", "date": "2025-01-03", "amount": 1850.00, "currency": "USD", "payment_method": "Mastercard", "status": "Success", "refund": None},
    {"transaction_id": "SP-AC-200498", "client_id": "AC-2023-0034", "client_name": "Awesome Client Inc.", "date": "2025-01-06", "amount": 420.75, "currency": "USD", "payment_method": "Visa", "status": "Success", "refund": None},
    {"transaction_id": "SP-AC-200553", "client_id": "AC-2023-0034", "client_name": "Awesome Client Inc.", "date": "2025-01-10", "amount": 3200.00, "currency": "USD", "payment_method": "Amex", "status": "Success", "refund": None},
    {"transaction_id": "SP-AC-200612", "client_id": "AC-2023-0034", "client_name": "Awesome Client Inc.", "date": "2025-01-14", "amount": 99.99, "currency": "USD", "payment_method": "Apple Pay", "status": "Success", "refund": None},
    {"transaction_id": "SP-AC-200670", "client_id": "AC-2023-0034", "client_name": "Awesome Client Inc.", "date": "2025-01-19", "amount": 750.00, "currency": "USD", "payment_method": "Visa", "status": "Failed", "refund": None},
    {"transaction_id": "SP-AC-200731", "client_id": "AC-2023-0034", "client_name": "Awesome Client Inc.", "date": "2025-01-23", "amount": 2100.00, "currency": "USD", "payment_method": "Mastercard", "status": "Success", "refund": None},
    {"transaction_id": "SP-AC-200789", "client_id": "AC-2023-0034", "client_name": "Awesome Client Inc.", "date": "2025-01-29", "amount": 580.50, "currency": "USD", "payment_method": "PayPal", "status": "Success", "refund": None},
    {"transaction_id": "SP-AC-200844", "client_id": "AC-2023-0034", "client_name": "Awesome Client Inc.", "date": "2025-02-04", "amount": 4500.00, "currency": "USD", "payment_method": "Amex", "status": "Success", "refund": None},
    {"transaction_id": "SP-AC-200902", "client_id": "AC-2023-0034", "client_name": "Awesome Client Inc.", "date": "2025-02-08", "amount": 199.00, "currency": "USD", "payment_method": "Google Pay", "status": "Success", "refund": None},
    {"transaction_id": "SP-AC-200961", "client_id": "AC-2023-0034", "client_name": "Awesome Client Inc.", "date": "2025-02-13", "amount": 1340.00, "currency": "USD", "payment_method": "Visa", "status": "Refunded", "refund": {"amount": 1340.00, "type": "Full", "reason": "Customer request", "refunded_at": "2025-02-18"}},
    {"transaction_id": "SP-AC-201020", "client_id": "AC-2023-0034", "client_name": "Awesome Client Inc.", "date": "2025-02-18", "amount": 870.00, "currency": "USD", "payment_method": "Mastercard", "status": "Refunded", "refund": {"amount": 870.00, "type": "Full", "reason": "Customer request", "refunded_at": "2025-02-23"}},
    {"transaction_id": "SP-AC-201079", "client_id": "AC-2023-0034", "client_name": "Awesome Client Inc.", "date": "2025-02-22", "amount": 295.00, "currency": "USD", "payment_method": "Apple Pay", "status": "Success", "refund": None},
    {"transaction_id": "SP-AC-201138", "client_id": "AC-2023-0034", "client_name": "Awesome Client Inc.", "date": "2025-02-27", "amount": 6800.00, "currency": "USD", "payment_method": "Amex", "status": "Success", "refund": None},
    {"transaction_id": "SP-AC-201197", "client_id": "AC-2023-0034", "client_name": "Awesome Client Inc.", "date": "2025-03-05", "amount": 430.00, "currency": "USD", "payment_method": "Visa", "status": "Success", "refund": None},
    {"transaction_id": "SP-AC-201256", "client_id": "AC-2023-0034", "client_name": "Awesome Client Inc.", "date": "2025-03-11", "amount": 1100.00, "currency": "USD", "payment_method": "Mastercard", "status": "Success", "refund": None},
    {"transaction_id": "SP-AC-201315", "client_id": "AC-2023-0034", "client_name": "Awesome Client Inc.", "date": "2025-03-16", "amount": 2750.00, "currency": "USD", "payment_method": "Amex", "status": "Success", "refund": None},
    {"transaction_id": "SP-AC-201374", "client_id": "AC-2023-0034", "client_name": "Awesome Client Inc.", "date": "2025-03-21", "amount": 340.00, "currency": "USD", "payment_method": "Google Pay", "status": "Failed", "refund": None},
    {"transaction_id": "SP-AC-201433", "client_id": "AC-2023-0034", "client_name": "Awesome Client Inc.", "date": "2025-03-26", "amount": 8200.00, "currency": "USD", "payment_method": "Wire / ACH", "status": "Success", "refund": None},
    {"transaction_id": "SP-AC-201492", "client_id": "AC-2023-0034", "client_name": "Awesome Client Inc.", "date": "2025-04-02", "amount": 990.00, "currency": "USD", "payment_method": "Visa", "status": "Success", "refund": None},
    {"transaction_id": "SP-AC-201551", "client_id": "AC-2023-0034", "client_name": "Awesome Client Inc.", "date": "2025-04-08", "amount": 1450.00, "currency": "USD", "payment_method": "Mastercard", "status": "Success", "refund": None},
    # --- Happy Client Ltd. (HC-2024-0081) ---
    {"transaction_id": "SP-HC-100142", "client_id": "HC-2024-0081", "client_name": "Happy Client Ltd.", "date": "2025-01-02", "amount": 312.50, "currency": "USD", "payment_method": "Visa", "status": "Success", "refund": None},
    {"transaction_id": "SP-HC-100198", "client_id": "HC-2024-0081", "client_name": "Happy Client Ltd.", "date": "2025-01-05", "amount": 89.99, "currency": "USD", "payment_method": "Apple Pay", "status": "Success", "refund": None},
    {"transaction_id": "SP-HC-100254", "client_id": "HC-2024-0081", "client_name": "Happy Client Ltd.", "date": "2025-01-09", "amount": 540.00, "currency": "USD", "payment_method": "Mastercard", "status": "Success", "refund": None},
    {"transaction_id": "SP-HC-100310", "client_id": "HC-2024-0081", "client_name": "Happy Client Ltd.", "date": "2025-01-13", "amount": 27.00, "currency": "USD", "payment_method": "Google Pay", "status": "Failed", "refund": None},
    {"transaction_id": "SP-HC-100381", "client_id": "HC-2024-0081", "client_name": "Happy Client Ltd.", "date": "2025-01-18", "amount": 195.75, "currency": "USD", "payment_method": "Visa", "status": "Success", "refund": None},
    {"transaction_id": "SP-HC-100429", "client_id": "HC-2024-0081", "client_name": "Happy Client Ltd.", "date": "2025-01-22", "amount": 67.49, "currency": "USD", "payment_method": "PayPal", "status": "Refunded", "refund": {"amount": 67.49, "type": "Full", "reason": "Customer request", "refunded_at": "2025-01-27"}},
    {"transaction_id": "SP-HC-100512", "client_id": "HC-2024-0081", "client_name": "Happy Client Ltd.", "date": "2025-01-28", "amount": 1249.00, "currency": "USD", "payment_method": "Amex", "status": "Success", "refund": None},
    {"transaction_id": "SP-HC-100589", "client_id": "HC-2024-0081", "client_name": "Happy Client Ltd.", "date": "2025-02-03", "amount": 88.00, "currency": "USD", "payment_method": "Mastercard", "status": "Success", "refund": None},
    {"transaction_id": "SP-HC-100634", "client_id": "HC-2024-0081", "client_name": "Happy Client Ltd.", "date": "2025-02-07", "amount": 430.20, "currency": "USD", "payment_method": "Visa", "status": "Refunded", "refund": {"amount": 430.20, "type": "Full", "reason": "Customer request", "refunded_at": "2025-02-12"}},
    {"transaction_id": "SP-HC-100701", "client_id": "HC-2024-0081", "client_name": "Happy Client Ltd.", "date": "2025-02-12", "amount": 55.00, "currency": "USD", "payment_method": "Apple Pay", "status": "Success", "refund": None},
    {"transaction_id": "SP-HC-100758", "client_id": "HC-2024-0081", "client_name": "Happy Client Ltd.", "date": "2025-02-17", "amount": 310.00, "currency": "USD", "payment_method": "Visa", "status": "Success", "refund": None},
    {"transaction_id": "SP-HC-100812", "client_id": "HC-2024-0081", "client_name": "Happy Client Ltd.", "date": "2025-02-21", "amount": 74.99, "currency": "USD", "payment_method": "Klarna", "status": "Success", "refund": None},
    {"transaction_id": "SP-HC-100876", "client_id": "HC-2024-0081", "client_name": "Happy Client Ltd.", "date": "2025-02-26", "amount": 920.00, "currency": "USD", "payment_method": "Mastercard", "status": "Success", "refund": None},
    {"transaction_id": "SP-HC-100934", "client_id": "HC-2024-0081", "client_name": "Happy Client Ltd.", "date": "2025-03-04", "amount": 155.50, "currency": "USD", "payment_method": "Google Pay", "status": "Success", "refund": None},
    {"transaction_id": "SP-HC-101021", "client_id": "HC-2024-0081", "client_name": "Happy Client Ltd.", "date": "2025-03-10", "amount": 49.00, "currency": "USD", "payment_method": "PayPal", "status": "Failed", "refund": None},
    {"transaction_id": "SP-HC-101089", "client_id": "HC-2024-0081", "client_name": "Happy Client Ltd.", "date": "2025-03-15", "amount": 780.00, "currency": "USD", "payment_method": "Visa", "status": "Success", "refund": None},
    {"transaction_id": "SP-HC-101143", "client_id": "HC-2024-0081", "client_name": "Happy Client Ltd.", "date": "2025-03-20", "amount": 33.00, "currency": "USD", "payment_method": "Apple Pay", "status": "Success", "refund": None},
    {"transaction_id": "SP-HC-101202", "client_id": "HC-2024-0081", "client_name": "Happy Client Ltd.", "date": "2025-03-25", "amount": 215.00, "currency": "USD", "payment_method": "Mastercard", "status": "Success", "refund": None},
    {"transaction_id": "SP-HC-101267", "client_id": "HC-2024-0081", "client_name": "Happy Client Ltd.", "date": "2025-04-01", "amount": 629.99, "currency": "USD", "payment_method": "Amex", "status": "Success", "refund": None},
    {"transaction_id": "SP-HC-101334", "client_id": "HC-2024-0081", "client_name": "Happy Client Ltd.", "date": "2025-04-07", "amount": 112.00, "currency": "USD", "payment_method": "Visa", "status": "Success", "refund": None},
]


def _matches_client(txn: dict, client_id: str) -> bool:
    needle = client_id.strip().lower()
    if not needle:
        return False
    return needle in txn["client_id"].lower() or needle in txn["client_name"].lower()


def find_transaction(transaction_id: str, client_id: str) -> dict | None:
    transaction_id = transaction_id.strip().upper()
    for txn in TRANSACTIONS:
        if txn["transaction_id"] == transaction_id and _matches_client(txn, client_id):
            return txn
    return None


def search_transactions(client_id: str, status: str = "") -> list[dict]:
    results = [txn for txn in TRANSACTIONS if _matches_client(txn, client_id)]
    if status:
        needle = status.strip().lower()
        results = [txn for txn in results if txn["status"].lower() == needle]
    return results
