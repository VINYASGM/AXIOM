import TreeSitter from 'web-tree-sitter';

// Supported languages
export enum SupportedLanguage {
    PYTHON = 'python',
    JAVASCRIPT = 'javascript',
    TYPESCRIPT = 'typescript',
}

let isInitialized = false;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const parsers: Record<string, any> = {};

/**
 * Initialize the tree-sitter library.
 * Must be called before any parsing.
 */
export async function initTreeSitter(): Promise<void> {
    if (isInitialized) return;

    try {
        // @ts-expect-error — web-tree-sitter's types don't expose init() on the default export
        await TreeSitter.init({
            locateFile(scriptName: string) {
                // Look for the .wasm file in the public folder
                return '/' + scriptName;
            },
        });
        isInitialized = true;
        // Tree-sitter initialized successfully
    } catch (error) {
        console.error('Failed to initialize tree-sitter:', error);
        throw error;
    }
}

/**
 * Get or create a parser for the specified language.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function getParser(language: SupportedLanguage): Promise<any | null> {
    if (!isInitialized) {
        await initTreeSitter();
    }

    if (parsers[language]) {
        return parsers[language];
    }

    try {
        // Load the language (grammar) wasm file
        // Assumes file is at /tree-sitter-{language}.wasm
        const lang = await TreeSitter.Language.load(`/tree-sitter-${language}.wasm`);
        // @ts-expect-error — web-tree-sitter's types don't expose the constructor on the default export
        const parser = new TreeSitter();
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

