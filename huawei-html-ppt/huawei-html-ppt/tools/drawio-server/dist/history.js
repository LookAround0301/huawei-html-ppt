/**
 * Simple diagram history - matches Next.js app pattern
 * Stores {xml, svg} entries in a circular buffer
 */
import { log } from "./logger.js";
const MAX_HISTORY = 20;
const historyStore = new Map();
export function addHistory(sessionId, xml, svg = "") {
    let history = historyStore.get(sessionId);
    if (!history) {
        history = [];
        historyStore.set(sessionId, history);
    }
    // Dedupe: skip if same as last entry
    const last = history[history.length - 1];
    if (last?.xml === xml) {
        return history.length - 1;
    }
    history.push({ xml, svg });
    // Circular buffer
    if (history.length > MAX_HISTORY) {
        history.shift();
    }
    log.debug(`History: session=${sessionId}, entries=${history.length}`);
    return history.length - 1;
}
export function getHistory(sessionId) {
    return historyStore.get(sessionId) || [];
}
export function getHistoryEntry(sessionId, index) {
    const history = historyStore.get(sessionId);
    return history?.[index];
}
export function clearHistory(sessionId) {
    historyStore.delete(sessionId);
}
export function updateLastHistorySvg(sessionId, svg) {
    const history = historyStore.get(sessionId);
    if (!history || history.length === 0)
        return false;
    const last = history[history.length - 1];
    if (!last.svg) {
        last.svg = svg;
        return true;
    }
    return false;
}
//# sourceMappingURL=history.js.map