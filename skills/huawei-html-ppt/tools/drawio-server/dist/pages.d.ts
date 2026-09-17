/**
 * Multi-page (mxfile) helpers for draw.io diagrams.
 *
 * The on-disk and embed-protocol shape of a draw.io document is:
 *
 *   <mxfile host="...">
 *     <diagram id="..." name="...">
 *       <mxGraphModel><root><mxCell .../>...</root></mxGraphModel>
 *     </diagram>
 *     ...one or more <diagram> children...
 *   </mxfile>
 *
 * This module centralises page CRUD so that index.ts, xml-validation.ts,
 * and diagram-operations.ts can all agree on:
 *   - what "the canonical in-memory shape" is (always mxfile),
 *   - how to find a page (id, name, or index),
 *   - how to add/rename/delete pages without re-parsing ad-hoc.
 */
export interface PageInfo {
    id: string;
    name: string;
    index: number;
    cellCount: number;
}
/** Selector used by all multi-page-aware tools. All fields optional. */
export interface PageSelector {
    page_id?: string;
    page_name?: string;
    page_index?: number;
}
/** True if the selector targets a specific page (any field set). */
export declare function hasPageSelector(s?: PageSelector | null): boolean;
/**
 * Generate a short page id similar in shape to drawio's auto-assigned ids.
 * Format: 12 chars alphanumeric with a single dash. Not a UUID — drawio itself
 * uses short ids; collisions are still astronomically unlikely for one session.
 */
export declare function generatePageId(): string;
/** Cheap regex check — does the XML start with an <mxfile> root? */
export declare function isMxFile(xml: string): boolean;
/** Cheap regex check — does the XML start with a bare <mxGraphModel>? */
export declare function isMxGraphModel(xml: string): boolean;
/**
 * Wrap a bare <mxGraphModel> XML string in <mxfile><diagram>...</diagram></mxfile>.
 * If the input is already an mxfile, returns it unchanged.
 * If the input is neither shape, returns null so the caller can surface a clear error.
 *
 * Strips any leading <?xml ?> declaration before embedding — a declaration is
 * only valid at the very start of a document, never inside a <diagram>.
 */
export declare function normalizeToMxfile(xml: string, opts?: {
    pageId?: string;
    pageName?: string;
    host?: string;
}): string | null;
/**
 * Parse an mxfile XML string. Returns null on parse error or if the root
 * isn't <mxfile> — callers are expected to have run normalizeToMxfile first.
 */
export declare function parseMxfile(xml: string): Document | null;
/** Serialise an mxfile doc back to a string via the global XMLSerializer polyfill. */
export declare function serializeMxfile(doc: Document): string;
export type PageProjection = {
    ok: true;
    xml: string;
    index: number;
    name: string;
} | {
    ok: false;
    reason: "parse" | "notfound";
};
/**
 * Project a single page out of an mxfile string into a standalone one-page
 * <mxfile>. Used by get_diagram and export_diagram so the three call sites
 * share one parse → find → serialise path.
 *
 * Returns { ok:false, reason:"parse" } if the xml isn't a parseable mxfile,
 * or { ok:false, reason:"notfound" } if the selector matches no page.
 */
export declare function projectPage(xml: string, selector: PageSelector): PageProjection;
/** Walk every <diagram> child of <mxfile> and return summary info. */
export declare function listPagesFromDoc(doc: Document): PageInfo[];
/**
 * Resolve a page selector to its <diagram> element.
 * Resolution order: page_id → page_name → page_index → default (first page).
 *
 * When no selector field is set we return the first page — the "active page
 * by convention" mentioned in §3.4 of the design doc.
 */
export declare function findPageElement(doc: Document, selector?: PageSelector): {
    element: Element;
    index: number;
} | null;
/**
 * Append a new <diagram> to the mxfile doc. The new page's model defaults to
 * an empty <mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/></root></mxGraphModel>.
 *
 * `opts.xml` must be a BARE <mxGraphModel> — passing a full <mxfile> would
 * end up nested inside <diagram>, which is malformed. We reject the mxfile
 * shape explicitly and strip any <?xml ?> declaration (only valid at
 * document start, never inside <diagram>).
 *
 * Returns the new PageInfo. Throws if the requested id collides or the xml
 * shape is wrong.
 */
export declare function addPageToDoc(doc: Document, opts?: {
    id?: string;
    name?: string;
    xml?: string;
}): PageInfo;
/** Rename the page matched by selector. Returns true on success. */
export declare function renamePageInDoc(doc: Document, selector: PageSelector, newName: string): boolean;
/**
 * Delete a page. Refuses to delete the last remaining page — the embed needs
 * at least one diagram to render anything, and silently recreating one would
 * be surprising behaviour for an MCP caller.
 */
export declare function deletePageFromDoc(doc: Document, selector: PageSelector): {
    ok: boolean;
    reason?: string;
    deletedId?: string;
    deletedIndex?: number;
};
//# sourceMappingURL=pages.d.ts.map