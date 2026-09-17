/**
 * Logger for MCP server
 *
 * CRITICAL: MCP servers communicate via STDIO (stdin/stdout).
 * Using console.log() will corrupt the JSON-RPC protocol messages.
 * ALL logging MUST use console.error() which writes to stderr.
 */
export const log = {
    info: (msg, ...args) => {
        console.error(`[MCP-DrawIO] [INFO] ${msg}`, ...args);
    },
    error: (msg, ...args) => {
        console.error(`[MCP-DrawIO] [ERROR] ${msg}`, ...args);
    },
    debug: (msg, ...args) => {
        if (process.env.DEBUG === "true") {
            console.error(`[MCP-DrawIO] [DEBUG] ${msg}`, ...args);
        }
    },
    warn: (msg, ...args) => {
        console.error(`[MCP-DrawIO] [WARN] ${msg}`, ...args);
    },
};
//# sourceMappingURL=logger.js.map