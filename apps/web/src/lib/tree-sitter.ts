import Parser from 'web-tree-sitter';

// Supported languages
export enum SupportedLanguage {
    PYTHON = 'python',
    JAVASCRIPT = 'javascript',
    TYPESCRIPT = 'typescript',
}

let isInitialized = false;
const parsers: Record<string, Parser> = {};

/**
 * Initialize the tree-sitter library.
 * Must be called before any parsing.
 */
export async function initTreeSitter(): Promise<void> {
    if (isInitialized) return;

    try {
        await Parser.init({
            locateFile(scriptName: string, scriptDirectory: string) {
                // Look for the .wasm file in the public folder
                return '/' + scriptName;
            },
        });
        isInitialized = true;
        console.log('Tree-sitter initialized');
    } catch (error) {
        console.error('Failed to initialize tree-sitter:', error);
        throw error;
    }
}

/**
 * Get or create a parser for the specified language.
 */
export async function getParser(language: SupportedLanguage): Promise<Parser | null> {
    if (!isInitialized) {
        await initTreeSitter();
    }

    if (parsers[language]) {
        return parsers[language];
    }

    try {
        // Load the language (grammar) wasm file
        // Assumes file is at /tree-sitter-{language}.wasm
        const lang = await Parser.Language.load(`/tree-sitter-${language}.wasm`);
        const parser = new Parser();
        parser.setLanguage(lang);
        parsers[language] = parser;
        return parser;
    } catch (error) {
        console.error(`Failed to load parser for ${language}:`, error);
        return null;
    }
}

/**
 * Unload all parsers to free memory.
 */
export function unloadParsers() {
    Object.keys(parsers).forEach((key) => {
        parsers[key].delete();
        delete parsers[key];
    });
}
