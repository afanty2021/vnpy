"""
配置验证器模块

提供配置验证功能，支持必需字段、数值范围和枚举值验证。
"""

from typing import Any, Dict, List, Optional, Union

from .base import BaseConfig


class ConfigValidator:
    """配置验证器

    提供静态配置验证方法，支持多种验证规则。

    Features:
        - 必需字段验证
        - 数值范围验证
        - 枚举值验证
        - 自定义验证规则

    Example:
        ```python
        validator = ConfigValidator()

        # 验证必需字段
        result = validator.validate_required_fields(
            config,
            ["mysql_host", "mysql_port"]
        )

        # 验证数值范围
        result = validator.validate_range(
            config,
            "max_position_ratio",
            min_val=0.0,
            max_val=1.0
        )

        # 验证枚举值
        result = validator.validate_enum(
            config,
            "level",
            ["DEBUG", "INFO", "WARNING", "ERROR"]
        )
        ```
    """

    @staticmethod
    def validate_required_fields(
        config: BaseConfig,
        required_fields: List[str],
    ) -> Dict[str, Any]:
        """验证必需字段

        检查配置对象是否包含所有必需的字段。

        Args:
            config: 配置对象
            required_fields: 必需字段列表

        Returns:
            验证结果字典，包含 valid 和 errors 字段

        Example:
            ```python
            result = validator.validate_required_fields(
                db_config,
                ["mysql_host", "mysql_port", "mysql_database"]
            )
            # result = {"valid": True, "errors": []}
            ```
        """
        errors: List[str] = []

        for field in required_fields:
            value = getattr(config, field, None)
            if value is None:
                errors.append(f"必需字段 '{field}' 未设置")
            elif isinstance(value, str) and not value.strip():
                errors.append(f"必需字段 '{field}' 不能为空")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }

    @staticmethod
    def validate_range(
        config: BaseConfig,
        field: str,
        min_val: Optional[Union[int, float]] = None,
        max_val: Optional[Union[int, float]] = None,
    ) -> Dict[str, Any]:
        """验证数值范围

        检查配置字段的值是否在指定范围内。

        Args:
            config: 配置对象
            field: 字段名称
            min_val: 最小值（包含）
            max_val: 最大值（包含）

        Returns:
            验证结果字典，包含 valid 和 errors 字段

        Example:
            ```python
            result = validator.validate_range(
                config,
                "cpu_threshold",
                min_val=0.0,
                max_val=100.0
            )
            ```
        """
        value = getattr(config, field, None)

        if value is None:
            return {"valid": True, "errors": []}

        # 类型检查
        if not isinstance(value, (int, float)):
            return {
                "valid": False,
                "errors": [f"字段 '{field}' 值类型错误，期望数值类型，实际: {type(value).__name__}"],
            }

        errors: List[str] = []

        if min_val is not None and value < min_val:
            errors.append(f"字段 '{field}' 值 {value} 小于最小值 {min_val}")

        if max_val is not None and value > max_val:
            errors.append(f"字段 '{field}' 值 {value} 大于最大值 {max_val}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }

    @staticmethod
    def validate_enum(
        config: BaseConfig,
        field: str,
        valid_values: List[str],
    ) -> Dict[str, Any]:
        """验证枚举值

        检查配置字段的值是否在允许的枚举值列表中。

        Args:
            config: 配置对象
            field: 字段名称
            valid_values: 允许的值列表

        Returns:
            验证结果字典，包含 valid 和 errors 字段

        Example:
            ```python
            result = validator.validate_enum(
                config,
                "level",
                ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            )
            ```
        """
        value = getattr(config, field, None)

        if value is None:
            return {"valid": True, "errors": []}

        # 转换为字符串比较，保持大小写
        value_str = str(value)

        if value_str not in valid_values:
            return {
                "valid": False,
                "errors": [f"字段 '{field}' 值 '{value}' 不在允许的值列表中: {valid_values}"],
            }

        return {"valid": True, "errors": []}

    @staticmethod
    def validate_config(config: BaseConfig) -> Dict[str, Any]:
        """综合验证配置

        使用 Pydantic 内置验证，并返回验证结果。

        Args:
            config: 配置对象

        Returns:
            验证结果字典

        Note:
            Pydantic 会在模型实例化时自动验证，
            此方法主要用于获取详细的验证错误信息。
        """
        try:
            # 尝试重新验证
            config.model_validate(config.model_dump())
            return {"valid": True, "errors": []}
        except Exception as e:
            return {"valid": False, "errors": [str(e)]}

    @staticmethod
    def validate_dependencies(
        config: BaseConfig,
        rules: Dict[str, List[str]],
    ) -> Dict[str, Any]:
        """验证字段依赖关系

        检查某些字段存在时，相关字段是否也有值。

        Args:
            config: 配置对象
            rules: 依赖规则，格式为 {field: [dependent_fields]}

        Returns:
            验证结果字典

        Example:
            ```python
            rules = {
                "email_enabled": ["smtp_host", "email_username", "email_password"],
                "wechat_enabled": ["wechat_webhook"]
            }
            result = validator.validate_dependencies(config, rules)
            ```
        """
        errors: List[str] = []

        for field, dependent_fields in rules.items():
            field_value = getattr(config, field, None)

            # 如果主字段存在且为 True，检查依赖字段
            if field_value:
                for dependent_field in dependent_fields:
                    dependent_value = getattr(config, dependent_field, None)
                    if dependent_value is None or (
                        isinstance(dependent_value, str) and not dependent_value.strip()
                    ):
                        errors.append(
                            f"字段 '{field}' 启用时，'{dependent_field}' 必须有值"
                        )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }
