import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
    title: 'AXIOM - Semantic Development Environment',
    description: 'Express verified intent, generate proven code. AXIOM is where humans design and AI implements.',
    keywords: ['AXIOM', 'AI coding', 'intent-driven', 'verified code', 'semantic development'],
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="en" className="dark">
            <body className={inter.className}>
                <Providers>{children}</Providers>
            </body>
        </html>
    );
}
