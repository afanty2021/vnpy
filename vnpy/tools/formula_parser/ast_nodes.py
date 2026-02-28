# -*- coding: utf-8 -*-
"""
通达信公式AST节点定义

定义抽象语法树的所有节点类型
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Any, Optional


class ASTNode(ABC):
    """AST节点基类"""

    def __init__(self, line: int = 0, column: int = 0):
        self.line = line
        self.column = column

    @abstractmethod
    def accept(self, visitor: 'ASTVisitor') -> Any:
        """接受访问器"""
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"


class ASTVisitor(ABC):
    """AST访问器基类"""

    @abstractmethod
    def visit(self, node: ASTNode) -> Any:
        """访问节点"""
        pass


@dataclass
class NumberNode(ASTNode):
    """数字字面量节点"""
    value: float

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_number(self)

    def __repr__(self) -> str:
        return f"NumberNode({self.value})"


@dataclass
class StringNode(ASTNode):
    """字符串字面量节点"""
    value: str

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_string(self)

    def __repr__(self) -> str:
        return f"StringNode('{self.value}')"


@dataclass
class IdentifierNode(ASTNode):
    """标识符节点"""
    name: str

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_identifier(self)

    def __repr__(self) -> str:
        return f"IdentifierNode('{self.name}')"


@dataclass
class BinaryOpNode(ASTNode):
    """二元运算节点"""
    left: ASTNode
    operator: str
    right: ASTNode

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_binary_op(self)

    def __repr__(self) -> str:
        return f"BinaryOpNode({self.left}, {self.operator}, {self.right})"


@dataclass
class UnaryOpNode(ASTNode):
    """一元运算节点"""
    operator: str
    operand: ASTNode

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_unary_op(self)

    def __repr__(self) -> str:
        return f"UnaryOpNode({self.operator}, {self.operand})"


@dataclass
class FunctionCallNode(ASTNode):
    """函数调用节点"""
    function: ASTNode  # 函数名（IdentifierNode）
    arguments: List[ASTNode]

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_function_call(self)

    def __repr__(self) -> str:
        args = ", ".join(str(arg) for arg in self.arguments)
        return f"FunctionCallNode({self.function}, [{args}])"


@dataclass
class ArrayAccessNode(ASTNode):
    """数组访问节点"""
    array: ASTNode  # 数组名（IdentifierNode）
    index: ASTNode  # 索引表达式

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_array_access(self)

    def __repr__(self) -> str:
        return f"ArrayAccessNode({self.array}, {self.index})"


@dataclass
class VariableNode(ASTNode):
    """变量声明节点"""
    name: str

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_variable(self)

    def __repr__(self) -> str:
        return f"VariableNode('{self.name}')"


@dataclass
class AssignmentNode(ASTNode):
    """赋值语句节点"""
    name: str
    value: ASTNode

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_assignment(self)

    def __repr__(self) -> str:
        return f"AssignmentNode('{self.name}', {self.value})"


@dataclass
class DrawNode(ASTNode):
    """DRAW语句节点（用于绘制图形）"""
    expression: ASTNode
    color: Optional[str] = None
    style: Optional[str] = None

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_draw(self)

    def __repr__(self) -> str:
        color = f", color='{self.color}'" if self.color else ""
        style = f", style='{self.style}'" if self.style else ""
        return f"DrawNode({self.expression}{color}{style})"


@dataclass
class ConditionNode(ASTNode):
    """条件表达式节点

    格式: 条件 ? 真值表达式 : 假值表达式
    """
    condition: ASTNode
    true_expr: ASTNode
    false_expr: ASTNode

    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_condition(self)

    def __repr__(self) -> str:
        return f"ConditionNode({self.condition}, {self.true_expr}, {self.false_expr})"


class ASTPrinter(ASTVisitor):
    """AST打印器，用于调试"""

    def __init__(self, indent: int = 0):
        self.indent = indent

    def _indent(self) -> str:
        return "  " * self.indent

    def visit(self, node: ASTNode) -> str:
        return node.accept(self)

    def visit_number(self, node: NumberNode) -> str:
        return f"{self._indent()}Number({node.value})"

    def visit_string(self, node: StringNode) -> str:
        return f"{self._indent()}String('{node.value}')"

    def visit_identifier(self, node: IdentifierNode) -> str:
        return f"{self._indent()}Identifier('{node.name}')"

    def visit_binary_op(self, node: BinaryOpNode) -> str:
        result = f"{self._indent()}BinaryOp('{node.operator}'):\n"
        self.indent += 1
        result += node.left.accept(self) + "\n"
        result += node.right.accept(self)
        self.indent -= 1
        return result

    def visit_unary_op(self, node: UnaryOpNode) -> str:
        result = f"{self._indent()}UnaryOp('{node.operator}'):\n"
        self.indent += 1
        result += node.operand.accept(self)
        self.indent -= 1
        return result

    def visit_function_call(self, node: FunctionCallNode) -> str:
        result = f"{self._indent()}FunctionCall:\n"
        self.indent += 1
        result += f"{self._indent()}Function: {node.function.accept(self)}\n"
        result += f"{self._indent()}Arguments:\n"
        self.indent += 1
        for arg in node.arguments:
            result += arg.accept(self) + "\n"
        self.indent -= 2
        return result.rstrip()

    def visit_array_access(self, node: ArrayAccessNode) -> str:
        result = f"{self._indent()}ArrayAccess:\n"
        self.indent += 1
        result += f"{self._indent()}Array: {node.array.accept(self)}\n"
        result += f"{self._indent()}Index:\n"
        self.indent += 1
        result += node.index.accept(self)
        self.indent -= 2
        return result

    def visit_variable(self, node: VariableNode) -> str:
        return f"{self._indent()}Variable('{node.name}')"

    def visit_assignment(self, node: AssignmentNode) -> str:
        result = f"{self._indent()}Assignment('{node.name}'):\n"
        self.indent += 1
        result += node.value.accept(self)
        self.indent -= 1
        return result

    def visit_draw(self, node: DrawNode) -> str:
        result = f"{self._indent()}Draw:\n"
        self.indent += 1
        result += node.expression.accept(self)
        self.indent -= 1
        return result

    def visit_condition(self, node: ConditionNode) -> str:
        result = f"{self._indent()}Condition:\n"
        self.indent += 1
        result += f"{self._indent()}Condition:\n{node.condition.accept(self)}\n"
        result += f"{self._indent()}True:\n{node.true_expr.accept(self)}\n"
        result += f"{self._indent()}False:\n{node.false_expr.accept(self)}"
        self.indent -= 1
        return result
