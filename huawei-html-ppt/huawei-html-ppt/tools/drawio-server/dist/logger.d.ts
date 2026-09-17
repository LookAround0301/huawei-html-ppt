/**
 * Logger for MCP server
 *
 * CRITICAL: MCP servers communicate via STDIO (stdin/stdout).
 * Using console.log() will corrupt the JSON-RPC protocol messages.
 * ALL logging MUST use console.error() which writes to stderr.
 */
export declare const log: {
    info: (msg: string, ...args: unknown[]) => void;
    error: (msg: string, ...args: unknown[]) => void;
    debug: (msg: string, ...args: unknown[]) => void;
    warn: (msg: string, ...args: unknown[]) => void;
};
//# sourceMappingURL=logger.d.ts.map