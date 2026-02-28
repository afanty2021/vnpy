# -*- coding: utf-8 -*-
"""
通达信公式词法分析器

将通达信公式字符串转换为token序列，为语法分析做准备。
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional


class TokenType(Enum):
    """Token类型枚举"""
    # 运算符
    PLUS = auto()          # +
    MINUS = auto()         # -
    MULTIPLY = auto()      # *
    DIVIDE = auto()        # /
    MODULO = auto()        # %

    # 比较运算符
    EQUAL = auto()         # ==
    NOT_EQUAL = auto()     # !=
    GREATER = auto()       # >
    LESS = auto()          # <
    GREATER_EQUAL = auto() # >=
    LESS_EQUAL = auto()    # <=

    # 逻辑运算符
    AND = auto()           # &&
    OR = auto()            # ||
    NOT = auto()           # !

    # 赋值
    ASSIGN = auto()        # :
    COLON = auto()         # : (变量声明)

    # 分隔符
    LPAREN = auto()        # (
    RPAREN = auto()        # )
    LBRACKET = auto()      # [
    RBRACKET = auto()      # ]
    COMMA = auto()         # ,
    SEMICOLON = auto()     # ;

    # 字面量
    NUMBER = auto()        # 数字
    STRING = auto()        # 字符串
    IDENTIFIER = auto()    # 标识符

    # 关键字
    VAR = auto()           # 变量定义
    DRAW = auto()          # DRAW函数
    COLOR = auto()         # 颜色关键字

    # 特殊
    EOF = auto()           # 结束符
    UNKNOWN = auto()       # 未知字符


@dataclass
class Token:
    """Token数据类"""
    type: TokenType
    value: any
    line: int = 1
    column: int = 1

    def __repr__(self) -> str:
        return f"Token({self.type}, {self.value})"


class FormulaLexer:
    """通达信公式词法分析器"""

    # 关键字映射
    KEYWORDS = {
        "VAR": TokenType.VAR,
        "DRAW": TokenType.DRAW,
        "COLOR": TokenType.COLOR,
        "RED": TokenType.COLOR,
        "GREEN": TokenType.COLOR,
        "BLUE": TokenType.COLOR,
        "YELLOW": TokenType.COLOR,
        "CYAN": TokenType.COLOR,
        "MAGENTA": TokenType.COLOR,
        "WHITE": TokenType.COLOR,
    }

    # 运算符映射
    OPERATORS = {
        "+": TokenType.PLUS,
        "-": TokenType.MINUS,
        "*": TokenType.MULTIPLY,
        "/": TokenType.DIVIDE,
        "%": TokenType.MODULO,
        "=": TokenType.ASSIGN,
        ":": TokenType.COLON,
        "(": TokenType.LPAREN,
        ")": TokenType.RPAREN,
        "[": TokenType.LBRACKET,
        "]": TokenType.RBRACKET,
        ",": TokenType.COMMA,
        ";": TokenType.SEMICOLON,
        ">": TokenType.GREATER,
        "<": TokenType.LESS,
        "!": TokenType.NOT,
    }

    # 多字符运算符
    MULTI_CHAR_OPS = {
        "==": TokenType.EQUAL,
        "!=": TokenType.NOT_EQUAL,
        ">=": TokenType.GREATER_EQUAL,
        "<=": TokenType.LESS_EQUAL,
        "&&": TokenType.AND,
        "||": TokenType.OR,
    }

    def __init__(self, text: str):
        """
        初始化词法分析器

        Args:
            text: 待分析的公式字符串
        """
        self.text = text
        self.pos = 0
        self.line = 1
        self.column = 1
        self.current_char = self.text[self.pos] if self.text else None

    def error(self, message: str = "非法字符"):
        """抛出词法错误"""
        raise SyntaxError(f"词法错误 [{self.line}:{self.column}]: {message}")

    def advance(self) -> None:
        """前进到下一个字符"""
        if self.current_char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1

        self.pos += 1
        if self.pos >= len(self.text):
            self.current_char = None
        else:
            self.current_char = self.text[self.pos]

    def peek(self, offset: int = 1) -> Optional[str]:
        """查看向前第n个字符"""
        peek_pos = self.pos + offset
        if peek_pos >= len(self.text):
            return None
        return self.text[peek_pos]

    def skip_whitespace(self) -> None:
        """跳过空白字符"""
        while self.current_char is not None and self.current_char.isspace():
            self.advance()

    def skip_comment(self) -> None:
        """跳过注释（//单行注释）"""
        if self.current_char == "/" and self.peek() == "/":
            while self.current_char is not None and self.current_char != "\n":
                self.advance()

    def number(self) -> Token:
        """读取数字"""
        start_line, start_column = self.line, self.column
        result = ""

        while self.current_char is not None and (self.current_char.isdigit() or self.current_char == "."):
            result += self.current_char
            self.advance()

        # 尝试转换为整数或浮点数
        try:
            if "." in result:
                value = float(result)
            else:
                value = int(result)
        except ValueError:
            self.error(f"无效的数字格式: {result}")

        return Token(TokenType.NUMBER, value, start_line, start_column)

    def string(self) -> Token:
        """读取字符串"""
        start_line, start_column = self.line, self.column
        quote_char = self.current_char
        self.advance()  # 跳过开始引号

        result = ""
        while self.current_char is not None and self.current_char != quote_char:
            result += self.current_char
            self.advance()

        if self.current_char != quote_char:
            self.error("未闭合的字符串")

        self.advance()  # 跳过结束引号
        return Token(TokenType.STRING, result, start_line, start_column)

    def identifier(self) -> Token:
        """读取标识符或关键字"""
        start_line, start_column = self.line, self.column
        result = ""

        # 标识符可以包含字母、数字、下划线
        while self.current_char is not None and (self.current_char.isalnum() or self.current_char == "_"):
            result += self.current_char
            self.advance()

        # 检查是否是关键字
        upper_result = result.upper()
        if upper_result in self.KEYWORDS:
            return Token(self.KEYWORDS[upper_result], upper_result, start_line, start_column)

        return Token(TokenType.IDENTIFIER, result, start_line, start_column)

    def get_next_token(self) -> Token:
        """获取下一个token"""
        while self.current_char is not None:
            # 跳过空白和注释
            if self.current_char.isspace():
                self.skip_whitespace()
                continue

            # 处理注释
            if self.current_char == "/" and self.peek() == "/":
                self.skip_comment()
                continue

            start_line, start_column = self.line, self.column

            # 处理多字符运算符
            two_chars = self.current_char + (self.peek() or "")
            if two_chars in self.MULTI_CHAR_OPS:
                self.advance()
                self.advance()
                return Token(self.MULTI_CHAR_OPS[two_chars], two_chars, start_line, start_column)

            # 处理单字符运算符
            if self.current_char in self.OPERATORS:
                char = self.current_char
                self.advance()
                return Token(self.OPERATORS[char], char, start_line, start_column)

            # 处理数字
            if self.current_char.isdigit():
                return self.number()

            # 处理字符串
            if self.current_char in ["'", '"']:
                return self.string()

            # 处理标识符
            if self.current_char.isalpha() or self.current_char == "_":
                return self.identifier()

            # 未知字符
            self.error(f"无法识别的字符: '{self.current_char}'")

        return Token(TokenType.EOF, None, self.line, self.column)

    def tokenize(self) -> List[Token]:
        """
        对整个字符串进行词法分析

        Returns:
            Token列表
        """
        tokens = []
        token = self.get_next_token()

        while token.type != TokenType.EOF:
            tokens.append(token)
            token = self.get_next_token()

        tokens.append(token)  # 添加EOF token
        return tokens
