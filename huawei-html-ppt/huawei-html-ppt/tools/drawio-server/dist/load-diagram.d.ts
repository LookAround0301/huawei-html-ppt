export type LoadResult = {
    ok: true;
    xml: string;
} | {
    ok: false;
    error: string;
};
/**
 * Decode one compressed page body (base64 → raw deflate → URI-decode).
 * Returns null if the text isn't in that format.
 */
export declare function decompressPageContent(compressed: string): string | null;
/**
 * Parse the content of a .drawio file into the canonical session shape:
 * an <mxfile> whose every page holds plain <mxGraphModel> XML. Accepts a
 * bare <mxGraphModel> (wrapped into a one-page mxfile) and decompresses
 * any compressed pages.
 */
export declare function parseDrawioFileContent(content: string): LoadResult;
//# sourceMappingURL=load-diagram.d.ts.map