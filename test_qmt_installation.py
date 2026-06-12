#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
QMT Environment Installation Verification Script
Verify xtquant and vnpy_qmt are correctly installed
"""

import sys
from pathlib import Path

def test_installation():
    """Test QMT environment installation"""
    print("=" * 60)
    print("QMT Environment Installation Verification")
    print("=" * 60)

    # Test 1: xtquant package
    print("\n1. Testing xtquant package...")
    try:
        import xtquant
        print(f"   [OK] xtquant version: {xtquant.__version__}")
        print(f"   [OK] Install path: {xtquant.__file__}")
    except ImportError as e:
        print(f"   [FAIL] xtquant import failed: {e}")
        return False

    # Test 2: xtdata module
    print("\n2. Testing xtdata module...")
    try:
        from xtquant import xtdata
        functions = [x for x in dir(xtdata) if not x.startswith('_')]
        print(f"   [OK] xtdata imported successfully")
        print(f"   [OK] Available functions: {len(functions)}")
        print(f"   [OK] Main functions: {functions[:5]}")
    except ImportError as e:
        print(f"   [FAIL] xtdata import failed: {e}")
        return False

    # Test 3: xttrader module
    print("\n3. Testing xttrader module...")
    try:
        from xtquant import xttrader
        functions = [x for x in dir(xttrader) if not x.startswith('_')]
        print(f"   [OK] xttrader imported successfully")
        print(f"   [OK] Available functions: {len(functions)}")
    except ImportError as e:
        print(f"   [FAIL] xttrader import failed: {e}")
        return False

    # Test 4: vnpy core
    print("\n4. Testing vnpy core package...")
    try:
        import vnpy
        print(f"   [OK] vnpy version: {vnpy.__version__}")
        print(f"   [OK] Install path: {vnpy.__file__}")
    except ImportError as e:
        print(f"   [FAIL] vnpy import failed: {e}")
        return False

    # Test 5: vnpy_qmt
    print("\n5. Testing vnpy_qmt package...")
    try:
        from vnpy_qmt import QmtGateway
        methods = [x for x in dir(QmtGateway) if not x.startswith('_')]
        print(f"   [OK] QmtGateway imported successfully")
        print(f"   [OK] Available methods: {len(methods)}")
        print(f"   [OK] Main methods: {methods[:8]}")
    except ImportError as e:
        print(f"   [FAIL] vnpy_qmt import failed: {e}")
        return False

    # Test 6: VeighNa core components
    print("\n6. Testing VeighNa core components...")
    try:
        from vnpy.event import EventEngine
        from vnpy.trader.engine import MainEngine
        print(f"   [OK] EventEngine imported successfully")
        print(f"   [OK] MainEngine imported successfully")
    except ImportError as e:
        print(f"   [FAIL] VeighNa core components import failed: {e}")
        return False

    print("\n" + "=" * 60)
    print("[SUCCESS] All tests passed! QMT environment setup completed")
    print("=" * 60)

    # Display environment information
    print(f"\nPython version: {sys.version}")
    print(f"Python path: {sys.executable}")
    print(f"\nInstalled key packages:")
    print(f"  - xtquant: {xtquant.__version__}")
    print(f"  - vnpy: {vnpy.__version__}")
    print(f"  - vnpy_qmt: Installed")

    return True

if __name__ == "__main__":
    success = test_installation()
    sys.exit(0 if success else 1)
