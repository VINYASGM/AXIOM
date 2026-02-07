'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState, useEffect } from 'react';
import { useAxiomStore } from '@/store/axiom';

function DataSync() {
    const { token, fetchLearnerProfile } = useAxiomStore();

    useEffect(() => {
        if (token) {
            fetchLearnerProfile(token);
        }
    }, [token, fetchLearnerProfile]);

    return null;
}

export function Providers({ children }: { children: React.ReactNode }) {
    const [queryClient] = useState(() => new QueryClient({
        defaultOptions: {
            queries: {
                staleTime: 60 * 1000, // 1 minute
                refetchOnWindowFocus: false,
            },
        },
    }));

    return (
        <QueryClientProvider client={queryClient}>
            <DataSync />
            {children}
        </QueryClientProvider>
    );
}
