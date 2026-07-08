"""Demo MCP server exposing fake Super Payments refund tools.

Not a real payments integration: transactions are seeded in-memory in
`data.py` from the sample RAG documents and mutated in place when refunded.
"""

from datetime import datetime as dt
from datetime import timezone

from mcp.server.fastmcp import FastMCP

from fake_refund import data

mcp = FastMCP("fake-refund", host="0.0.0.0", port=8010)

PROCESSING_TIMES = {
    "mastercard": "5-10 business days",
    "visa": "5-10 business days",
    "amex": "5-10 business days",
    "apple pay": "3-5 business days",
    "google pay": "3-5 business days",
    "paypal": "1-3 business days",
    "klarna": "5-7 business days",
    "wire / ach": "3-7 business days",
}


def _format_transaction(txn: dict) -> str:
    lines = [
        f"transaction_id: {txn['transaction_id']}",
        f"client: {txn['client_name']} ({txn['client_id']})",
        f"date: {txn['date']}",
        f"amount: {txn['amount']:.2f} {txn['currency']}",
        f"payment_method: {txn['payment_method']}",
        f"status: {txn['status']}",
    ]
    if txn["refund"]:
        r = txn["refund"]
        lines.append(
            f"refund: {r['type']} refund of {r['amount']:.2f} {txn['currency']} "
            f"on {r['refunded_at']} (reason: {r['reason'] or 'n/a'})"
        )
    return "\n".join(lines)


@mcp.tool()
def list_transactions(client: str = "", status: str = "") -> str:
    """List Super Payments transactions, optionally filtered by client name/ID
    ("Awesome Client Inc." / AC-2023-0034, or "Happy Client Ltd." / HC-2024-0081)
    and/or status (Success, Failed, Refunded). Leave a parameter empty to skip
    that filter. Use this to find a transaction_id before calling
    get_transaction or refund_transaction.
    """
    results = data.search_transactions(client=client, status=status)
    if not results:
        return "No matching transactions found."
    header = "transaction_id | date | amount | payment_method | status"
    rows = [
        f"{t['transaction_id']} | {t['date']} | {t['amount']:.2f} {t['currency']} | "
        f"{t['payment_method']} | {t['status']}"
        for t in results
    ]
    return "\n".join([header, *rows])


@mcp.tool()
def get_transaction(transaction_id: str) -> str:
    """Look up full details for one Super Payments transaction by its
    transaction_id (e.g. "SP-AC-200441"): client, date, amount, payment
    method, current status, and refund details if already refunded.
    """
    txn = data.find_transaction(transaction_id)
    if txn is None:
        return f"No transaction found with ID '{transaction_id}'."
    return _format_transaction(txn)


@mcp.tool()
def refund_transaction(transaction_id: str, amount: float = 0.0, reason: str = "") -> str:
    """Issue a refund for a Super Payments transaction. Omit amount (or pass
    0) for a FULL refund of the original amount; pass a positive amount less
    than the original for a PARTIAL refund. Fails with a clear message if the
    transaction doesn't exist, is already refunded, was a Failed transaction,
    or the requested amount exceeds the original. On success, returns the
    refund type, amount, and an estimated processing time based on the
    original payment method (cards 5-10 business days, Apple/Google Pay 3-5
    days, PayPal 1-3 days, Klarna 5-7 days, Wire/ACH 3-7 days).
    """
    txn = data.find_transaction(transaction_id)
    if txn is None:
        return f"No transaction found with ID '{transaction_id}'."
    if txn["status"] == "Refunded":
        r = txn["refund"]
        return (
            f"Transaction '{transaction_id}' was already refunded "
            f"({r['type']}, {r['amount']:.2f} {txn['currency']}, on {r['refunded_at']}). "
            "Cannot issue another refund."
        )
    if txn["status"] == "Failed":
        return f"Transaction '{transaction_id}' was a Failed transaction and was never charged; nothing to refund."

    refund_amount = amount if amount and amount > 0 else txn["amount"]
    if refund_amount > txn["amount"]:
        return (
            f"Refund amount {refund_amount:.2f} {txn['currency']} exceeds the original "
            f"transaction amount of {txn['amount']:.2f} {txn['currency']}. Refund rejected."
        )

    refund_type = "Full" if refund_amount == txn["amount"] else "Partial"
    txn["status"] = "Refunded"
    txn["refund"] = {
        "amount": refund_amount,
        "type": refund_type,
        "reason": reason,
        "refunded_at": dt.now(timezone.utc).date().isoformat(),
    }

    eta = PROCESSING_TIMES.get(txn["payment_method"].lower(), "5-10 business days")
    return (
        f"{refund_type} refund issued for transaction '{transaction_id}': "
        f"{refund_amount:.2f} {txn['currency']} refunded to the original {txn['payment_method']} "
        f"payment method. Estimated to reach the shopper in {eta}."
    )
