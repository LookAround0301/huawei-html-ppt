export type EditGateResult = {
    ok: true;
} | {
    ok: false;
    reason: "no-context" | "stale";
};
/**
 * Structural fingerprint of a diagram document: page names + each page's
 * <root> subtree, ignoring everything draw.io rewrites on re-serialisation
 * (mxfile/mxGraphModel attributes, diagram ids, formatting). A bare
 * <mxGraphModel> fingerprints identically to its single-page mxfile wrapping.
 * Unparseable input falls back to the trimmed raw string, degrading to the
 * plain string comparison.
 *
 * `includeNames=false` drops page names from the fingerprint — used when the
 * other side of a comparison is a bare <mxGraphModel>, which carries no page
 * name at all (normalizeToMxfile would invent "Page-1", falsely mismatching
 * any real page name).
 */
export declare function contentFingerprint(xml: string, includeNames?: boolean): string;
export declare function checkEditGate(lastSeenXml: string, liveXml: string): EditGateResult;
//# sourceMappingURL=edit-gate.d.ts.map