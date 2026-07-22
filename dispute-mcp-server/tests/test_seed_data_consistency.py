"""Cross-reference integrity checks for the seeded mock data."""

from dispute_mcp_server import seed_data


def test_every_case_transaction_id_has_a_transaction_record() -> None:
    for case in seed_data.CASES.values():
        assert case.transaction_id in seed_data.TRANSACTIONS


def test_every_transaction_case_id_matches_a_real_case() -> None:
    for transaction in seed_data.TRANSACTIONS.values():
        assert transaction.case_id in seed_data.CASES


def test_every_transaction_has_authorization_and_settlement() -> None:
    for transaction_id in seed_data.TRANSACTIONS:
        assert transaction_id in seed_data.AUTHORIZATIONS
        assert transaction_id in seed_data.SETTLEMENTS
        assert transaction_id in seed_data.REFUNDS_OR_REVERSALS


def test_every_case_customer_id_has_a_customer_profile() -> None:
    for case in seed_data.CASES.values():
        assert case.customer_id in seed_data.CUSTOMER_PROFILES


def test_every_customer_has_prior_disputes_and_refund_history_entries() -> None:
    for customer_id in seed_data.CUSTOMER_PROFILES:
        assert customer_id in seed_data.PRIOR_DISPUTES
        assert customer_id in seed_data.REFUND_HISTORY


def test_every_case_has_merchant_evidence_delivery_and_cancellation_details() -> None:
    for case_id in seed_data.CASES:
        assert case_id in seed_data.MERCHANT_EVIDENCE
        assert case_id in seed_data.DELIVERY_DETAILS
        assert case_id in seed_data.CANCELLATION_DETAILS


def test_transaction_amounts_match_their_case_amounts() -> None:
    for case in seed_data.CASES.values():
        transaction = seed_data.TRANSACTIONS[case.transaction_id]
        assert transaction.amount == case.amount
        assert transaction.currency == case.currency


def test_authorization_and_settlement_amounts_match_transaction_amounts() -> None:
    for transaction_id, transaction in seed_data.TRANSACTIONS.items():
        auth = seed_data.AUTHORIZATIONS[transaction_id]
        settlement = seed_data.SETTLEMENTS[transaction_id]
        assert auth.amount == transaction.amount
        assert settlement.amount == transaction.amount
