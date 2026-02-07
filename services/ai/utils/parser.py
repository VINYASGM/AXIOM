"""
Tree-sitter Parser Utility

Singleton provider for Tree-sitter parsers and languages.
Handles loading of shared libraries and initialization.
"""
import os
from typing import Optional, Any, Dict

# Try to import tree-sitter bindings
try:
    from tree_sitter import Language, Parser
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    Language = None
    Parser = None

class ParserFactory:
    """Factory for creating and caching Tree-sitter parsers."""
    
    _instance: Optional['ParserFactory'] = None
    
    def __init__(self):
        self._languages: Dict[str, Any] = {}
        self._parsers: Dict[str, Any] = {}
        
    @classmethod
    def get_instance(cls) -> 'ParserFactory':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def get_parser(self, language_name: str) -> Optional[Any]:
        """Get a parser for the specified language."""
        if not TREE_SITTER_AVAILABLE:
            return None
            
        if language_name in self._parsers:
            return self._parsers[language_name]
            
        lang = self._load_language(language_name)
        if not lang:
            return None
            
        try:
            parser = Parser()
            parser.set_language(lang)
            self._parsers[language_name] = parser
            return parser
        except Exception as e:
            print(f"Error initializing parser for {language_name}: {e}")
            return None
    
    def _load_language(self, name: str) -> Optional[Any]:
        """Load specific language grammar."""
        if name in self._languages:
            return self._languages[name]
        
        lang = None
        try:
            # 1. Try tree_sitter_languages (easiest)
            import tree_sitter_languages
            lang = tree_sitter_languages.get_language(name)
        except ImportError:
            # 2. Try individual packages
            lang = self._load_from_packages(name)
            
        if lang:
            self._languages[name] = lang
            
        return lang

    def _load_from_packages(self, name: str) -> Optional[Any]:
        """Try loading from specific python packages."""
        try:
            if name == "python":
                import tree_sitter_python
                return Language(tree_sitter_python.language())
            elif name == "javascript":
                import tree_sitter_javascript
                return Language(tree_sitter_javascript.language())
            elif name == "typescript":
                import tree_sitter_typescript
                return Language(tree_sitter_typescript.language_typescript())
            elif name == "go":
                import tree_sitter_go
                return Language(tree_sitter_go.language())
            elif name == "rust":
                import tree_sitter_rust
                return Language(tree_sitter_rust.language())
        except Exception as e:
            print(f"Failed to load language package for {name}: {e}")
            
        return None

# Global Accessor
def get_parser(language: str) -> Optional[Any]:
    return ParserFactory.get_instance().get_parser(language)
