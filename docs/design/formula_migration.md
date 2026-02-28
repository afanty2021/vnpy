# 通达信公式策略迁移工具设计方案

> 更新时间：2026-02-28

## Context

**问题背景**：
1. **大量存量策略**：大量投资者熟悉通达信公式语法，积累了丰富的技术分析策略
2. **迁移成本高**：手动将通达信公式转换为 vnpy 策略需要重新学习 API
3. **语法差异**：通达信公式与 Python/vnpy 语法差异较大

**目标**：设计通达信公式到 vnpy 策略的自动迁移工具，包括：
1. 通达信公式解析器（词法分析 + 语法分析）
2. 函数映射转换器
3. 策略代码生成器
4. 可视化迁移工具

---

## 通达信公式语法特征

### 1. 基本语法

```
// 变量定义（使用 :=）
MA5:=MA(CLOSE,5);
MA10:=MA(CLOSE,10);

// 条件表达式
金叉:CROSS(MA5,MA10);
死叉:CROSS(MA10,MA5);

// 输出指标（使用 :）
BOLL:MA(CLOSE,20);
```

### 2. 内置数据变量

| 通达信变量 | 含义 | vnpy 对应 |
|-----------|------|----------|
| `CLOSE` / `C` | 收盘价 | `bar.close_price` |
| `OPEN` / `O` | 开盘价 | `bar.open_price` |
| `HIGH` / `H` | 最高价 | `bar.high_price` |
| `LOW` / `L` | 最低价 | `bar.low_price` |
| `VOL` / `V` | 成交量 | `bar.volume` |
| `AMOUNT` | 成交额 | `bar.turnover` |

### 3. 常用函数

| 通达信函数 | 功能 | vnpy 对应 |
|-----------|------|----------|
| `MA(X,N)` | 简单移动平均 | `am.sma(N)` |
| `EMA(X,N)` | 指数移动平均 | `am.ema(N)` |
| `MACD(...)` | MACD指标 | `am.macd(...)` |
| `RSI(N)` | 相对强弱指数 | `am.rsi(N)` |
| `KDJ(...)` | KDJ指标 | 需自定义 |
| `CROSS(A,B)` | 金叉判断 | 自定义函数 |
| `REF(X,N)` | N周期前值 | `am.sma(N).shift(N)` |
| `HHV(X,N)` | N周期最高 | `am.high[N:].max()` |
| `LLV(X,N)` | N周期最低 | `am.low[N:].min()` |

---

## 设计方案

### 1. 新增文件

| 文件 | 职责 |
|------|------|
| `vnpy/tools/formula_parser/__init__.py` | 模块导出 |
| `vnpy/tools/formula_parser/lexer.py` | 词法分析器 |
| `vnpy/tools/formula_parser/parser.py` | 语法分析器 |
| `vnpy/tools/formula_parser/ast_nodes.py` | 抽象语法树节点 |
| `vnpy/tools/formula_parser/converter.py` | 函数映射转换器 |
| `vnpy/tools/formula_parser/code_generator.py` | Python代码生成器 |
| `vnpy/tools/formula_parser/function_map.py` | 函数映射表 |

### 2. AST 节点定义

**文件**: `vnpy/tools/formula_parser/ast_nodes.py`

```python
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

class NodeType(Enum):
    """节点类型"""
    PROGRAM = auto()        # 程序根节点
    ASSIGNMENT = auto()     # 赋值语句 (:=)
    OUTPUT = auto()         # 输出语句 (:)
    FUNCTION_CALL = auto()  # 函数调用
    BINARY_OP = auto()      # 二元运算
    UNARY_OP = auto()       # 一元运算
    IDENTIFIER = auto()     # 标识符
    NUMBER = auto()         # 数字
    CONDITION = auto()      # 条件语句
    DRAW_CALL = auto()      # 绘图函数


@dataclass
class ASTNode:
    """AST节点基类"""
    node_type: NodeType
    line: int = 0
    column: int = 0


@dataclass
class NumberNode(ASTNode):
    """数字节点"""
    value: float


@dataclass
class IdentifierNode(ASTNode):
    """标识符节点"""
    name: str


@dataclass
class FunctionCallNode(ASTNode):
    """函数调用节点"""
    function_name: str
    arguments: list[ASTNode]


@dataclass
class BinaryOpNode(ASTNode):
    """二元运算节点"""
    operator: str
    left: ASTNode
    right: ASTNode


@dataclass
class AssignmentNode(ASTNode):
    """赋值语句节点"""
    variable_name: str
    expression: ASTNode
    is_output: bool = False  # True 表示输出指标 (:), False 表示中间变量 (:=)


@dataclass
class ProgramNode(ASTNode):
    """程序根节点"""
    statements: list[ASTNode]
```

### 3. 词法分析器

**文件**: `vnpy/tools/formula_parser/lexer.py`

```python
from dataclasses import dataclass
from enum import Enum, auto

class TokenType(Enum):
    """词法单元类型"""
    # 字面量
    NUMBER = auto()
    STRING = auto()

    # 标识符和关键字
    IDENTIFIER = auto()
    KEYWORD = auto()

    # 运算符
    PLUS = auto()       # +
    MINUS = auto()      # -
    MULTIPLY = auto()   # *
    DIVIDE = auto()     # /
    ASSIGN = auto()     # :=
    OUTPUT = auto()     # :
    COMMA = auto()      # ,
    SEMICOLON = auto()  # ;
    LPAREN = auto()     # (
    RPAREN = auto()     # )

    # 比较运算符
    GT = auto()         # >
    LT = auto()         # <
    GE = auto()         # >=
    LE = auto()         # <=
    EQ = auto()         # =
    NE = auto()         # <>

    # 逻辑运算符
    AND = auto()
    OR = auto()
    NOT = auto()

    # 特殊
    EOF = auto()
    NEWLINE = auto()


@dataclass
class Token:
    """词法单元"""
    type: TokenType
    value: Any
    line: int
    column: int


class FormulaLexer:
    """通达信公式词法分析器"""

    KEYWORDS = {'AND', 'OR', 'NOT', 'IF', 'THEN', 'ELSE'}

    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1

    def tokenize(self) -> list[Token]:
        """将源代码转换为词法单元列表"""
        tokens = []

        while self.pos < len(self.source):
            ch = self.source[self.pos]

            # 跳过空白字符
            if ch.isspace():
                if ch == '\n':
                    self.line += 1
                    self.column = 1
                else:
                    self.column += 1
                self.pos += 1
                continue

            # 注释
            if ch == '/' and self._peek() == '/':
                self._skip_comment()
                continue

            # 数字
            if ch.isdigit() or (ch == '.' and self._peek().isdigit()):
                tokens.append(self._read_number())
                continue

            # 标识符或关键字
            if ch.isalpha() or ch == '_':
                tokens.append(self._read_identifier())
                continue

            # 运算符
            if ch == ':' and self._peek() == '=':
                tokens.append(Token(TokenType.ASSIGN, ':=', self.line, self.column))
                self.pos += 2
                self.column += 2
                continue

            if ch == ':' and self._peek() != '=':
                tokens.append(Token(TokenType.OUTPUT, ':', self.line, self.column))
                self.pos += 1
                self.column += 1
                continue

            # ... 其他运算符处理

        tokens.append(Token(TokenType.EOF, None, self.line, self.column))
        return tokens

    def _read_number(self) -> Token:
        """读取数字"""
        start = self.pos
        while self.pos < len(self.source) and (self.source[self.pos].isdigit() or self.source[self.pos] == '.'):
            self.pos += 1
            self.column += 1
        return Token(TokenType.NUMBER, float(self.source[start:self.pos]), self.line, self.column)

    def _read_identifier(self) -> Token:
        """读取标识符"""
        start = self.pos
        while self.pos < len(self.source) and (self.source[self.pos].isalnum() or self.source[self.pos] == '_'):
            self.pos += 1
            self.column += 1
        name = self.source[start:self.pos]
        if name.upper() in self.KEYWORDS:
            return Token(TokenType.KEYWORD, name.upper(), self.line, self.column)
        return Token(TokenType.IDENTIFIER, name, self.line, self.column)
```

### 4. 函数映射表

**文件**: `vnpy/tools/formula_parser/function_map.py`

```python
from dataclasses import dataclass
from typing import Callable

@dataclass
class FunctionMapping:
    """函数映射配置"""
    tdx_name: str                    # 通达信函数名
    vnpy_name: str                   # vnpy 对应函数名
    param_transform: Callable | None # 参数转换函数
    requires_array_manager: bool = True  # 是否需要 ArrayManager


# 函数映射表
FUNCTION_MAPPINGS: dict[str, FunctionMapping] = {
    # 移动平均类
    "MA": FunctionMapping(
        tdx_name="MA",
        vnpy_name="sma",
        param_transform=lambda args: args,  # MA(X, N) -> sma(N)
    ),
    "EMA": FunctionMapping(
        tdx_name="EMA",
        vnpy_name="ema",
    ),
    "SMA": FunctionMapping(
        tdx_name="SMA",
        vnpy_name="wma",  # 加权移动平均
    ),

    # MACD
    "MACD": FunctionMapping(
        tdx_name="MACD",
        vnpy_name="macd",
        param_transform=lambda args: (args[0] if len(args) > 0 else 12,
                                       args[1] if len(args) > 1 else 26,
                                       args[2] if len(args) > 2 else 9),
    ),

    # RSI
    "RSI": FunctionMapping(
        tdx_name="RSI",
        vnpy_name="rsi",
    ),

    # 布林带
    "STD": FunctionMapping(
        tdx_name="STD",
        vnpy_name="std",
    ),

    # 极值函数
    "HHV": FunctionMapping(
        tdx_name="HHV",
        vnpy_name="ts_max",  # 时序最大值
        requires_array_manager=False,
    ),
    "LLV": FunctionMapping(
        tdx_name="LLV",
        vnpy_name="ts_min",
        requires_array_manager=False,
    ),

    # 引用函数
    "REF": FunctionMapping(
        tdx_name="REF",
        vnpy_name="ts_delay",
        requires_array_manager=False,
    ),

    # 交叉函数
    "CROSS": FunctionMapping(
        tdx_name="CROSS",
        vnpy_name="_cross",  # 自定义交叉函数
        requires_array_manager=False,
    ),

    # 条件函数
    "IF": FunctionMapping(
        tdx_name="IF",
        vnpy_name="np.where",
        requires_array_manager=False,
    ),

    # 统计函数
    "COUNT": FunctionMapping(
        tdx_name="COUNT",
        vnpy_name="ts_sum",  # 时序求和
    ),
    "SUM": FunctionMapping(
        tdx_name="SUM",
        vnpy_name="ts_sum",
    ),
    "MAX": FunctionMapping(
        tdx_name="MAX",
        vnpy_name="np.maximum",
        requires_array_manager=False,
    ),
    "MIN": FunctionMapping(
        tdx_name="MIN",
        vnpy_name="np.minimum",
        requires_array_manager=False,
    ),
    "ABS": FunctionMapping(
        tdx_name="ABS",
        vnpy_name="np.abs",
        requires_array_manager=False,
    ),
}


# 数据变量映射
DATA_VARIABLE_MAPPINGS: dict[str, str] = {
    "CLOSE": "close_price",
    "C": "close_price",
    "OPEN": "open_price",
    "O": "open_price",
    "HIGH": "high_price",
    "H": "high_price",
    "LOW": "low_price",
    "L": "low_price",
    "VOL": "volume",
    "V": "volume",
    "AMOUNT": "turnover",
}
```

### 5. 代码生成器

**文件**: `vnpy/tools/formula_parser/code_generator.py`

```python
from string import Template

STRATEGY_TEMPLATE = Template('''
"""
自动生成的 vnpy 策略 - 基于通达信公式迁移
原始公式: ${formula_name}
生成时间: ${generated_time}
"""
from vnpy.trader.utility import ArrayManager
from vnpy_ctastrategy import CtaTemplate


class ${class_name}(CtaTemplate):
    """${class_name} - 迁移自通达信公式"""

    # 策略作者
    author = "Formula Migrator"

    # 策略参数
    ${parameters}

    # 策略变量
    ${variables}

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        # K线管理器
        self.am = ArrayManager(size=${array_size})

    def on_init(self):
        """策略初始化"""
        self.write_log("策略初始化")

    def on_start(self):
        """策略启动"""
        self.write_log("策略启动")

    def on_stop(self):
        """策略停止"""
        self.write_log("策略停止")

    def on_bar(self, bar):
        """K线数据更新"""
        # 更新K线管理器
        self.am.update_bar(bar)

        if not self.am.inited:
            return

        # 计算指标
        ${indicator_calculation}

        # 交易逻辑
        ${trading_logic}

    ${custom_functions}
''')


class CodeGenerator:
    """Python代码生成器"""

    def __init__(self, ast_root: ProgramNode, formula_name: str):
        self.ast = ast_root
        self.formula_name = formula_name
        self.variables = {}      # 变量定义
        self.outputs = {}        # 输出指标
        self.parameters = {}     # 可调参数
        self.signals = {}        # 交易信号

    def generate(self) -> str:
        """生成完整的策略代码"""
        # 分析AST，提取变量和信号
        self._analyze_ast()

        # 生成参数定义
        params_code = self._generate_parameters()

        # 生成变量定义
        vars_code = self._generate_variables()

        # 生成指标计算代码
        indicators_code = self._generate_indicators()

        # 生成交易逻辑代码
        trading_code = self._generate_trading_logic()

        # 生成辅助函数
        custom_funcs = self._generate_custom_functions()

        return STRATEGY_TEMPLATE.substitute(
            formula_name=self.formula_name,
            generated_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            class_name=self._generate_class_name(),
            parameters=params_code,
            variables=vars_code,
            array_size=self._calculate_array_size(),
            indicator_calculation=indicators_code,
            trading_logic=trading_code,
            custom_functions=custom_funcs,
        )

    def _analyze_ast(self):
        """分析AST，提取关键信息"""
        for stmt in self.ast.statements:
            if isinstance(stmt, AssignmentNode):
                if stmt.is_output:
                    # 输出指标
                    self.outputs[stmt.variable_name] = stmt.expression
                else:
                    # 中间变量
                    self.variables[stmt.variable_name] = stmt.expression

                # 检测交易信号（通常包含 BUY, SELL 等关键词）
                if self._is_signal_variable(stmt.variable_name):
                    self.signals[stmt.variable_name] = stmt.expression

    def _is_signal_variable(self, name: str) -> bool:
        """判断是否为交易信号变量"""
        signal_keywords = ['BUY', 'SELL', 'ENTER', 'EXIT', 'LONG', 'SHORT',
                          '金叉', '死叉', '买入', '卖出', '开仓', '平仓']
        return any(kw in name.upper() for kw in signal_keywords)

    def _generate_indicators(self) -> str:
        """生成指标计算代码"""
        lines = []

        for var_name, expr in self.variables.items():
            py_expr = self._convert_expression(expr)
            lines.append(f"        {var_name.lower()} = {py_expr}")

        for out_name, expr in self.outputs.items():
            py_expr = self._convert_expression(expr)
            lines.append(f"        {out_name.lower()} = {py_expr}")

        return '\n'.join(lines)

    def _convert_expression(self, node: ASTNode) -> str:
        """将AST节点转换为Python表达式"""
        if isinstance(node, NumberNode):
            return str(node.value)

        if isinstance(node, IdentifierNode):
            name = node.name.upper()
            if name in DATA_VARIABLE_MAPPINGS:
                return f"bar.{DATA_VARIABLE_MAPPINGS[name]}"
            return node.name.lower()

        if isinstance(node, FunctionCallNode):
            return self._convert_function_call(node)

        if isinstance(node, BinaryOpNode):
            left = self._convert_expression(node.left)
            right = self._convert_expression(node.right)
            return f"({left} {node.operator} {right})"

        return ""

    def _convert_function_call(self, node: FunctionCallNode) -> str:
        """转换函数调用"""
        func_name = node.function_name.upper()

        if func_name in FUNCTION_MAPPINGS:
            mapping = FUNCTION_MAPPINGS[func_name]

            # 转换参数
            args = [self._convert_expression(arg) for arg in node.arguments]

            if mapping.requires_array_manager:
                return f"self.am.{mapping.vnpy_name}({', '.join(args)})"
            else:
                return f"{mapping.vnpy_name}({', '.join(args)})"

        # 未映射的函数，保持原样
        args = [self._convert_expression(arg) for arg in node.arguments]
        return f"{func_name.lower()}({', '.join(args)})"

    def _generate_trading_logic(self) -> str:
        """生成交易逻辑代码"""
        lines = []

        for signal_name, expr in self.signals.items():
            signal_var = signal_name.lower()

            if 'BUY' in signal_name.upper() or '买入' in signal_name or '金叉' in signal_name:
                lines.append(f"        if {signal_var}:")
                lines.append(f"            self.buy(bar.close_price, 1)")

            if 'SELL' in signal_name.upper() or '卖出' in signal_name or '死叉' in signal_name:
                lines.append(f"        if {signal_var}:")
                lines.append(f"            self.sell(bar.close_price, 1)")

        if not lines:
            lines.append("        # TODO: 请根据信号变量完善交易逻辑")
            lines.append("        pass")

        return '\n'.join(lines)

    def _generate_custom_functions(self) -> str:
        """生成自定义辅助函数"""
        return '''
    def _cross(self, fast, slow):
        """交叉判断：fast上穿slow"""
        return (fast[-1] <= slow[-1]) and (fast[0] > slow[0])
'''
```

### 6. 迁移工作流

```
┌─────────────────────────────────────────────────────────────────┐
│                    通达信公式迁移流程                              │
└─────────────────────────────────────────────────────────────────┘

    ┌──────────────┐     ┌──────────────────┐     ┌─────────────┐
    │ 通达信公式    │────▶│  FormulaLexer    │────▶│  Token 列表  │
    │ 源代码       │     │  .tokenize()     │     │             │
    └──────────────┘     └──────────────────┘     └─────────────┘
                                   │
                                   ▼
                         ┌──────────────────┐
                         │  FormulaParser   │
                         │  .parse()        │
                         └──────────────────┘
                                   │
                                   ▼
                         ┌──────────────────┐
                         │  AST (抽象语法树)  │
                         │  ProgramNode     │
                         └──────────────────┘
                                   │
                                   ▼
                         ┌──────────────────┐
                         │  CodeGenerator   │
                         │  .generate()     │
                         └──────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
            ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
            │ 变量映射     │ │ 函数映射     │ │ 信号识别     │
            │ CLOSE→close │ │ MA→sma     │ │ 金叉→BUY    │
            └─────────────┘ └─────────────┘ └─────────────┘
                                   │
                                   ▼
                         ┌──────────────────┐
                         │ Python 策略代码   │
                         │ CtaTemplate 子类 │
                         └──────────────────┘
```

### 7. 使用示例

```python
from vnpy.tools.formula_parser import FormulaParser, CodeGenerator

# 通达信公式
tdx_formula = """
MA5:=MA(CLOSE,5);
MA10:=MA(CLOSE,10);
MA20:=MA(CLOSE,20);

金叉:CROSS(MA5,MA10);
死叉:CROSS(MA10,MA5);

多头排列:MA5>MA10 AND MA10>MA20;
"""

# 解析公式
lexer = FormulaLexer(tdx_formula)
tokens = lexer.tokenize()

parser = FormulaParser(tokens)
ast = parser.parse()

# 生成策略代码
generator = CodeGenerator(ast, formula_name="MA_Cross")
python_code = generator.generate()

# 保存到文件
with open("ma_cross_strategy.py", "w", encoding="utf-8") as f:
    f.write(python_code)
```

### 8. 生成的策略代码示例

```python
"""
自动生成的 vnpy 策略 - 基于通达信公式迁移
原始公式: MA_Cross
生成时间: 2026-02-28 15:30:00
"""
from vnpy.trader.utility import ArrayManager
from vnpy_ctastrategy import CtaTemplate


class MACrossStrategy(CtaTemplate):
    """MACrossStrategy - 迁移自通达信公式"""

    author = "Formula Migrator"

    # 策略参数
    ma_fast_period = 5
    ma_slow_period = 10
    ma_trend_period = 20

    # 策略变量
    ma5 = 0.0
    ma10 = 0.0
    ma20 = 0.0

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self.am = ArrayManager(size=100)

    def on_init(self):
        self.write_log("策略初始化")

    def on_start(self):
        self.write_log("策略启动")

    def on_stop(self):
        self.write_log("策略停止")

    def on_bar(self, bar):
        self.am.update_bar(bar)

        if not self.am.inited:
            return

        # 计算指标
        ma5 = self.am.sma(self.ma_fast_period)
        ma10 = self.am.sma(self.ma_slow_period)
        ma20 = self.am.sma(self.ma_trend_period)

        golden_cross = self._cross(ma5, ma10)
        death_cross = self._cross(ma10, ma5)

        # 交易逻辑
        if golden_cross:
            self.buy(bar.close_price, 1)

        if death_cross:
            self.sell(bar.close_price, 1)

    def _cross(self, fast, slow):
        """交叉判断"""
        return (fast[-1] <= slow[-1]) and (fast[0] > slow[0])
```

---

## 实现任务

### Phase 1: 词法分析（P0）

- [ ] 实现 `FormulaLexer` 词法分析器
- [ ] 支持数字、标识符、运算符识别
- [ ] 处理注释和空白字符

### Phase 2: 语法分析（P0）

- [ ] 实现 `FormulaParser` 语法分析器
- [ ] 构建 AST 抽象语法树
- [ ] 支持赋值、函数调用、条件表达式

### Phase 3: 函数映射（P0）

- [ ] 建立 `FUNCTION_MAPPINGS` 映射表
- [ ] 建立 `DATA_VARIABLE_MAPPINGS` 映射表
- [ ] 实现参数转换逻辑

### Phase 4: 代码生成（P0）

- [ ] 实现 `CodeGenerator` 代码生成器
- [ ] 生成 CtaTemplate 子类代码
- [ ] 自动识别交易信号

### Phase 5: 工具集成（P1）

- [ ] 实现命令行工具 `vnpy-formula-migrate`
- [ ] 支持批量公式迁移
- [ ] 生成迁移报告

---

## 验证方案

### 1. 单元测试

```python
# 测试词法分析
lexer = FormulaLexer("MA5:=MA(CLOSE,5);")
tokens = lexer.tokenize()
assert tokens[0].type == TokenType.IDENTIFIER
assert tokens[0].value == "MA5"

# 测试语法分析
parser = FormulaParser(tokens)
ast = parser.parse()
assert isinstance(ast, ProgramNode)
assert len(ast.statements) == 1

# 测试代码生成
generator = CodeGenerator(ast, "TestFormula")
code = generator.generate()
assert "def on_bar(self, bar):" in code
```

### 2. 功能测试

```python
# 测试完整迁移流程
tdx_formula = """
MA5:=MA(CLOSE,5);
MA10:=MA(CLOSE,10);
金叉:CROSS(MA5,MA10);
"""

code = migrate_formula(tdx_formula, "MA_Cross")
exec(code)  # 验证代码可执行

# 验证生成的策略类
assert "MACrossStrategy" in dir()
```

---

## 关键文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `vnpy/tools/formula_parser/__init__.py` | 新增 | 模块导出 |
| `vnpy/tools/formula_parser/lexer.py` | 新增 | 词法分析器 |
| `vnpy/tools/formula_parser/parser.py` | 新增 | 语法分析器 |
| `vnpy/tools/formula_parser/ast_nodes.py` | 新增 | AST节点定义 |
| `vnpy/tools/formula_parser/function_map.py` | 新增 | 函数映射表 |
| `vnpy/tools/formula_parser/code_generator.py` | 新增 | 代码生成器 |
| `tests/test_formula_parser.py` | 新增 | 单元测试 |