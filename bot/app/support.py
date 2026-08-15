class SupportRelay:
    """Keeps the group reply anchor private and routes replies through the shop bot."""

    def __init__(self) -> None:
        self._customer_chats: dict[int, int] = {}

    def remember(self, group_message_id: int, customer_chat_id: int) -> None:
        self._customer_chats[group_message_id] = customer_chat_id

    def customer_for_reply(self, group_reply_to_message_id: int) -> int | None:
        return self._customer_chats.get(group_reply_to_message_id)
