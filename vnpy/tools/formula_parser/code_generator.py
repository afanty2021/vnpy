# -*- coding: utf-8 -*-
"""
通达信公式代码生成器

将AST转换为vnpy策略Python代码
"""

from typing import List, Optional, Dict, Any
from .ast_nodes import *
from .function_map import FunctionMapper, get_global_mapper


class CodeGenerator:
    """代码生成器"""

    def __init__(self, function_mapper: Optional[FunctionMapper] = None):
        """
        初始化代码生成器

        Args:
            function_mapper: 函数映射器，默认使用全局映射器
        """
        self.function_mapper = function_mapper or get_global_mapper()
        self.indent_level = 0
        self.imports: set = set()
        self.variables: Dict[str, Any] = {}  # 变量类型信息

    def _indent(self) -> str:
        """生成缩进"""
        return "    " * self.indent_level

    def generate(self, ast_nodes: List[ASTNode]) -> str:
        """
        生成完整的Python代码

        Args:
            ast_nodes: AST节点列表

        Returns:
            Python代码字符串
        """
        self.imports = set()
        self.variables = {}

        # 生成导入语句
        code_lines = self._generate_imports()

        # 生成策略类
        code_lines.append("\nclass GeneratedStrategy:\n")
        self.indent_level += 1

        # 生成初始化方法
        code_lines.append(f"{self._indent()}def __init__(self):\n")
        self.indent_level += 1
        code_lines.append(f"{self._indent()}pass\n")
        self.indent_level -= 2

        # 生成计算方法
        code_lines.append(f"\n{self._indent()}def calculate(self, data):\n")
        self.indent_level += 1

        # 为每个AST节点生成代码
        for node in ast_nodes:
            code_lines.append(self._generate_node(node))
            code_lines.append("\n")

        self.indent_level -= 1

        return "".join(code_lines)

    def _generate_imports(self) -> List[str]:
        """生成导入语句"""
        imports = [
            "import pandas as pd\n",
            "import numpy as np\n",
            "from vnpy.trader.object import BarData, TickData\n",
        ]

        # 根据使用的函数添加额外的导入
        if any(func_name.lower() in ["ma", "ema", "sma", "std", "var"] for func_name in self.variables.keys()):
            imports.append("from vnpy.indicator import *\n")

        return imports

    def _generate_node(self, node: ASTNode) -> str:
        """为AST节点生成代码"""
        return node.accept(self)

    def visit_number(self, node: NumberNode) -> str:
        """生成数字字面量代码"""
        return f"{self._indent()}# {node.value}\n"

    def visit_string(self, node: StringNode) -> str:
        """生成字符串字面量代码"""
        return f"{self._indent()}# '{node.value}'\n"

    def visit_identifier(self, node: IdentifierNode) -> str:
        """生成标识符代码"""
        return f"{self._indent()}data['{node.name}']\n"

    def visit_binary_op(self, node: BinaryOpNode) -> str:
        """生成二元运算代码"""
        left = node.left.accept(self).strip()
        right = node.right.accept(self).strip()

        # Python运算符映射
        op_map = {
            "+": "+",
            "-": "-",
            "*": "*",
            "/": "/",
            "%": "%",
            "==": "==",
            "!=": "!=",
            ">": ">",
            "<": "<",
            ">=": ">=",
            "<=": "<=",
            "&&": " and ",
            "||": " or ",
        }

        op = op_map.get(node.operator, node.operator)
        return f"{self._indent()}({left} {op} {right})\n"

    def visit_unary_op(self, node: UnaryOpNode) -> str:
        """生成一元运算代码"""
        operand = node.operand.accept(self).strip()

        if node.operator == "!":
            op = "not "
        else:
            op = node.operator

        return f"{self._indent()}({op}{operand})\n"

    def visit_function_call(self, node: FunctionCallNode) -> str:
        """生成函数调用代码"""
        func_name = node.function
        if isinstance(func_name, IdentifierNode):
            func_name = func_name.name

        # 检查是否是通达信函数
        mapped_func = self.function_mapper.translate(func_name)
        if mapped_func:
            func_name = mapped_func

        # 生成参数代码
        args = []
        for arg in node.arguments:
            arg_code = arg.accept(self).strip()
            args.append(arg_code)

        # 生成函数调用
        return f"{self._indent()}{func_name}({', '.join(args)})\n"

    def visit_array_access(self, node: ArrayAccessNode) -> str:
        """生成数组访问代码"""
        array_name = node.array
        if isinstance(array_name, IdentifierNode):
            array_name = array_name.name

        index_code = node.index.accept(self).strip()
        return f"{self._indent()}{array_name}[{index_code}]\n"

    def visit_variable(self, node: VariableNode) -> str:
        """生成变量声明代码"""
        return f"{self._indent()}# Variable: {node.name}\n"

    def visit_assignment(self, node: AssignmentNode) -> str:
        """生成赋值语句代码"""
        value_code = node.value.accept(self).strip()
        self.variables[node.name] = "auto"  # 记录变量

        # 如果是赋值给data的列
        if node.name.lower() in ["open", "high", "low", "close", "volume"]:
            return f"{self._indent()}data['{node.name}'] = {value_code}\n"

        return f"{self._indent()}{node.name} = {value_code}\n"

    def visit_draw(self, node: DrawNode) -> str:
        """生成DRAW语句代码"""
        expr_code = node.expression.accept(self).strip()

        # DRAW语句转换为注释或打印
        return f"{self._indent()}# DRAW: {expr_code}\n"

    def visit_condition(self, node: ConditionNode) -> str:
        """生成条件表达式代码"""
        condition = node.condition.accept(self).strip()
        true_expr = node.true_expr.accept(self).strip()
        false_expr = node.false_expr.accept(self).strip()

        return f"{self._indent()}({true_expr} if {condition} else {false_expr})\n"


class PythonExpressionGenerator:
    """Python表达式生成器（简化版）"""

    def __init__(self, function_mapper: Optional[FunctionMapper] = None):
        self.function_mapper = function_mapper or get_global_mapper()

    def generate(self, node: ASTNode) -> str:
        """生成Python表达式字符串"""
        return node.accept(self)

    def visit_number(self, node: NumberNode) -> str:
        return str(node.value)

    def visit_string(self, node: StringNode) -> str:
        return f'"{node.value}"'

    def visit_identifier(self, node: IdentifierNode) -> str:
        return node.name

    def visit_binary_op(self, node: BinaryOpNode) -> str:
        left = node.left.accept(self)
        right = node.right.accept(self)

        # Python运算符映射
        op_map = {
            "&&": "and",
            "||": "or",
        }

        op = op_map.get(node.operator, node.operator)
        return f"({left} {op} {right})"

    def visit_unary_op(self, node: UnaryOpNode) -> str:
        operand = node.operand.accept(self)
        op = "not " if node.operator == "!" else node.operator
        return f"{op}{operand}"

    def visit_function_call(self, node: FunctionCallNode) -> str:
        func_name = node.function
        if isinstance(func_name, IdentifierNode):
            func_name = func_name.name

        # 转换通达信函数名
        mapped_func = self.function_mapper.translate(func_name)
        if mapped_func:
            func_name = mapped_func

        args = [arg.accept(self) for arg in node.arguments]
        return f"{func_name}({', '.join(args)})"

    def visit_array_access(self, node: ArrayAccessNode) -> str:
        array_name = node.array
        if isinstance(array_name, IdentifierNode):
            array_name = array_name.name

        index = node.index.accept(self)
        return f"{array_name}[{index}]"

    def visit_variable(self, node: VariableNode) -> str:
        return node.name

    def visit_assignment(self, node: AssignmentNode) -> str:
        value = node.value.accept(self)
        return f"{node.name} = {value}"

    def visit_draw(self, node: DrawNode) -> str:
        expr = node.expression.accept(self)
        return f"# DRAW {expr}"

    def visit_condition(self, node: ConditionNode) -> str:
        condition = node.condition.accept(self)
        true_expr = node.true_expr.accept(self)
        false_expr = node.false_expr.accept(self)
        return f"({true_expr} if {condition} else {false_expr})"


def convert_formula_to_python(formula: str) -> str:
    """
    将通达信公式转换为Python代码

    Args:
        formula: 通达信公式字符串

    Returns:
        Python代码字符串
    """
    from .lexer import FormulaLexer
    from .parser import FormulaParser

    # 词法分析
    lexer = FormulaLexer(formula)
    tokens = lexer.tokenize()

    # 语法分析
    parser = FormulaParser(tokens)
    ast_nodes = parser.parse()

    # 代码生成
    generator = CodeGenerator()
    return generator.generate(ast_nodes)


def convert_formula_to_expression(formula: str) -> str:
    """
    将通达信公式转换为Python表达式

    Args:
        formula: 通达信公式字符串

    Returns:
        Python表达式字符串
    """
    from .lexer import FormulaLexer
    from .parser import FormulaParser

    # 词法分析
    lexer = FormulaLexer(formula)
    tokens = lexer.tokenize()

    # 语法分析
    parser = FormulaParser(tokens)
    ast_nodes = parser.parse()

    if len(ast_nodes) == 0:
        return ""

    # 表达式生成（简化版）
    generator = PythonExpressionGenerator()
    return generator.generate(ast_nodes[0])
