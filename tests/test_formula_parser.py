# -*- coding: utf-8 -*-
"""
通达信公式解析器单元测试
"""

import pytest
import sys
from pathlib import Path

# 添加vnpy路径
vnpy_path = Path(__file__).parent.parent
sys.path.insert(0, str(vnpy_path))

from vnpy.tools.formula_parser.lexer import FormulaLexer, TokenType
from vnpy.tools.formula_parser.parser import FormulaParser
from vnpy.tools.formula_parser.ast_nodes import *
from vnpy.tools.formula_parser.function_map import FunctionMapper
from vnpy.tools.formula_parser.code_generator import CodeGenerator, PythonExpressionGenerator


class TestFormulaLexer:
    """词法分析器测试"""

    def test_number(self):
        """测试数字识别"""
        lexer = FormulaLexer("123")
        tokens = lexer.tokenize()

        assert len(tokens) == 2  # NUMBER + EOF
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].value == 123

    def test_float(self):
        """测试浮点数识别"""
        lexer = FormulaLexer("123.45")
        tokens = lexer.tokenize()

        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].value == 123.45

    def test_operators(self):
        """测试运算符识别"""
        lexer = FormulaLexer("+ - * / %")
        tokens = lexer.tokenize()

        operators = [t.type for t in tokens if t.type != TokenType.EOF]
        assert operators == [
            TokenType.PLUS,
            TokenType.MINUS,
            TokenType.MULTIPLY,
            TokenType.DIVIDE,
            TokenType.MODULO
        ]

    def test_comparison_operators(self):
        """测试比较运算符识别"""
        lexer = FormulaLexer("== != > < >= <=")
        tokens = lexer.tokenize()

        operators = [t.type for t in tokens if t.type != TokenType.EOF]
        assert operators == [
            TokenType.EQUAL,
            TokenType.NOT_EQUAL,
            TokenType.GREATER,
            TokenType.LESS,
            TokenType.GREATER_EQUAL,
            TokenType.LESS_EQUAL
        ]

    def test_logical_operators(self):
        """测试逻辑运算符识别"""
        lexer = FormulaLexer("&& || !")
        tokens = lexer.tokenize()

        operators = [t.type for t in tokens if t.type != TokenType.EOF]
        assert operators == [
            TokenType.AND,
            TokenType.OR,
            TokenType.NOT
        ]

    def test_identifier(self):
        """测试标识符识别"""
        lexer = FormulaLexer("MA EMA CLOSE")
        tokens = lexer.tokenize()

        identifiers = [t for t in tokens if t.type == TokenType.IDENTIFIER]
        assert len(identifiers) == 3
        assert identifiers[0].value == "MA"
        assert identifiers[1].value == "EMA"
        assert identifiers[2].value == "CLOSE"

    def test_string(self):
        """测试字符串识别"""
        lexer = FormulaLexer('"hello" \'world\'')
        tokens = lexer.tokenize()

        strings = [t for t in tokens if t.type == TokenType.STRING]
        assert len(strings) == 2
        assert strings[0].value == "hello"
        assert strings[1].value == "world"

    def test_function_call(self):
        """测试函数调用识别"""
        lexer = FormulaLexer("MA(CLOSE, 5)")
        tokens = lexer.tokenize()

        expected_types = [
            TokenType.IDENTIFIER,  # MA
            TokenType.LPAREN,      # (
            TokenType.IDENTIFIER,  # CLOSE
            TokenType.COMMA,       # ,
            TokenType.NUMBER,      # 5
            TokenType.RPAREN,      # )
            TokenType.EOF
        ]

        assert [t.type for t in tokens] == expected_types

    def test_comment(self):
        """测试注释跳过"""
        lexer = FormulaLexer("123 // this is a comment\n456")
        tokens = lexer.tokenize()

        numbers = [t for t in tokens if t.type == TokenType.NUMBER]
        assert len(numbers) == 2
        assert numbers[0].value == 123
        assert numbers[1].value == 456

    def test_complex_expression(self):
        """测试复杂表达式"""
        formula = "MA(CLOSE, 5) > MA(CLOSE, 10) && VOLUME > 10000"
        lexer = FormulaLexer(formula)
        tokens = lexer.tokenize()

        # 验证token序列
        expected_keywords = ["MA", "CLOSE", "MA", "CLOSE", "VOLUME"]
        identifiers = [t.value for t in tokens if t.type == TokenType.IDENTIFIER]
        assert identifiers == expected_keywords


class TestFormulaParser:
    """语法分析器测试"""

    def test_number_expression(self):
        """测试数字表达式"""
        lexer = FormulaLexer("123")
        tokens = lexer.tokenize()
        parser = FormulaParser(tokens)

        ast = parser.parse()
        assert len(ast) == 1
        assert isinstance(ast[0], NumberNode)
        assert ast[0].value == 123

    def test_binary_operation(self):
        """测试二元运算"""
        lexer = FormulaLexer("1 + 2")
        tokens = lexer.tokenize()
        parser = FormulaParser(tokens)

        ast = parser.parse()
        assert len(ast) == 1
        assert isinstance(ast[0], BinaryOpNode)
        assert ast[0].operator == "+"

    def test_operator_precedence(self):
        """测试运算符优先级"""
        lexer = FormulaLexer("1 + 2 * 3")
        tokens = lexer.tokenize()
        parser = FormulaParser(tokens)

        ast = parser.parse()
        assert len(ast) == 1
        assert isinstance(ast[0], BinaryOpNode)
        # 应该是 (1 + (2 * 3))
        assert ast[0].operator == "+"
        assert isinstance(ast[0].right, BinaryOpNode)
        assert ast[0].right.operator == "*"

    def test_function_call(self):
        """测试函数调用"""
        lexer = FormulaLexer("MA(CLOSE, 5)")
        tokens = lexer.tokenize()
        parser = FormulaParser(tokens)

        ast = parser.parse()
        assert len(ast) == 1
        assert isinstance(ast[0], FunctionCallNode)
        assert ast[0].function.name == "MA"
        assert len(ast[0].arguments) == 2

    def test_nested_function_call(self):
        """测试嵌套函数调用"""
        lexer = FormulaLexer("MAX(MA(CLOSE, 5), MA(CLOSE, 10))")
        tokens = lexer.tokenize()
        parser = FormulaParser(tokens)

        ast = parser.parse()
        assert len(ast) == 1
        assert isinstance(ast[0], FunctionCallNode)
        assert ast[0].function.name == "MAX"
        assert len(ast[0].arguments) == 2

    def test_logical_expression(self):
        """测试逻辑表达式"""
        lexer = FormulaLexer("A > B && C < D")
        tokens = lexer.tokenize()
        parser = FormulaParser(tokens)

        ast = parser.parse()
        assert len(ast) == 1
        assert isinstance(ast[0], BinaryOpNode)
        assert ast[0].operator == "&&"

    def test_parentheses(self):
        """测试括号"""
        lexer = FormulaLexer("(1 + 2) * 3")
        tokens = lexer.tokenize()
        parser = FormulaParser(tokens)

        ast = parser.parse()
        assert len(ast) == 1
        assert isinstance(ast[0], BinaryOpNode)
        # 应该是 ((1 + 2) * 3)
        assert ast[0].operator == "*"
        assert isinstance(ast[0].left, BinaryOpNode)
        assert ast[0].left.operator == "+"


class TestFunctionMapper:
    """函数映射器测试"""

    def test_basic_translation(self):
        """测试基本函数转换"""
        mapper = FunctionMapper()

        # 测试MA函数
        func_info = mapper.get_by_tdx_name("MA")
        assert func_info is not None
        assert func_info.name == "ma"

    def test_unknown_function(self):
        """测试未知函数"""
        mapper = FunctionMapper()

        func_info = mapper.get_by_tdx_name("UNKNOWN_FUNCTION")
        assert func_info is None

    def test_function_validation(self):
        """测试函数调用验证"""
        mapper = FunctionMapper()

        # MA函数需要2个参数
        assert mapper.is_valid_call("MA", 2)
        assert not mapper.is_valid_call("MA", 1)

        # MAX函数可以有1或2个参数
        assert mapper.is_valid_call("MAX", 1)
        assert mapper.is_valid_call("MAX", 2)

    def test_case_insensitive(self):
        """测试大小写不敏感"""
        mapper = FunctionMapper()

        ma_lower = mapper.get_by_tdx_name("ma")
        ma_upper = mapper.get_by_tdx_name("MA")
        ma_mixed = mapper.get_by_tdx_name("Ma")

        assert ma_lower is not None
        assert ma_upper is not None
        assert ma_mixed is not None

        assert ma_lower == ma_upper == ma_mixed


class TestCodeGenerator:
    """代码生成器测试"""

    def test_simple_expression(self):
        """测试简单表达式生成"""
        lexer = FormulaLexer("1 + 2")
        tokens = lexer.tokenize()
        parser = FormulaParser(tokens)
        ast = parser.parse()

        generator = PythonExpressionGenerator()
        code = generator.generate(ast[0])

        assert code == "(1 + 2)"

    def test_function_call_expression(self):
        """测试函数调用表达式生成"""
        lexer = FormulaLexer("MA(CLOSE, 5)")
        tokens = lexer.tokenize()
        parser = FormulaParser(tokens)
        ast = parser.parse()

        generator = PythonExpressionGenerator()
        code = generator.generate(ast[0])

        assert "ma" in code.lower()
        assert "CLOSE" in code
        assert "5" in code

    def test_complex_expression(self):
        """测试复杂表达式生成"""
        lexer = FormulaLexer("MA(CLOSE, 5) > MA(CLOSE, 10)")
        tokens = lexer.tokenize()
        parser = FormulaParser(tokens)
        ast = parser.parse()

        generator = PythonExpressionGenerator()
        code = generator.generate(ast[0])

        assert ">" in code
        assert "ma" in code.lower()


class TestIntegration:
    """集成测试"""

    def test_complete_conversion(self):
        """测试完整的公式转换流程"""
        from vnpy.tools.formula_parser.code_generator import convert_formula_to_expression

        formula = "MA(CLOSE, 5)"
        python_expr = convert_formula_to_expression(formula)

        assert "ma" in python_expr.lower()
        assert "CLOSE" in python_expr

    def test_ma_cross_strategy(self):
        """测试均线金叉策略转换"""
        from vnpy.tools.formula_parser.code_generator import convert_formula_to_expression

        formula = "CROSS(MA(CLOSE, 5), MA(CLOSE, 10))"
        python_expr = convert_formula_to_expression(formula)

        assert "cross" in python_expr.lower()

    def test_complex_strategy(self):
        """测试复杂策略转换"""
        from vnpy.tools.formula_parser.code_generator import convert_formula_to_expression

        formula = "MA(CLOSE, 5) > MA(CLOSE, 10) && VOLUME > MA(VOLUME, 5)"
        python_expr = convert_formula_to_expression(formula)

        assert "and" in python_expr.lower()
        assert "ma" in python_expr.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
