#!/usr/bin/env python3
"""notion_tg_notifier 网络健壮性回归测试(stdlib + unittest.mock)。

约束:所有 requests 调用必须显式 timeout;Notion 写调用网络异常不得向上抛
(与类内既有错误处理风格一致:打印并返回 None/False)。
"""
from unittest import mock

import notion_tg_notifier
from notion_tg_notifier import NotionTGNotifier


def _make_notifier():
    n = NotionTGNotifier(config_path="/nonexistent/.env.lit")
    n.bot_token = "tk"
    n.chat_id = "cid"
    n.notion_token = "ntk"
    n.parent_id = "pid"
    n.proxy = None
    return n


def _resp(status=200, payload=None):
    r = mock.Mock()
    r.status_code = status
    r.json.return_value = payload if payload is not None else {}
    r.text = "mocked"
    return r


def test_all_requests_calls_have_timeout():
    n = _make_notifier()
    with mock.patch.object(notion_tg_notifier, "requests") as req:
        req.get.return_value = _resp(200, {"results": []})
        req.post.return_value = _resp(200, {"id": "page-1", "ok": True})
        req.patch.return_value = _resp(200)

        n.send_tg_message("hi")
        n.get_or_create_page("parent-1", "2026年06月")
        n.append_blocks("page-1", [])

        calls = list(req.get.call_args_list) + list(req.post.call_args_list) + list(req.patch.call_args_list)
        assert calls, "应当发生过 requests 调用"
        missing = [c for c in calls if not c.kwargs.get("timeout")]
        assert not missing, f"存在未设置 timeout 的 requests 调用: {missing}"


def test_notion_write_errors_do_not_raise():
    n = _make_notifier()
    with mock.patch.object(notion_tg_notifier, "requests") as req:
        req.get.side_effect = ConnectionError("net down")
        req.post.side_effect = ConnectionError("net down")
        req.patch.side_effect = ConnectionError("net down")

        page = n.get_or_create_page("parent-1", "标题")  # 不应抛异常
        assert page is None
        ok = n.append_blocks("page-1", [])  # 不应抛异常
        assert ok is False


if __name__ == "__main__":
    test_all_requests_calls_have_timeout()
    test_notion_write_errors_do_not_raise()
    print("OK")
