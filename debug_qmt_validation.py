"""调试 QmtConfig 验证"""

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class QmtConfig(BaseModel):
    """测试 QmtConfig"""

    account_id: str = Field(
        default="",
        description="QMT交易账号（启用时必填）"
    )
    enabled: bool = False

    @field_validator("account_id")
    @classmethod
    def validate_account_id(cls, v: str, info: ValidationInfo) -> str:
        """验证 account_id"""
        print(f"DEBUG: v = {repr(v)}")
        print(f"DEBUG: type(info) = {type(info)}")
        print(f"DEBUG: dir(info) = {dir(info)}")
        print(f"DEBUG: hasattr(info, 'data') = {hasattr(info, 'data')}")

        if hasattr(info, 'data'):
            print(f"DEBUG: info.data = {info.data}")
            print(f"DEBUG: type(info.data) = {type(info.data)}")

        if hasattr(info, 'data') and info.data:
            enabled = info.data.get('enabled', False)
            print(f"DEBUG: enabled from data = {enabled}")
        else:
            enabled = False
            print(f"DEBUG: enabled default = {enabled}")

        if enabled:
            if not v or not v.strip():
                raise ValueError("account_id 在启用QMT时不能为空")
            return v.strip()

        return v.strip() if v else v


# 测试1：enabled=True, account_id=""
print("\n=== Test 1: enabled=True, account_id='' ===")
try:
    config = QmtConfig(account_id="", enabled=True)
    print(f"Result: account_id = {repr(config.account_id)}")
except Exception as e:
    print(f"Exception: {type(e).__name__}: {e}")

# 测试2：enabled=True, account_id="123"
print("\n=== Test 2: enabled=True, account_id='123' ===")
try:
    config = QmtConfig(account_id="123", enabled=True)
    print(f"Result: account_id = {repr(config.account_id)}")
except Exception as e:
    print(f"Exception: {type(e).__name__}: {e}")

# 测试3：enabled=False, account_id=""
print("\n=== Test 3: enabled=False, account_id='' ===")
try:
    config = QmtConfig(account_id="", enabled=False)
    print(f"Result: account_id = {repr(config.account_id)}")
except Exception as e:
    print(f"Exception: {type(e).__name__}: {e}")
