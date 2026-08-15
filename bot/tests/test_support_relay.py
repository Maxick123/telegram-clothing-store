from app.support import SupportRelay


def test_relay_routes_group_reply_to_original_customer() -> None:
    """An operator reply is sent only to the customer whose copied message it answers."""
    relay = SupportRelay()
    relay.remember(group_message_id=42, customer_chat_id=100500)

    assert relay.customer_for_reply(42) == 100500


def test_relay_does_not_route_unrelated_group_message() -> None:
    """A group message without a known customer anchor must never be delivered."""
    relay = SupportRelay()

    assert relay.customer_for_reply(999) is None
