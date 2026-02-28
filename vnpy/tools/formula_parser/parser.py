# -*- coding: utf-8 -*-
"""
通达信公式语法分析器

将token序列转换为抽象语法树(AST)
"""

from typing import List, Optional, Union
from .lexer import Token, TokenType
from .ast_nodes import *


class FormulaParser:
    """通达信公式语法分析器"""

    def __init__(self, tokens: List[Token]):
        """
        初始化语法分析器

        Args:
            tokens: 词法分析得到的token列表
        """
        self.tokens = tokens
        self.pos = 0
        self.current_token = self.tokens[0] if tokens else None

    def error(self, message: str = "语法错误"):
        """抛出语法错误"""
        line = self.current_token.line if self.current_token else 0
        column = self.current_token.column if self.current_token else 0
        raise SyntaxError(f"语法错误 [{line}:{column}]: {message}")

    def advance(self) -> None:
        """前进到下一个token"""
        self.pos += 1
        if self.pos < len(self.tokens):
            self.current_token = self.tokens[self.pos]
        else:
            self.current_token = None

    def expect(self, token_type: TokenType) -> Token:
        """
        期望特定类型的token，如果不是则报错

        Args:
            token_type: 期望的token类型

        Returns:
            当前token
        """
        if self.current_token is None:
            self.error(f"意外的文件结束，期望: {token_type}")

        if self.current_token.type != token_type:
            self.error(f"期望 {token_type}，但得到 {self.current_token.type}")

        token = self.current_token
        self.advance()
        return token

    def peek(self, offset: int = 1) -> Optional[Token]:
        """查看向前第n个token"""
        peek_pos = self.pos + offset
        if peek_pos >= len(self.tokens):
            return None
        return self.tokens[peek_pos]

    def parse(self) -> List[ASTNode]:
        """
        解析整个公式

        Returns:
            AST节点列表
        """
        statements = []

        while self.current_token is not None and self.current_token.type != TokenType.EOF:
            # 变量定义
            if self.current_token.type == TokenType.VAR:
                statements.append(self.parse_variable_declaration())
            # 赋值语句: 检查是否是 IDENTIFIER : 模式
            elif self.current_token.type == TokenType.IDENTIFIER:
                # Look ahead to check if this is an assignment
                if self.peek() and self.peek().type == TokenType.COLON:
                    statements.append(self.parse_assignment())
                else:
                    statements.append(self.parse_expression())
            else:
                statements.append(self.parse_expression())

            # 可选的分号
            if self.current_token and self.current_token.type == TokenType.SEMICOLON:
                self.advance()

        return statements

    def parse_variable_declaration(self) -> VariableNode:
        """
        解析变量声明语句

        格式: VAR 变量名;
        """
        var_token = self.current_token
        self.expect(TokenType.VAR)

        if self.current_token is None or self.current_token.type != TokenType.IDENTIFIER:
            self.error("变量声明需要标识符")

        var_name = self.current_token.value
        self.advance()

        node = VariableNode(var_name)
        node.line = var_token.line
        node.column = var_token.column
        return node

    def parse_assignment(self) -> AssignmentNode:
        """
        解析赋值语句

        格式: 变量名 : 表达式;
        """
        # 左值：变量名
        if self.current_token is None or self.current_token.type != TokenType.IDENTIFIER:
            self.error("赋值语句需要变量名")

        var_name = self.current_token.value
        line, column = self.current_token.line, self.current_token.column
        self.advance()

        # 赋值符号
        self.expect(TokenType.COLON)

        # 右值：表达式
        expression = self.parse_expression()

        node = AssignmentNode(var_name, expression)
        node.line = line
        node.column = column
        return node

    def parse_expression(self) -> ASTNode:
        """
        解析表达式

        处理逻辑或运算 ||
        """
        return self.parse_logical_or()

    def parse_logical_or(self) -> ASTNode:
        """
        解析逻辑或表达式

        || 运算，左结合
        """
        left = self.parse_logical_and()

        while self.current_token and self.current_token.type == TokenType.OR:
            op_token = self.current_token
            self.advance()
            right = self.parse_logical_and()
            node = BinaryOpNode(left, op_token.value, right)
            node.line = op_token.line
            node.column = op_token.column
            left = node

        return left

    def parse_logical_and(self) -> ASTNode:
        """
        解析逻辑与表达式

        && 运算，左结合
        """
        left = self.parse_equality()

        while self.current_token and self.current_token.type == TokenType.AND:
            op_token = self.current_token
            self.advance()
            right = self.parse_equality()
            node = BinaryOpNode(left, op_token.value, right)
            node.line = op_token.line
            node.column = op_token.column
            left = node

        return left

    def parse_equality(self) -> ASTNode:
        """
        解析相等性表达式

        ==, != 运算，左结合
        """
        left = self.parse_comparison()

        while self.current_token and self.current_token.type in [TokenType.EQUAL, TokenType.NOT_EQUAL]:
            op_token = self.current_token
            self.advance()
            right = self.parse_comparison()
            node = BinaryOpNode(left, op_token.value, right)
            node.line = op_token.line
            node.column = op_token.column
            left = node

        return left

    def parse_comparison(self) -> ASTNode:
        """
        解析比较表达式

        >, <, >=, <= 运算，左结合
        """
        left = self.parse_additive()

        while self.current_token and self.current_token.type in [
            TokenType.GREATER,
            TokenType.LESS,
            TokenType.GREATER_EQUAL,
            TokenType.LESS_EQUAL
        ]:
            op_token = self.current_token
            self.advance()
            right = self.parse_additive()
            node = BinaryOpNode(left, op_token.value, right)
            node.line = op_token.line
            node.column = op_token.column
            left = node

        return left

    def parse_additive(self) -> ASTNode:
        """
        解析加减表达式

        +, - 运算，左结合
        """
        left = self.parse_multiplicative()

        while self.current_token and self.current_token.type in [TokenType.PLUS, TokenType.MINUS]:
            op_token = self.current_token
            self.advance()
            right = self.parse_multiplicative()
            node = BinaryOpNode(left, op_token.value, right)
            node.line = op_token.line
            node.column = op_token.column
            left = node

        return left

    def parse_multiplicative(self) -> ASTNode:
        """
        解析乘除模表达式

        *, /, % 运算，左结合
        """
        left = self.parse_unary()

        while self.current_token and self.current_token.type in [
            TokenType.MULTIPLY,
            TokenType.DIVIDE,
            TokenType.MODULO
        ]:
            op_token = self.current_token
            self.advance()
            right = self.parse_unary()
            node = BinaryOpNode(left, op_token.value, right)
            node.line = op_token.line
            node.column = op_token.column
            left = node

        return left

    def parse_unary(self) -> ASTNode:
        """
        解析一元表达式

        +, -, ! 运算
        """
        if self.current_token and self.current_token.type in [TokenType.PLUS, TokenType.MINUS, TokenType.NOT]:
            op_token = self.current_token
            self.advance()
            operand = self.parse_unary()
            node = UnaryOpNode(op_token.value, operand)
            node.line = op_token.line
            node.column = op_token.column
            return node

        return self.parse_postfix()

    def parse_postfix(self) -> ASTNode:
        """
        解析后缀表达式

        函数调用: IDENTIFIER ( 参数列表 )
        数组访问: IDENTIFIER [ 索引 ]
        """
        node = self.parse_primary()

        while self.current_token:
            # 函数调用
            if self.current_token.type == TokenType.LPAREN:
                line, column = self.current_token.line, self.current_token.column
                self.advance()
                args = []

                if self.current_token and self.current_token.type != TokenType.RPAREN:
                    args.append(self.parse_expression())
                    while self.current_token and self.current_token.type == TokenType.COMMA:
                        self.advance()
                        args.append(self.parse_expression())

                self.expect(TokenType.RPAREN)
                call_node = FunctionCallNode(node, args)
                call_node.line = line
                call_node.column = column
                node = call_node

            # 数组访问
            elif self.current_token.type == TokenType.LBRACKET:
                line, column = self.current_token.line, self.current_token.column
                self.advance()
                index = self.parse_expression()
                self.expect(TokenType.RBRACKET)
                access_node = ArrayAccessNode(node, index)
                access_node.line = line
                access_node.column = column
                node = access_node

            else:
                break

        return node

    def parse_primary(self) -> ASTNode:
        """
        解析基本表达式

        数字、字符串、标识符、括号表达式
        """
        token = self.current_token

        if token is None:
            self.error("意外的表达式结束")

        # 数字字面量
        if token.type == TokenType.NUMBER:
            self.advance()
            node = NumberNode(token.value)
            node.line = token.line
            node.column = token.column
            return node

        # 字符串字面量
        if token.type == TokenType.STRING:
            self.advance()
            node = StringNode(token.value)
            node.line = token.line
            node.column = token.column
            return node

        # 标识符
        if token.type == TokenType.IDENTIFIER:
            self.advance()
            node = IdentifierNode(token.value)
            node.line = token.line
            node.column = token.column
            return node

        # 括号表达式
        if token.type == TokenType.LPAREN:
            self.advance()
            expr = self.parse_expression()
            self.expect(TokenType.RPAREN)
            return expr

        self.error(f"无法解析的表达式: {token}")
