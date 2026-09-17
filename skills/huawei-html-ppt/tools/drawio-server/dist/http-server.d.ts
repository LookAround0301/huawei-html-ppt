/**
 * Embedded HTTP Server for MCP
 * Serves draw.io embed with state sync and history UI
 */
interface SessionState {
    xml: string;
    version: number;
    lastUpdated: Date;
    svg?: string;
    syncRequested?: number;
    exportFormat?: "png" | "svg";
    exportXml?: string;
    exportData?: string;
}
export declare const stateStore: Map<string, SessionState>;
export declare function getState(sessionId: string): SessionState | undefined;
export declare function setState(sessionId: string, xml: string, svg?: string): number;
/**
 * Ask the browser bridge to export the current diagram as png/svg.
 *
 * When `projectionXml` is given (a single-page <mxfile>), the bridge loads it
 * first, waits for draw.io's own load event, exports, then reloads the
 * session's real document — so a page-targeted export never mutates the
 * canonical session state and needs no fixed-delay guessing on the server.
 *
 * Returns false when the session is unknown. Callers should then poll
 * `getState(sessionId)?.exportData` for the result.
 */
export declare function requestExport(sessionId: string, format: "png" | "svg", projectionXml?: string): boolean;
export declare function requestSync(sessionId: string): boolean;
export declare function waitForSync(sessionId: string, timeoutMs?: number): Promise<boolean>;
export declare function startHttpServer(port?: number): Promise<number>;
export declare function stopHttpServer(): void;
export declare function shutdown(): void;
export declare function getServerPort(): number;
export {};
//# sourceMappingURL=http-server.d.ts.map