from app.services.telegram_bot import is_authorized, split_telegram_text


def test_telegram_auth_allows_when_owner_unset():
    assert is_authorized(123, "") is True


def test_telegram_auth_blocks_other_users_when_owner_set():
    assert is_authorized(123, "456") is False
    assert is_authorized(456, "456") is True


def test_split_telegram_text_chunks_long_messages():
    chunks = split_telegram_text("a\n" * 5000, limit=1000)

    assert len(chunks) > 1
    assert all(len(chunk) <= 1000 for chunk in chunks)
