import json

import pytest

from src.services import goofish_seller_service as service


def test_normalize_cookie_entries_supports_playwright_storage_state():
    raw = {
        "cookies": [
            {"name": "unb", "value": "123", "domain": ".goofish.com"},
            {"name": "_m_h5_tk", "value": "token_1", "path": "/"},
            {"name": "ignored"},
        ],
        "origins": [],
    }

    assert service._normalize_cookie_entries(raw) == [
        {"name": "unb", "value": "123"},
        {"name": "_m_h5_tk", "value": "token_1"},
    ]


def test_prepare_goofish_cookie_file_converts_account_state(tmp_path, monkeypatch):
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    (state_dir / "main.json").write_text(
        json.dumps({"cookies": [{"name": "unb", "value": "123"}]}),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(service.env_manager, "get_value", lambda key, default=None: str(state_dir))

    cookie_path = service._prepare_goofish_cookie_file("main")

    assert cookie_path is not None
    assert json.loads((tmp_path / "data" / "goofish-cookies" / "main.json").read_text()) == [
        {"name": "unb", "value": "123"}
    ]


def test_prepare_goofish_cookie_file_rejects_bad_account_name():
    with pytest.raises(service.SellerToolError):
        service._prepare_goofish_cookie_file("../secret")
