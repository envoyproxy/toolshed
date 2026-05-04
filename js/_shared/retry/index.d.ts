export declare const RETRIABLE_STATUSES: Set<number>;
export declare const RETRIABLE_CODES: Set<string>;
export interface RetryOptions {
    retries: number;
    baseDelayMs: number;
    maxDelayMs: number;
}
export declare const parseRetryAfter: (err: unknown) => number | undefined;
export declare const parseIntInput: (raw: string, name: string, defaultVal: number, label: string, warn: (msg: string) => void) => number;
export declare const withRetry: <T>(fn: () => Promise<T>, { retries, baseDelayMs, maxDelayMs }: RetryOptions, label: string, warn: (msg: string) => void) => Promise<T>;
//# sourceMappingURL=index.d.ts.map