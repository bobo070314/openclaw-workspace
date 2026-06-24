"""宪法检查器 — 把宪法编译成可执行规则引擎

核心理念：
- 不是"事后验收"，是"生成时实时拦截"
- 每条规则都有自动触发条件
- 违规后自动给出修正代码
- 支持自定义宪法（不是硬编码）
"""

from .rules import ConstitutionalRule, RuleCategory, RuleViolation, Severity


class ConstitutionalChecker:
    """宪法检查器 — 可执行的代码宪法"""

    def __init__(self):
        self.rules: list[ConstitutionalRule] = []
        self._register_default_rules()
        self._active = True

    # ================================================================
    # 核心 API
    # ================================================================

    def check_code(self, code: str, context: dict = None) -> list[RuleViolation]:
        """检查代码是否符合宪法

        Args:
            code: 要检查的代码
            context: 上下文（文件路径、语言、任务类型等）

        Returns:
            所有违规列表（按严重级排序）

        """
        context = context or {}
        violations = []

        for rule in self.rules:
            if not rule.enabled:
                continue

            # 检查触发条件
            if rule.trigger and not rule.trigger(context):
                continue

            # 检查文件模式
            if rule.file_patterns:
                file_path = context.get("file_path", "")
                if not any(self._match_pattern(file_path, p) for p in rule.file_patterns):
                    continue
                if any(self._match_pattern(file_path, p) for p in rule.exclude_patterns):
                    continue

            # 执行检查
            if rule.check:
                try:
                    result = rule.check(code, context)
                    violations.extend(result)
                except Exception as e:
                    violations.append(
                        RuleViolation(
                            rule_id=rule.id,
                            rule_name=rule.name,
                            severity=Severity.WARNING,
                            message=f"规则检查异常: {e}",
                            suggestion="请检查规则定义",
                        )
                    )

        # 按严重级排序：blocker > critical > warning > info > suggestion
        severity_order = {"blocker": 0, "critical": 1, "warning": 2, "info": 3, "suggestion": 4}
        violations.sort(key=lambda v: severity_order.get(v.severity.value, 5))

        return violations

    def check_file(self, file_path: str) -> list[RuleViolation]:
        """检查整个文件"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()
        except (OSError, UnicodeDecodeError) as e:
            return [
                RuleViolation(
                    rule_id="CONSTITUTION_FILE",
                    rule_name="文件可读性",
                    severity=Severity.WARNING,
                    message=f"无法读取文件: {e}",
                    suggestion="检查文件权限和编码",
                    location=file_path,
                )
            ]

        context = {"file_path": file_path, "language": self._infer_language(file_path)}
        return self.check_code(code, context)

    def auto_fix(self, code: str, violations: list[RuleViolation]) -> str:
        """尝试自动修复违规

        Returns:
            修复后的代码（如果无法修复，返回原文）

        """
        fixed_code = code
        for violation in violations:
            if violation.auto_fix:
                # 简单替换（生产环境应使用 AST 级别的修复）
                fixed_code = violation.auto_fix
                continue

            # 查找对应规则的 fix 函数
            for rule in self.rules:
                if rule.id == violation.rule_id and rule.fix:
                    try:
                        fixed_code = rule.fix(violation, fixed_code)
                    except Exception:
                        pass

        return fixed_code

    def get_report(self, violations: list[RuleViolation]) -> dict:
        """生成违规报告"""
        by_severity = {}
        for v in violations:
            sev = v.severity.value
            if sev not in by_severity:
                by_severity[sev] = []
            by_severity[sev].append(v.to_dict())

        blockers = len(by_severity.get("blocker", []))
        criticals = len(by_severity.get("critical", []))

        return {
            "total_violations": len(violations),
            "blockers": blockers,
            "criticals": criticals,
            "can_proceed": blockers == 0,
            "by_severity": by_severity,
            "summary": f"{len(violations)} 违规: {blockers} 阻断 {criticals} 严重",
        }

    def register_rule(self, rule: ConstitutionalRule):
        """注册自定义宪法规则"""
        self.rules.append(rule)

    def remove_rule(self, rule_id: str):
        """移除宪法规则"""
        self.rules = [r for r in self.rules if r.id != rule_id]

    def get_rules(self) -> list[dict]:
        """获取所有规则摘要"""
        return [r.to_dict() for r in self.rules]

    # ================================================================
    # 默认宪法规则（24条）
    # ================================================================

    def _register_default_rules(self):
        """注册内置的宪法规则"""
        # ── 代码质量规则 ──
        self.rules.extend(
            [
                ConstitutionalRule(
                    id="CONST_NO_TODO",
                    name="禁止未追踪的 TODO",
                    description="代码中不能包含无追踪链接的 TODO 注释",
                    category=RuleCategory.CODE_QUALITY,
                    severity=Severity.WARNING,
                    check=lambda code, ctx: self._check_pattern(
                        code,
                        r"#\s*TODO(?!.*https?://|.*[A-Z]+-\d+)",
                        "CONST_NO_TODO",
                        "TODO 注释",
                        "TODO 必须附带 Issue 链接或 Jira 编号",
                    ),
                    tags=["todo", "comment"],
                ),
                ConstitutionalRule(
                    id="CONST_MAX_FUNCTION_LENGTH",
                    name="函数长度限制",
                    description="单函数不超过 100 行（构造函数和测试除外）",
                    category=RuleCategory.CODE_QUALITY,
                    severity=Severity.SUGGESTION,
                    check=lambda code, ctx: self._check_function_length(code, 100),
                    tags=["complexity", "refactor"],
                ),
                ConstitutionalRule(
                    id="CONST_NO_BARE_EXCEPT",
                    name="禁止裸 except",
                    description="禁止使用 except: 或 except Exception: 而不记录或处理",
                    category=RuleCategory.CODE_QUALITY,
                    severity=Severity.WARNING,
                    file_patterns=["*.py"],
                    check=lambda code, ctx: self._check_pattern(
                        code,
                        r"except\s*:",
                        "CONST_NO_BARE_EXCEPT",
                        "裸 except",
                        "指定捕获的异常类型，如 except ValueError:",
                    ),
                    tags=["error-handling", "python"],
                ),
                ConstitutionalRule(
                    id="CONST_REQUIRE_TYPING",
                    name="要求类型注解",
                    description="公共函数参数和返回值必须有类型注解",
                    category=RuleCategory.CODE_QUALITY,
                    severity=Severity.SUGGESTION,
                    file_patterns=["*.py"],
                    check=lambda code, ctx: self._check_typing(code),
                    tags=["typing", "python"],
                ),
                ConstitutionalRule(
                    id="CONST_NAMED_CONSTANTS",
                    name="禁止魔法数字",
                    description="代码中的数字必须使用命名常量",
                    category=RuleCategory.CODE_QUALITY,
                    severity=Severity.SUGGESTION,
                    check=lambda code, ctx: self._check_magic_numbers(code),
                    tags=["readability"],
                ),
                ConstitutionalRule(
                    id="CONST_MAX_CLASS_LENGTH",
                    name="类长度限制",
                    description="单类不超过 300 行（不包括 docstring）",
                    category=RuleCategory.CODE_QUALITY,
                    severity=Severity.SUGGESTION,
                    check=lambda code, ctx: self._check_class_length(code, 300),
                    tags=["complexity", "refactor"],
                ),
            ]
        )

        # ── 安全规则 ──
        self.rules.extend(
            [
                ConstitutionalRule(
                    id="CONST_NO_HARDCODED_SECRETS",
                    name="禁止硬编码密钥",
                    description="禁止在代码中硬编码密钥、密码、Token",
                    category=RuleCategory.SECURITY,
                    severity=Severity.BLOCKER,
                    check=lambda code, ctx: self._check_secrets(code),
                    tags=["security", "secrets"],
                ),
                ConstitutionalRule(
                    id="CONST_NO_SQL_INJECTION",
                    name="禁止 SQL 注入",
                    description="禁止使用字符串拼接构造 SQL 查询",
                    category=RuleCategory.SECURITY,
                    severity=Severity.CRITICAL,
                    file_patterns=["*.py", "*.js", "*.ts"],
                    check=lambda code, ctx: self._check_sql_injection(code),
                    tags=["security", "sql"],
                ),
                ConstitutionalRule(
                    id="CONST_INPUT_VALIDATION",
                    name="输入必须验证",
                    description="所有用户输入必须经过验证和清理",
                    category=RuleCategory.SECURITY,
                    severity=Severity.CRITICAL,
                    check=lambda code, ctx: self._check_input_validation(code),
                    tags=["security", "input"],
                ),
                ConstitutionalRule(
                    id="CONST_NO_EVAL",
                    name="禁止 eval/exec",
                    description="禁止使用 eval() / exec() / Function() 执行动态代码",
                    category=RuleCategory.SECURITY,
                    severity=Severity.BLOCKER,
                    file_patterns=["*.py", "*.js", "*.ts"],
                    check=lambda code, ctx: self._check_eval(code),
                    tags=["security", "code-injection"],
                ),
                ConstitutionalRule(
                    id="CONST_NO_DEBUG_IN_PROD",
                    name="禁止调试代码上生产",
                    description="print/console.log 等调试语句不能出现在生产代码中",
                    category=RuleCategory.SECURITY,
                    severity=Severity.WARNING,
                    check=lambda code, ctx: self._check_debug_code(code),
                    tags=["security", "production"],
                ),
            ]
        )

        # ── 架构规则 ──
        self.rules.extend(
            [
                ConstitutionalRule(
                    id="CONST_NO_CIRCULAR_DEPS",
                    name="禁止循环依赖",
                    description="模块之间禁止循环引用",
                    category=RuleCategory.ARCHITECTURE,
                    severity=Severity.CRITICAL,
                    file_patterns=["*.py"],
                    check=lambda code, ctx: self._check_pattern(
                        code,
                        r"from\s+\.\w+\s+import",
                        "CONST_NO_CIRCULAR_DEPS",
                        "可能的循环依赖",
                        "使用依赖注入或抽象接口打破循环",
                    ),
                    tags=["architecture", "dependencies"],
                ),
                ConstitutionalRule(
                    id="CONST_SINGLE_RESPONSIBILITY",
                    name="单一职责",
                    description="一个文件/类不应混合多种职责",
                    category=RuleCategory.ARCHITECTURE,
                    severity=Severity.SUGGESTION,
                    check=lambda code, ctx: self._check_single_responsibility(code),
                    tags=["architecture", "solid"],
                ),
                ConstitutionalRule(
                    id="CONST_INTERFACE_SEGREGATION",
                    name="接口隔离",
                    description="类不应依赖它不使用的接口方法",
                    category=RuleCategory.ARCHITECTURE,
                    severity=Severity.SUGGESTION,
                    check=lambda code, ctx: self._check_interface_bloat(code),
                    tags=["architecture", "solid"],
                ),
            ]
        )

        # ── 文档规则 ──
        self.rules.extend(
            [
                ConstitutionalRule(
                    id="CONST_PUBLIC_DOCSTRING",
                    name="公共函数必须有文档",
                    description="所有公共函数/类必须有 docstring",
                    category=RuleCategory.DOCUMENTATION,
                    severity=Severity.WARNING,
                    file_patterns=["*.py"],
                    check=lambda code, ctx: self._check_docstrings(code),
                    tags=["documentation"],
                ),
                ConstitutionalRule(
                    id="CONST_EXAMPLE_IN_DOCS",
                    name="API 文档含示例",
                    description="API 端点文档必须包含请求/响应示例",
                    category=RuleCategory.DOCUMENTATION,
                    severity=Severity.SUGGESTION,
                    file_patterns=["*.py", "*.ts"],
                    check=lambda code, ctx: self._check_api_docs(code),
                    tags=["documentation", "api"],
                ),
            ]
        )

        # ── 依赖规则 ──
        self.rules.extend(
            [
                ConstitutionalRule(
                    id="CONST_PIN_DEPENDENCIES",
                    name="依赖必须锁定版本",
                    description="requirements.txt / package.json 中依赖必须指定确切版本",
                    category=RuleCategory.DEPENDENCY,
                    severity=Severity.CRITICAL,
                    file_patterns=["requirements.txt", "package.json", "pyproject.toml"],
                    check=lambda code, ctx: self._check_pinned_deps(code),
                    tags=["dependencies", "security"],
                ),
                ConstitutionalRule(
                    id="CONST_NO_ABANDONED_DEPS",
                    name="禁止使用废弃依赖",
                    description="禁止依赖超过 1 年未更新的包",
                    category=RuleCategory.DEPENDENCY,
                    severity=Severity.WARNING,
                    check=lambda code, ctx: self._check_abandoned(code),
                    tags=["dependencies", "maintenance"],
                ),
            ]
        )

        # ── 测试规则 ──
        self.rules.extend(
            [
                ConstitutionalRule(
                    id="CONST_TEST_COVERAGE",
                    name="测试覆盖率",
                    description="核心业务逻辑必须有测试覆盖",
                    category=RuleCategory.TESTING,
                    severity=Severity.WARNING,
                    file_patterns=["*.py"],
                    check=lambda code, ctx: self._check_test_coverage(code, ctx),
                    tags=["testing", "coverage"],
                ),
                ConstitutionalRule(
                    id="CONST_NO_SKIP_IN_CI",
                    name="禁止跳过 CI 测试",
                    description="禁止使用 @pytest.mark.skip 或 test.skip 在 CI 环境中",
                    category=RuleCategory.TESTING,
                    severity=Severity.CRITICAL,
                    file_patterns=["test_*.py", "*_test.py", "*.test.*"],
                    check=lambda code, ctx: self._check_skipped_tests(code),
                    tags=["testing", "ci"],
                ),
            ]
        )

        # ── 数据规则 ──
        self.rules.extend(
            [
                ConstitutionalRule(
                    id="CONST_NO_PII_IN_LOGS",
                    name="禁止日志含敏感数据",
                    description="日志中不能包含 PII（个人身份信息）",
                    category=RuleCategory.DATA,
                    severity=Severity.CRITICAL,
                    check=lambda code, ctx: self._check_pii_in_logs(code),
                    tags=["data", "privacy", "pii"],
                ),
                ConstitutionalRule(
                    id="CONST_ENCRYPT_AT_REST",
                    name="敏感数据加密存储",
                    description="敏感数据在存储前必须加密",
                    category=RuleCategory.DATA,
                    severity=Severity.CRITICAL,
                    check=lambda code, ctx: self._check_encryption(code),
                    tags=["data", "encryption", "privacy"],
                ),
            ]
        )

    # ================================================================
    # 检测函数实现
    # ================================================================

    @staticmethod
    def _check_pattern(code: str, pattern: str, rule_id: str, name: str, suggestion: str) -> list[RuleViolation]:
        """通用模式匹配检测"""
        import re

        violations = []
        for i, line in enumerate(code.split("\n"), 1):
            if re.search(pattern, line):
                # 跳过注释行
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("--"):
                    continue
                violations.append(
                    RuleViolation(
                        rule_id=rule_id,
                        rule_name=name,
                        severity=Severity.WARNING,
                        message=f"第 {i} 行: {line.strip()[:80]}",
                        suggestion=suggestion,
                        location=f"line {i}",
                        context=line.strip(),
                    )
                )
        return violations

    @staticmethod
    def _check_secrets(code: str) -> list[RuleViolation]:
        """检测硬编码密钥"""
        import re

        secret_patterns = [
            (r'(?:api_key|apikey|secret|password|token)\s*[:=]\s*["][^""]{8,}["]', "硬编码密钥"),
            (r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----", "硬编码私钥"),
            (r"(?:sk-[a-zA-Z0-9]{8,})", "OpenAI/AI API Key"),
            (r"(?:ghp_[a-zA-Z0-9]{36})", "GitHub Personal Access Token"),
            (r"(?:AKIA[0-9A-Z]{16})", "AWS Access Key"),
        ]

        violations = []
        for i, line in enumerate(code.split("\n"), 1):
            for pattern, desc in secret_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    violations.append(
                        RuleViolation(
                            rule_id="CONST_NO_HARDCODED_SECRETS",
                            rule_name="禁止硬编码密钥",
                            severity=Severity.BLOCKER,
                            message=f"第 {i} 行: {desc}",
                            suggestion="使用环境变量或密钥管理服务替代: import os; os.getenv('SECRET')",
                            location=f"line {i}",
                            context=line.strip(),
                        )
                    )
        return violations

    @staticmethod
    def _check_sql_injection(code: str) -> list[RuleViolation]:
        """检测 SQL 注入风险"""
        import re

        risky = [
            r'execute\s*\(\s*["\'].*%s',  # cursor.execute("... %s" % val)
            r'execute\s*\(\s*f["\']',  # cursor.execute(f"...")
            r"\.format\s*\(.*\)\s*\)",  # "...".format(val))
            r'["\']\s*\+\s*\w+\s*\+\s*["\']',  # "SELECT * FROM " + table + " WHERE"
            r'raw\s*\(\s*f["\']',  # Django raw(f"...")
        ]

        violations = []
        for i, line in enumerate(code.split("\n"), 1):
            for pattern in risky:
                if re.search(pattern, line, re.IGNORECASE):
                    violations.append(
                        RuleViolation(
                            rule_id="CONST_NO_SQL_INJECTION",
                            rule_name="禁止 SQL 注入",
                            severity=Severity.CRITICAL,
                            message=f"第 {i} 行: 可能的 SQL 注入点",
                            suggestion="使用参数化查询: cursor.execute('SELECT * FROM t WHERE id = ?', (id,))",
                            location=f"line {i}",
                            context=line.strip(),
                        )
                    )
                    break
        return violations

    @staticmethod
    def _check_eval(code: str) -> list[RuleViolation]:
        """检测 eval/exec"""
        import re

        violations = []
        for i, line in enumerate(code.split("\n"), 1):
            if re.search(r"\beval\s*\(", line):
                violations.append(
                    RuleViolation(
                        rule_id="CONST_NO_EVAL",
                        rule_name="禁止 eval/exec",
                        severity=Severity.BLOCKER,
                        message=f"第 {i} 行: 使用 eval()",
                        suggestion="使用安全替代方案: json.loads() 或 ast.literal_eval()",
                        location=f"line {i}",
                        context=line.strip(),
                    )
                )
            if re.search(r"\bexec\s*\(", line):
                violations.append(
                    RuleViolation(
                        rule_id="CONST_NO_EVAL",
                        rule_name="禁止 eval/exec",
                        severity=Severity.BLOCKER,
                        message=f"第 {i} 行: 使用 exec()",
                        suggestion="避免 exec()，使用 importlib 或显式代码路径",
                        location=f"line {i}",
                        context=line.strip(),
                    )
                )
        return violations

    @staticmethod
    def _check_input_validation(code: str) -> list[RuleViolation]:
        """检测输入验证"""
        import re

        violations = []
        lines = code.split("\n")

        for i, line in enumerate(lines):
            stripped = line.strip()
            # Flask/Django/FastAPI 接收输入但未验证
            input_patterns = [
                r"request\.(args|form|json|data|POST|GET)\[",
                r"request\.(args|form|json|data)\.get\(",
                r'input\s*\(\s*["\']',
                r"raw_input\s*\(",
            ]
            for pattern in input_patterns:
                if __import__("re").search(pattern, stripped, re.IGNORECASE):
                    # 检查后续几行是否有验证
                    validated = False
                    for j in range(i, min(i + 5, len(lines))):
                        if any(
                            kw in lines[j].lower() for kw in ["validate", "sanitize", "clean", "strip", "isinstance"]
                        ):
                            validated = True
                            break
                    if not validated:
                        violations.append(
                            RuleViolation(
                                rule_id="CONST_INPUT_VALIDATION",
                                rule_name="输入必须验证",
                                severity=Severity.CRITICAL,
                                message=f"第 {i + 1} 行: 用户输入未经验证",
                                suggestion="添加输入验证: value = sanitize(request.args.get('key', ''))",
                                location=f"line {i + 1}",
                                context=stripped[:80],
                            )
                        )
        return violations

    @staticmethod
    def _check_debug_code(code: str) -> list[RuleViolation]:
        """检测调试代码"""
        debug_patterns = [
            (r"\bprint\s*\(", "print() 调试语句"),
            (r"\bconsole\.log\s*\(", "console.log() 调试语句"),
            (r"\bdebugger\b", "debugger 语句"),
            (r"\bimport\s+pdb\b", "pdb 调试器导入"),
            (r"\bpdb\.set_trace\s*\(", "pdb.set_trace() 断点"),
        ]

        violations = []
        for i, line in enumerate(code.split("\n"), 1):
            for pattern, desc in debug_patterns:
                if __import__("re").search(pattern, line):
                    if "test" not in code[:200].lower() and "test_" not in code[:200]:
                        violations.append(
                            RuleViolation(
                                rule_id="CONST_NO_DEBUG_IN_PROD",
                                rule_name="禁止调试代码上生产",
                                severity=Severity.WARNING,
                                message=f"第 {i} 行: {desc}",
                                suggestion="使用 logging 模块替代: logging.debug(...)",
                                location=f"line {i}",
                                context=line.strip(),
                            )
                        )
        return violations

    @staticmethod
    def _check_docstrings(code: str) -> list[RuleViolation]:
        """检测 docstring"""
        # 简单检测：def/class 后没有 docstring
        violations = []
        lines = code.split("\n")

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("def ") or stripped.startswith("class "):
                # 检查下一行是否有 docstring
                has_doc = False
                for j in range(i + 1, min(i + 3, len(lines))):
                    check = lines[j].strip()
                    if '"""' in check or "'''" in check:
                        has_doc = True
                        break
                    if check.startswith("@") or check.startswith("#"):
                        continue
                    if ":" in stripped and not check:
                        continue
                    break

                if not has_doc:
                    name = stripped.split("(")[0].replace("def ", "").replace("class ", "").strip()
                    if not name.startswith("_"):  # 私有函数豁免
                        violations.append(
                            RuleViolation(
                                rule_id="CONST_PUBLIC_DOCSTRING",
                                rule_name="公共函数必须有文档",
                                severity=Severity.WARNING,
                                message=f"第 {i + 1} 行: {name} 缺少 docstring",
                                suggestion='添加: """简要描述"""',
                                location=f"line {i + 1}",
                                context=stripped[:80],
                            )
                        )
        return violations

    @staticmethod
    def _check_function_length(code: str, max_len: int) -> list[RuleViolation]:
        """检测函数长度"""
        # 简化版：检测 def 之间的行数
        violations = []
        lines = code.split("\n")
        in_func = False
        func_start = 0
        func_name = ""

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("def "):
                if in_func and (i - func_start) > max_len:
                    violations.append(
                        RuleViolation(
                            rule_id="CONST_MAX_FUNCTION_LENGTH",
                            rule_name="函数长度限制",
                            severity=Severity.SUGGESTION,
                            message=f"{func_name} 共 {i - func_start} 行（超过 {max_len} 行限制）",
                            suggestion="拆分为多个小函数，每个函数只做一件事",
                            location=f"line {func_start + 1}",
                        )
                    )
                func_start = i
                func_name = stripped.split("(")[0].replace("def ", "").strip()
                in_func = True

        return violations

    @staticmethod
    def _check_class_length(code: str, max_len: int) -> list[RuleViolation]:
        """检测类长度"""
        violations = []
        lines = code.split("\n")
        in_class = False
        class_start = 0
        indent = 0

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("class "):
                in_class = True
                class_start = i
                indent = len(line) - len(line.lstrip())
            elif in_class and line.strip() and (len(line) - len(line.lstrip())) <= indent:
                if (i - class_start) > max_len:
                    violations.append(
                        RuleViolation(
                            rule_id="CONST_MAX_CLASS_LENGTH",
                            rule_name="类长度限制",
                            severity=Severity.SUGGESTION,
                            message=f"类共 {i - class_start} 行（超过 {max_len} 行限制）",
                            suggestion="提取子类或 Mixin 分解职责",
                            location=f"line {class_start + 1}",
                        )
                    )
                in_class = False

        return violations

    @staticmethod
    def _check_typing(code: str) -> list[RuleViolation]:
        """检测类型注解"""
        violations = []
        for i, line in enumerate(code.split("\n"), 1):
            stripped = line.strip()
            if stripped.startswith("def ") and "(" in stripped:
                # 公共函数（不以 _ 开头）必须有类型注解
                func_part = stripped.split("(")[0].replace("def ", "").strip()
                if not func_part.startswith("_") and func_part != "__init__":
                    if "->" not in stripped and ":" not in stripped.split("(")[1].split(")")[0]:
                        violations.append(
                            RuleViolation(
                                rule_id="CONST_REQUIRE_TYPING",
                                rule_name="要求类型注解",
                                severity=Severity.SUGGESTION,
                                message=f"第 {i} 行: {func_part} 缺少类型注解",
                                suggestion=f"添加: def {func_part}(x: int) -> str:",
                                location=f"line {i}",
                            )
                        )
        return violations

    @staticmethod
    def _check_magic_numbers(code: str) -> list[RuleViolation]:
        """检测魔法数字（简化版）"""
        import re

        violations = []
        # 查找数字 0,1,True/False 以外的字面量数字
        for i, line in enumerate(code.split("\n"), 1):
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("import") or stripped.startswith("from"):
                continue
            # 查找赋值以外的独立数字
            if re.search(r'(?<![=#\w\'".])\b([2-9]\d*)\b(?![.\d])', stripped):
                violations.append(
                    RuleViolation(
                        rule_id="CONST_NAMED_CONSTANTS",
                        rule_name="禁止魔法数字",
                        severity=Severity.SUGGESTION,
                        message=f"第 {i} 行: 存在魔法数字",
                        suggestion="使用命名常量: MAX_RETRIES = 3",
                        location=f"line {i}",
                    )
                )
        return violations

    @staticmethod
    def _check_api_docs(code: str) -> list[RuleViolation]:
        """检测 API 文档"""
        violations = []
        # 检测 @app.route / @router.get 等装饰器后是否有示例
        for i, line in enumerate(code.split("\n"), 1):
            stripped = line.strip()
            if any(deco in stripped for deco in ["@app.route", "@router.get", "@router.post", "@app.get", "@app.post"]):
                # 检查后续 docstring 是否有示例
                has_example = False
                for j in range(i, min(i + 20, len(code.split("\n")))):
                    check = code.split("\n")[j].lower()
                    if any(kw in check for kw in ["example", "示例", "request:", "response:"]):
                        has_example = True
                        break
                if not has_example:
                    violations.append(
                        RuleViolation(
                            rule_id="CONST_EXAMPLE_IN_DOCS",
                            rule_name="API 文档含示例",
                            severity=Severity.SUGGESTION,
                            message=f"第 {i} 行: API 端点缺少请求/响应示例",
                            suggestion='在 docstring 中添加: """...\\nExample:\\n    GET /api/users -> {"id": 1}"""',
                            location=f"line {i}",
                        )
                    )
        return violations

    @staticmethod
    def _check_pinned_deps(code: str) -> list[RuleViolation]:
        """检测是否锁定依赖版本"""
        violations = []
        # requirements.txt: 检查是否有 == 或 >= 版本
        has_unpinned = False
        for line in code.split("\n"):
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and not stripped.startswith("-"):
                if "==" not in stripped and ">=" not in stripped and "~=" not in stripped:
                    has_unpinned = True

        if has_unpinned:
            violations.append(
                RuleViolation(
                    rule_id="CONST_PIN_DEPENDENCIES",
                    rule_name="依赖必须锁定版本",
                    severity=Severity.CRITICAL,
                    message="requirements.txt 中存在未锁定版本的依赖",
                    suggestion="使用 pip freeze > requirements.txt 或指定确切版本: requests==2.31.0",
                )
            )
        return violations

    @staticmethod
    def _check_abandoned(code: str) -> list[RuleViolation]:
        """检测废弃依赖（仅记录，无法实际检查 npm/pypi）"""
        return []  # 需要联网查询，暂时不做

    @staticmethod
    def _check_single_responsibility(code: str) -> list[RuleViolation]:
        """检测单一职责"""
        # 简化版：一个文件里有太多独立 class/function 就是职责混合
        classes = code.count("class ")
        functions = code.count("def ")

        violations = []
        if classes > 3 or (classes > 1 and functions > 10):
            violations.append(
                RuleViolation(
                    rule_id="CONST_SINGLE_RESPONSIBILITY",
                    rule_name="单一职责",
                    severity=Severity.SUGGESTION,
                    message=f"文件包含 {classes} 个类和 {functions} 个函数，可能职责过多",
                    suggestion="考虑按职责拆分为多个文件",
                )
            )
        return violations

    @staticmethod
    def _check_interface_bloat(code: str) -> list[RuleViolation]:
        """检测接口臃肿（简化版）"""
        return []  # 需要 AST 分析，暂时不做

    @staticmethod
    def _check_test_coverage(code: str, ctx: dict) -> list[RuleViolation]:
        """检测测试覆盖（仅标记，不做真实覆盖率分析）"""
        return []  # 需要运行 pytest coverage，暂时不做

    @staticmethod
    def _check_skipped_tests(code: str) -> list[RuleViolation]:
        """检测跳过的测试"""
        import re

        violations = []
        for i, line in enumerate(code.split("\n"), 1):
            if re.search(r"@pytest\.mark\.skip\b", line):
                violations.append(
                    RuleViolation(
                        rule_id="CONST_NO_SKIP_IN_CI",
                        rule_name="禁止跳过 CI 测试",
                        severity=Severity.CRITICAL,
                        message=f"第 {i} 行: 测试被标记为 skip",
                        suggestion="使用 @pytest.mark.xfail 替代 skip，或添加 skip 原因注释",
                        location=f"line {i}",
                    )
                )
        return violations

    @staticmethod
    def _check_pii_in_logs(code: str) -> list[RuleViolation]:
        """检测日志中的 PII"""
        import re

        violations = []
        for i, line in enumerate(code.split("\n"), 1):
            # 检测日志语句中包含敏感字段名
            if re.search(r"(?:log|print|logger)\s*[.(].*", line, re.IGNORECASE):
                if re.search(r"(?:email|phone|ssn|credit_card|password|secret|token|address)", line, re.IGNORECASE):
                    violations.append(
                        RuleViolation(
                            rule_id="CONST_NO_PII_IN_LOGS",
                            rule_name="禁止日志含敏感数据",
                            severity=Severity.CRITICAL,
                            message=f"第 {i} 行: 日志语句可能包含敏感数据",
                            suggestion="使用脱敏函数: log.info(f'User {mask_email(email)} logged in')",
                            location=f"line {i}",
                            context=line.strip()[:80],
                        )
                    )
        return violations

    @staticmethod
    def _check_encryption(code: str) -> list[RuleViolation]:
        """检测敏感数据加密"""
        # 简化版：检测是否有加密库导入但未使用
        return []  # 需要完整的流分析，暂时不做

    @staticmethod
    def _match_pattern(path: str, pattern: str) -> bool:
        """简单 glob 匹配"""
        if pattern.startswith("*."):
            ext = pattern[1:]
            return path.endswith(ext)
        return pattern in path

    @staticmethod
    def _infer_language(file_path: str) -> str:
        """推断文件语言"""
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript-react",
            ".jsx": "javascript-react",
            ".html": "html",
            ".css": "css",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".md": "markdown",
            ".sql": "sql",
        }
        for ext, lang in ext_map.items():
            if file_path.endswith(ext):
                return lang
        return "unknown"
