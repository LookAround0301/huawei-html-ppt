/**
 * ID-based diagram operations
 *
 * The xmlContent argument may be either a bare <mxGraphModel> (legacy) or a
 * full <mxfile> with one or more <diagram> pages. For mxfile inputs, an
 * optional pageSelector identifies which page to edit; when omitted, the
 * first page is targeted (the "active page by convention" — see pages.ts).
 */
import { type PageSelector } from "./pages.js";
export interface DiagramOperation {
    operation: "update" | "add" | "delete";
    cell_id: string;
    new_xml?: string;
}
export interface OperationError {
    type: "update" | "add" | "delete";
    cellId: string;
    message: string;
}
export interface ApplyOperationsResult {
    result: string;
    errors: OperationError[];
}
/**
 * Apply diagram operations (update/add/delete) using ID-based lookup.
 *
 * @param xmlContent - The diagram XML. May be either a bare <mxGraphModel> or
 *                     a full <mxfile> with one or more <diagram> children.
 * @param operations - Array of operations to apply.
 * @param pageSelector - Optional page selector for multi-page docs. Defaults
 *                       to the first page.
 * @returns Object with result XML (same shape as input) and any per-op errors.
 */
export declare function applyDiagramOperations(xmlContent: string, operations: DiagramOperation[], pageSelector?: PageSelector): ApplyOperationsResult;
//# sourceMappingURL=diagram-operations.d.ts.map