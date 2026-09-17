/**
 * Simple diagram history - matches Next.js app pattern
 * Stores {xml, svg} entries in a circular buffer
 */
export declare function addHistory(sessionId: string, xml: string, svg?: string): number;
export declare function getHistory(sessionId: string): Array<{
    xml: string;
    svg: string;
}>;
export declare function getHistoryEntry(sessionId: string, index: number): {
    xml: string;
    svg: string;
} | undefined;
export declare function clearHistory(sessionId: string): void;
export declare function updateLastHistorySvg(sessionId: string, svg: string): boolean;
//# sourceMappingURL=history.d.ts.map