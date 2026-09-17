/**
 * XML Validation and Auto-Fix for draw.io diagrams
 * Copied from lib/utils.ts to avoid cross-package imports
 */
/**
 * Validates draw.io XML structure for common issues
 * Uses DOM parsing + additional regex checks for high accuracy
 * @param xml - The XML string to validate
 * @returns null if valid, error message string if invalid
 */
export declare function validateMxCellStructure(xml: string): string | null;
/**
 * Attempts to auto-fix common XML issues in draw.io diagrams
 * @param xml - The XML string to fix
 * @returns Object with fixed XML and list of fixes applied
 */
export declare function autoFixXml(xml: string): {
    fixed: string;
    fixes: string[];
};
/**
 * Validates XML and attempts to fix if invalid
 * @param xml - The XML string to validate and potentially fix
 * @returns Object with validation result, fixed XML if applicable, and fixes applied
 */
export declare function validateAndFixXml(xml: string): {
    valid: boolean;
    error: string | null;
    fixed: string | null;
    fixes: string[];
};
/**
 * Check if mxCell XML output is complete (not truncated).
 * Uses a robust approach that handles any LLM provider's wrapper tags
 * by finding the last valid mxCell ending and checking if suffix is just closing tags.
 * @param xml - The XML string to check (can be undefined/null)
 * @returns true if XML appears complete, false if truncated or empty
 */
export declare function isMxCellXmlComplete(xml: string | undefined | null): boolean;
//# sourceMappingURL=xml-validation.d.ts.map