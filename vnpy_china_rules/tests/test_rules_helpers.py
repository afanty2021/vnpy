"""风控 helper 单测（不需 vnpy_riskmanager）"""

import unittest
from unittest.mock import MagicMock

from vnpy_china_rules.risk._helpers import get_first_account


class TestGetFirstAccount(unittest.TestCase):
    def test_returns_first_when_multiple(self):
        """多账户时返回首个"""
        a1 = MagicMock(name="account1")
        a2 = MagicMock(name="account2")
        main_engine = MagicMock()
        main_engine.get_all_accounts.return_value = [a1, a2]
        self.assertIs(get_first_account(main_engine), a1)

    def test_returns_none_when_empty(self):
        """无账户时返回 None"""
        main_engine = MagicMock()
        main_engine.get_all_accounts.return_value = []
        self.assertIsNone(get_first_account(main_engine))


if __name__ == "__main__":
    unittest.main()
