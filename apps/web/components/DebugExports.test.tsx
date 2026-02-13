import { describe, it } from 'vitest';
import * as Lucide from 'lucide-react';
import { Send } from 'lucide-react';
import { ScaffoldingLevel } from './AdaptiveScaffolding';
import { render } from '@testing-library/react';
import React from 'react';
import { createRequire } from 'module';

describe('Debug Exports', () => {
    it('check exports', () => {
        // ...
        console.log('Lucide keys count:', Object.keys(Lucide).length);
        console.log('Send type:', typeof Send);
        console.log('Send is valid react component?', typeof Send === 'function' || typeof Send === 'object');

        console.log('ScaffoldingLevel type:', typeof ScaffoldingLevel);
        console.log('ScaffoldingLevel value:', ScaffoldingLevel);
    });

    // ...

    it('render Send', () => {
        const require = createRequire(import.meta.url);
        console.log('React path:', require.resolve('react'));
        // render(React.createElement(Send));
    });
});
