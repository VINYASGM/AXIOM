"""
Tier 0 Verification - Tree-sitter Incremental Parsing

Provides instant (<10ms) syntax validation using Tree-sitter.
This is the first line of defense in the verification pipeline.

Features:
- Incremental parsing for real-time feedback
- AST caching for efficiency
- Multi-language support (Python, JavaScript, TypeScript, Go, Rust)
- Structural analysis and error detection
"""
import os
import time
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

# Tree-sitter imports (optional - graceful fallback if not installed)
try:
    from tree_sitter import Language, Parser, Node
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    Language = None
    Parser = None
    Node = None


class SupportedLanguage(str, Enum):
    """Languages supported by Tier 0 verification."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    GO = "go"
    RUST = "rust"


@dataclass
class SyntaxError:
    """A syntax error detected by Tree-sitter."""
    line: int
    column: int
    end_line: int
    end_column: int
    message: str
    severity: str = "error"  # error, warning, info
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "line": self.line,
            "column": self.column,
            "end_line": self.end_line,
            "end_column": self.end_column,
            "message": self.message,
            "severity": self.severity
        }


@dataclass
class ASTNode:
    """Simplified AST node for analysis."""
    type: str
    start_line: int
    start_column: int
    end_line: int
    end_column: int
    text: str
    children: List['ASTNode'] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "text": self.text[:100] if len(self.text) > 100 else self.text,
            "children_count": len(self.children)
        }


@dataclass
class Tier0Result:
    """Result of Tier 0 verification."""
    passed: bool
    language: str
    parse_time_ms: float
    errors: List[SyntaxError] = field(default_factory=list)
    warnings: List[SyntaxError] = field(default_factory=list)
    
    # Structural information
    has_syntax_tree: bool = False
    root_node_type: Optional[str] = None
    node_count: int = 0
    
    # Key structures detected
    functions: List[Dict[str, Any]] = field(default_factory=list)
    classes: List[Dict[str, Any]] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    
    # Confidence based on structure
    confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "language": self.language,
            "parse_time_ms": round(self.parse_time_ms, 2),
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
            "has_syntax_tree": self.has_syntax_tree,
            "root_node_type": self.root_node_type,
            "node_count": self.node_count,
            "functions": self.functions,
            "classes": self.classes,
            "imports": self.imports,
            "confidence": round(self.confidence, 3)
        }


from utils.parser import get_parser, TREE_SITTER_AVAILABLE

class TreeSitterVerifier:
    """
    Tree-sitter based syntax verifier.
    
    Provides Tier 0 verification with <10ms response time.
    """
    
    # Language to file extension mapping
    LANG_EXTENSIONS = {
        SupportedLanguage.PYTHON: [".py"],
        SupportedLanguage.JAVASCRIPT: [".js", ".jsx", ".mjs"],
        SupportedLanguage.TYPESCRIPT: [".ts", ".tsx"],
        SupportedLanguage.GO: [".go"],
        SupportedLanguage.RUST: [".rs"]
    }
    
    # Node types that indicate functions by language
    FUNCTION_NODE_TYPES = {
        "python": ["function_definition", "async_function_definition"],
        "javascript": ["function_declaration", "arrow_function", "function_expression", "method_definition"],
        "typescript": ["function_declaration", "arrow_function", "function_expression", "method_definition"],
        "go": ["function_declaration", "method_declaration"],
        "rust": ["function_item"]
    }
    
    # Node types that indicate classes
    CLASS_NODE_TYPES = {
        "python": ["class_definition"],
        "javascript": ["class_declaration"],
        "typescript": ["class_declaration"],
        "go": ["type_declaration"],  # struct-based
        "rust": ["struct_item", "impl_item"]
    }
    
    # Node types that indicate imports
    IMPORT_NODE_TYPES = {
        "python": ["import_statement", "import_from_statement"],
        "javascript": ["import_statement"],
        "typescript": ["import_statement"],
        "go": ["import_declaration"],
        "rust": ["use_declaration"]
    }
    
    def __init__(self):
        self._ast_cache: Dict[str, Tuple[str, Any]] = {}  # code_hash -> (code, tree)
        self._max_cache_size = 100
    
    def _get_parser(self, language: str) -> Optional[Any]:
        """Get parser from utility."""
        return get_parser(language)
    
    def verify(self, code: str, language: str) -> Tier0Result:
        """
        Verify code syntax using Tree-sitter.
        
        Args:
            code: Source code to verify
            language: Programming language
            
        Returns:
            Tier0Result with syntax validation results
        """
        start_time = time.time()
        
        # Check cache first
        code_hash = hash(code)
        if code_hash in self._ast_cache:
            cached_code, cached_tree = self._ast_cache[code_hash]
            if cached_code == code:
                parse_time = (time.time() - start_time) * 1000
                return self._analyze_tree(cached_tree, language, parse_time)
        
        # Get parser
        parser = self._get_parser(language)
        
        if parser is None:
            # Fallback to basic validation without tree-sitter
            return self._fallback_verify(code, language, (time.time() - start_time) * 1000)
        
        # Parse the code
        try:
            tree = parser.parse(bytes(code, "utf-8"))
            
            # Cache the result
            self._cache_tree(code_hash, code, tree)
            
            parse_time = (time.time() - start_time) * 1000
            return self._analyze_tree(tree, language, parse_time)
            
        except Exception as e:
            parse_time = (time.time() - start_time) * 1000
            return Tier0Result(
                passed=False,
                language=language,
                parse_time_ms=parse_time,
                errors=[SyntaxError(
                    line=1, column=0, end_line=1, end_column=0,
                    message=f"Parse error: {str(e)}"
                )],
                confidence=0.0
            )
    
    def _analyze_tree(self, tree: Any, language: str, parse_time: float) -> Tier0Result:
        """Analyze a parsed syntax tree."""
        root = tree.root_node
        
        errors = []
        warnings = []
        functions = []
        classes = []
        imports = []
        
        # Count nodes and find errors
        node_count = 0
        
        def traverse(node):
            nonlocal node_count
            node_count += 1
            
            # Check for syntax errors
            if node.is_error or node.is_missing:
                errors.append(SyntaxError(
                    line=node.start_point[0] + 1,
                    column=node.start_point[1],
                    end_line=node.end_point[0] + 1,
                    end_column=node.end_point[1],
                    message=f"Syntax error: unexpected {node.type}" if node.is_error else f"Missing: {node.type}"
                ))
            
            # Extract structures
            node_type = node.type
            
            if node_type in self.FUNCTION_NODE_TYPES.get(language, []):
                name = self._get_node_name(node, language, "function")
                functions.append({
                    "name": name,
                    "line": node.start_point[0] + 1,
                    "end_line": node.end_point[0] + 1
                })
            
            if node_type in self.CLASS_NODE_TYPES.get(language, []):
                name = self._get_node_name(node, language, "class")
                classes.append({
                    "name": name,
                    "line": node.start_point[0] + 1,
                    "end_line": node.end_point[0] + 1
                })
            
            if node_type in self.IMPORT_NODE_TYPES.get(language, []):
                import_text = node.text.decode("utf-8") if node.text else ""
                imports.append(import_text)
            
            # Recurse
            for child in node.children:
                traverse(child)
        
        traverse(root)
        
        # Calculate confidence based on structure and errors
        confidence = 1.0
        if errors:
            confidence -= 0.3 * min(len(errors), 3)  # Max -0.9 for errors
        if not functions and not classes:
            confidence -= 0.1  # Slight penalty for no structure
        confidence = max(0.0, min(1.0, confidence))
        
        return Tier0Result(
            passed=len(errors) == 0,
            language=language,
            parse_time_ms=parse_time,
            errors=errors,
            warnings=warnings,
            has_syntax_tree=True,
            root_node_type=root.type,
            node_count=node_count,
            functions=functions,
            classes=classes,
            imports=imports,
            confidence=confidence
        )
    
    def _get_node_name(self, node: Any, language: str, node_kind: str) -> str:
        """Extract the name from a function/class node."""
        # Look for identifier child
        for child in node.children:
            if child.type == "identifier" or child.type == "name":
                return child.text.decode("utf-8") if child.text else "unknown"
        return "anonymous"
    
    def _fallback_verify(self, code: str, language: str, parse_time: float) -> Tier0Result:
        """Basic verification without tree-sitter."""
        errors = []
        
        # Very basic syntax checks
        if language == "python":
            try:
                compile(code, "<string>", "exec")
            except SyntaxError as e:
                errors.append(SyntaxError(
                    line=e.lineno or 1,
                    column=e.offset or 0,
                    end_line=e.lineno or 1,
                    end_column=(e.offset or 0) + 1,
                    message=str(e.msg)
                ))
        
        elif language in ["javascript", "typescript"]:
            # Basic brace/paren matching
            if not self._check_balanced(code, "{", "}"):
                errors.append(SyntaxError(1, 0, 1, 0, "Unbalanced braces"))
            if not self._check_balanced(code, "(", ")"):
                errors.append(SyntaxError(1, 0, 1, 0, "Unbalanced parentheses"))
        
        return Tier0Result(
            passed=len(errors) == 0,
            language=language,
            parse_time_ms=parse_time,
            errors=errors,
            has_syntax_tree=False,
            confidence=0.5 if len(errors) == 0 else 0.2  # Lower confidence for fallback
        )
    
    def _check_balanced(self, code: str, open_char: str, close_char: str) -> bool:
        """Check if delimiters are balanced."""
        count = 0
        in_string = False
        string_char = None
        
        for i, char in enumerate(code):
            if char in '"\'':
                if not in_string:
                    in_string = True
                    string_char = char
                elif char == string_char and (i == 0 or code[i-1] != '\\'):
                    in_string = False
            
            if not in_string:
                if char == open_char:
                    count += 1
                elif char == close_char:
                    count -= 1
                    if count < 0:
                        return False
        
        return count == 0
    
    def _cache_tree(self, code_hash: int, code: str, tree: Any):
        """Cache a parsed tree with LRU eviction."""
        if len(self._ast_cache) >= self._max_cache_size:
            # Remove oldest entry
            oldest_key = next(iter(self._ast_cache))
            del self._ast_cache[oldest_key]
        
        self._ast_cache[code_hash] = (code, tree)
    
    def detect_language(self, code: str, filename: Optional[str] = None) -> str:
        """Detect the programming language from code or filename."""
        if filename:
            ext = os.path.splitext(filename)[1].lower()
            for lang, exts in self.LANG_EXTENSIONS.items():
                if ext in exts:
                    return lang.value
        
        # Heuristic detection from code
        if "def " in code or "import " in code and "from " in code:
            return "python"
        if "function " in code or "const " in code or "=>" in code:
            return "javascript"
        if "func " in code and "package " in code:
            return "go"
        if "fn " in code and "let mut" in code:
            return "rust"
        
        return "python"  # Default


# Global verifier instance
_tier0_verifier: Optional[TreeSitterVerifier] = None


def get_tier0_verifier() -> TreeSitterVerifier:
    """Get the global Tier 0 verifier instance."""
    global _tier0_verifier
    if _tier0_verifier is None:
        _tier0_verifier = TreeSitterVerifier()
    return _tier0_verifier


async def verify_tier0(code: str, language: str) -> Tier0Result:
    """Async wrapper for Tier 0 verification."""
    verifier = get_tier0_verifier()
    return verifier.verify(code, language)
