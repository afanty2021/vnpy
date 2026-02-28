"""直接测试验证逻辑"""

from vnpy_china_config.global_config import QmtConfig

# 测试1：enabled=True, account_id="" - 应该抛出异常
print("=== Test 1: enabled=True, account_id='' ===")
try:
    config = QmtConfig(account_id="", mini_path="D:/test", enabled=True)
    print(f"FAIL: No exception raised. account_id={repr(config.account_id)}")
except Exception as e:
    print(f"PASS: {type(e).__name__}: {e}")

# 测试2：enabled=True, mini_path="" - 应该抛出异常
print("\n=== Test 2: enabled=True, mini_path='' ===")
try:
    config = QmtConfig(account_id="123", mini_path="", enabled=True)
    print(f"FAIL: No exception raised. mini_path={repr(config.mini_path)}")
except Exception as e:
    print(f"PASS: {type(e).__name__}: {e}")

# 测试3：enabled=True, 两者都有值 - 应该成功
print("\n=== Test 3: enabled=True, both valid ===")
try:
    config = QmtConfig(account_id="123", mini_path="D:/test", enabled=True)
    print(f"PASS: account_id={repr(config.account_id)}, mini_path={repr(config.mini_path)}")
except Exception as e:
    print(f"FAIL: {type(e).__name__}: {e}")

# 测试4：enabled=False, 两者都为空 - 应该成功
print("\n=== Test 4: enabled=False, both empty ===")
try:
    config = QmtConfig(account_id="", mini_path="", enabled=False)
    print(f"PASS: account_id={repr(config.account_id)}, mini_path={repr(config.mini_path)}")
except Exception as e:
    print(f"FAIL: {type(e).__name__}: {e}")
