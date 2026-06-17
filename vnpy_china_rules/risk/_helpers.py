"""风控共享 helper（vnpy 4.4.0 API 适配）"""

from typing import Optional

from vnpy.trader.object import AccountData


def get_first_account(main_engine) -> Optional[AccountData]:
    """获取首个账户（A股单账户场景）。

    vnpy 4.4.0 的 MainEngine.get_account(vt_accountid) 需要 vt_accountid，
    规则运行时无此信息，故用 get_all_accounts() 取首个。无账户返回 None
    （调用方现有 `if not account` 逻辑会跳过检查）。
    """
    accounts = main_engine.get_all_accounts()
    return accounts[0] if accounts else None
