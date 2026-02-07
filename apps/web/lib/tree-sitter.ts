
export enum SupportedLanguage {
    PYTHON = 'python',
    JAVASCRIPT = 'javascript',
    TYPESCRIPT = 'typescript',
    GO = 'go'
}

export async function initTreeSitter() {
    console.log("Mock TreeSitter initialized");
    return true;
}

class MockNode {
    type: string = 'program';
    startPosition = { row: 0, column: 0 };
    endPosition = { row: 0, column: 0 };

    hasError() { return false; }
    isError() { return false; }
    isMissing() { return false; }
}

class MockCursor {
    currentNode() { return new MockNode(); }
    gotoFirstChild() { return false; }
    gotoNextSibling() { return false; }
    gotoParent() { return false; }
}

class MockTree {
    rootNode = new MockNode();
    walk() { return new MockCursor(); }
    delete() { }
}

export async function getParser(lang: SupportedLanguage) {
    return {
        parse: (text: string) => new MockTree()
    };
}
