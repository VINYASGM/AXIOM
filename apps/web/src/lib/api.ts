const API_BASE = '/api/v1';

interface RequestOptions {
    method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
    body?: unknown;
    headers?: Record<string, string>;
}

class ApiClient {
    private token: string | null = null;

    setToken(token: string) {
        this.token = token;
    }

    clearToken() {
        this.token = null;
    }

    async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
        const { method = 'GET', body, headers = {} } = options;

        const requestHeaders: Record<string, string> = {
            'Content-Type': 'application/json',
            ...headers,
        };

        if (this.token) {
            requestHeaders['Authorization'] = `Bearer ${this.token}`;
        }

        const response = await fetch(`${API_BASE}${endpoint}`, {
            method,
            headers: requestHeaders,
            body: body ? JSON.stringify(body) : undefined,
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ error: 'Unknown error' }));
            throw new Error(error.error || `Request failed: ${response.status}`);
        }

        return response.json();
    }

    // Auth
    async register(email: string, name: string, password: string) {
        return this.request('/auth/register', {
            method: 'POST',
            body: { email, name, password },
        });
    }

    async login(email: string, password: string) {
        return this.request<{ token: string; user: unknown }>('/auth/login', {
            method: 'POST',
            body: { email, password },
        });
    }

    // Intent
    async parseIntent(rawIntent: string) {
        return this.request<{
            parsed_intent: Record<string, unknown>;
            confidence: number;
            suggested_refinements: string[];
        }>('/intent/parse', {
            method: 'POST',
            body: { raw_intent: rawIntent },
        });
    }

    async createIVCU(projectId: string, rawIntent: string, contracts: unknown[] = []) {
        return this.request<{ ivcu_id: string }>('/intent/create', {
            method: 'POST',
            body: { project_id: projectId, raw_intent: rawIntent, contracts },
        });
    }

    async getIVCU(id: string) {
        return this.request<{
            id: string;
            raw_intent: string;
            code: string;
            confidence_score: number;
            status: string;
        }>(`/intent/${id}`);
    }

    // Generation
    async startGeneration(ivcuId: string, language: string) {
        return this.request<{ generation_id: string }>('/generation/start', {
            method: 'POST',
            body: { ivcu_id: ivcuId, language },
        });
    }

    async getGenerationStatus(id: string) {
        return this.request<{
            status: string;
            progress: number;
            confidence: number;
        }>(`/generation/${id}/status`);
    }

    // Verification
    async verify(ivcuId: string, code: string) {
        return this.request<{
            passed: boolean;
            confidence: number;
            verifier_results: unknown[];
        }>('/verification/verify', {
            method: 'POST',
            body: { ivcu_id: ivcuId, code },
        });
    }
}

export const api = new ApiClient();
