/**
 * AXIOM gRPC-Web Client
 * 
 * Unified client for communicating with AXIOM gRPC services.
 * Supports gRPC-Web protocol with automatic SSE fallback for environments
 * where gRPC-Web is not available.
 * 
 * @module lib/grpc
 */

// ============================================================================
// TYPES
// ============================================================================

export type TransportType = 'grpc-web' | 'sse' | 'auto';

export interface GrpcClientConfig {
    /** Base URL for the API */
    baseUrl: string;
    /** Transport type: 'grpc-web', 'sse', or 'auto' */
    transport?: TransportType;
    /** Request timeout in milliseconds */
    timeout?: number;
    /** Auth token for requests */
    authToken?: string;
    /** Custom headers */
    headers?: Record<string, string>;
    /** Enable debug logging */
    debug?: boolean;
}

export interface StreamOptions {
    /** Abort signal for cancellation */
    signal?: AbortSignal;
    /** Called when stream receives data */
    onData?: (data: any) => void;
    /** Called when stream errors */
    onError?: (error: Error) => void;
    /** Called when stream completes */
    onComplete?: () => void;
}

export interface UnaryResponse<T> {
    data: T;
    status: number;
    headers: Record<string, string>;
}

// ============================================================================
// GRPC CLIENT
// ============================================================================

export class GrpcClient {
    private config: Required<GrpcClientConfig>;
    private transport: TransportType;

    constructor(config: GrpcClientConfig) {
        this.config = {
            baseUrl: config.baseUrl,
            transport: config.transport || 'auto',
            timeout: config.timeout || 30000,
            authToken: config.authToken || '',
            headers: config.headers || {},
            debug: config.debug || false,
        };

        // Detect best transport
        this.transport = this.detectTransport();

        if (this.config.debug) {
            console.log(`[GrpcClient] Using transport: ${this.transport}`);
        }
    }

    /**
     * Detect the best transport method
     */
    private detectTransport(): TransportType {
        if (this.config.transport !== 'auto') {
            return this.config.transport;
        }

        // Check for gRPC-Web support
        // In modern browsers, we can use gRPC-Web with proper CORS setup
        // For now, default to SSE which works universally
        if (typeof window !== 'undefined' && 'TextDecoder' in window) {
            // Could use gRPC-Web, but SSE is more universally supported
            return 'sse';
        }

        return 'sse';
    }

    /**
     * Get default headers
     */
    private getHeaders(): Record<string, string> {
        const headers: Record<string, string> = {
            'Content-Type': 'application/json',
            ...this.config.headers,
        };

        if (this.config.authToken) {
            headers['Authorization'] = `Bearer ${this.config.authToken}`;
        }

        return headers;
    }

    /**
     * Make a unary (request-response) call
     */
    async unary<TReq, TRes>(
        method: string,
        request: TReq,
        options?: { signal?: AbortSignal }
    ): Promise<UnaryResponse<TRes>> {
        const url = `${this.config.baseUrl}${method}`;

        if (this.config.debug) {
            console.log(`[GrpcClient] Unary call: ${method}`, request);
        }

        const response = await fetch(url, {
            method: 'POST',
            headers: this.getHeaders(),
            body: JSON.stringify(request),
            signal: options?.signal,
        });

        if (!response.ok) {
            throw new GrpcError(
                `Request failed: ${response.statusText}`,
                response.status
            );
        }

        const data = await response.json();

        // Extract headers
        const headers: Record<string, string> = {};
        response.headers.forEach((value, key) => {
            headers[key] = value;
        });

        return { data, status: response.status, headers };
    }

    /**
     * Make a server streaming call
     * Returns an async iterator for the stream
     */
    async *serverStream<TReq, TRes>(
        method: string,
        request: TReq,
        options?: StreamOptions
    ): AsyncGenerator<TRes, void, unknown> {
        const url = `${this.config.baseUrl}${method}`;

        if (this.config.debug) {
            console.log(`[GrpcClient] Server stream: ${method}`, request);
        }

        if (this.transport === 'sse') {
            yield* this.sseStream<TReq, TRes>(url, request, options);
        } else {
            yield* this.grpcWebStream<TReq, TRes>(url, request, options);
        }
    }

    /**
     * SSE-based streaming implementation
     */
    private async *sseStream<TReq, TRes>(
        url: string,
        request: TReq,
        options?: StreamOptions
    ): AsyncGenerator<TRes, void, unknown> {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                ...this.getHeaders(),
                'Accept': 'text/event-stream',
            },
            body: JSON.stringify(request),
            signal: options?.signal,
        });

        if (!response.ok) {
            const error = new GrpcError(
                `Stream failed: ${response.statusText}`,
                response.status
            );
            options?.onError?.(error);
            throw error;
        }

        if (!response.body) {
            throw new GrpcError('No response body', 500);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        try {
            while (true) {
                const { done, value } = await reader.read();

                if (done) {
                    options?.onComplete?.();
                    break;
                }

                buffer += decoder.decode(value, { stream: true });

                // Parse SSE events
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);

                        if (data === '[DONE]') {
                            options?.onComplete?.();
                            return;
                        }

                        try {
                            const parsed = JSON.parse(data) as TRes;
                            options?.onData?.(parsed);
                            yield parsed;
                        } catch (e) {
                            if (this.config.debug) {
                                console.warn('[GrpcClient] Failed to parse SSE data:', data);
                            }
                        }
                    }
                }
            }
        } catch (error: any) {
            if (error.name === 'AbortError') {
                if (this.config.debug) {
                    console.log('[GrpcClient] Stream aborted');
                }
                return;
            }
            options?.onError?.(error);
            throw error;
        }
    }

    /**
     * gRPC-Web streaming implementation (placeholder for full implementation)
     */
    private async *grpcWebStream<TReq, TRes>(
        url: string,
        request: TReq,
        options?: StreamOptions
    ): AsyncGenerator<TRes, void, unknown> {
        // For full gRPC-Web support, you would use @grpc/grpc-js or grpc-web package
        // This is a placeholder that falls back to SSE
        if (this.config.debug) {
            console.log('[GrpcClient] gRPC-Web not fully implemented, falling back to SSE');
        }
        yield* this.sseStream<TReq, TRes>(url, request, options);
    }

    /**
     * Create a bidirectional stream
     * Uses WebSocket for true bidirectional communication
     */
    createBidiStream<TReq, TRes>(
        method: string,
        options?: StreamOptions
    ): BidiStream<TReq, TRes> {
        const wsUrl = this.config.baseUrl
            .replace('http://', 'ws://')
            .replace('https://', 'wss://');

        return new BidiStream<TReq, TRes>(`${wsUrl}${method}`, {
            headers: this.getHeaders(),
            debug: this.config.debug,
            ...options,
        });
    }

    /**
     * Set auth token
     */
    setAuthToken(token: string): void {
        this.config.authToken = token;
    }

    /**
     * Set custom header
     */
    setHeader(key: string, value: string): void {
        this.config.headers[key] = value;
    }
}

// ============================================================================
// BIDIRECTIONAL STREAM
// ============================================================================

interface BidiStreamOptions extends StreamOptions {
    headers?: Record<string, string>;
    debug?: boolean;
}

export class BidiStream<TReq, TRes> {
    private ws: WebSocket | null = null;
    private messageQueue: TRes[] = [];
    private resolvers: Array<(value: TRes) => void> = [];
    private closed = false;
    private options: BidiStreamOptions;

    constructor(private url: string, options: BidiStreamOptions = {}) {
        this.options = options;
        this.connect();
    }

    private connect(): void {
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
            if (this.options.debug) {
                console.log('[BidiStream] Connected');
            }
        };

        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data) as TRes;
                this.options.onData?.(data);

                if (this.resolvers.length > 0) {
                    const resolver = this.resolvers.shift()!;
                    resolver(data);
                } else {
                    this.messageQueue.push(data);
                }
            } catch (e) {
                if (this.options.debug) {
                    console.warn('[BidiStream] Failed to parse message:', event.data);
                }
            }
        };

        this.ws.onerror = (error) => {
            this.options.onError?.(new Error('WebSocket error'));
        };

        this.ws.onclose = () => {
            this.closed = true;
            this.options.onComplete?.();
        };
    }

    /**
     * Send a message to the server
     */
    send(message: TReq): void {
        if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            throw new Error('WebSocket not connected');
        }
    }

    /**
     * Receive the next message
     */
    async receive(): Promise<TRes> {
        if (this.messageQueue.length > 0) {
            return this.messageQueue.shift()!;
        }

        if (this.closed) {
            throw new Error('Stream closed');
        }

        return new Promise((resolve) => {
            this.resolvers.push(resolve);
        });
    }

    /**
     * Async iterator for receiving messages
     */
    async *[Symbol.asyncIterator](): AsyncGenerator<TRes, void, unknown> {
        while (!this.closed) {
            try {
                yield await this.receive();
            } catch {
                break;
            }
        }
    }

    /**
     * Close the stream
     */
    close(): void {
        this.closed = true;
        this.ws?.close();
    }
}

// ============================================================================
// ERROR CLASS
// ============================================================================

export class GrpcError extends Error {
    constructor(
        message: string,
        public readonly code: number,
        public readonly details?: any
    ) {
        super(message);
        this.name = 'GrpcError';
    }
}

// ============================================================================
// FACTORY FUNCTION
// ============================================================================

let defaultClient: GrpcClient | null = null;

/**
 * Get or create the default gRPC client
 */
export function getGrpcClient(config?: Partial<GrpcClientConfig>): GrpcClient {
    if (!defaultClient || config) {
        defaultClient = new GrpcClient({
            baseUrl: config?.baseUrl || '/api/v1',
            transport: config?.transport || 'auto',
            timeout: config?.timeout || 30000,
            authToken: config?.authToken || '',
            headers: config?.headers || {},
            debug: config?.debug || process.env.NODE_ENV === 'development',
        });
    }
    return defaultClient;
}

export default GrpcClient;
