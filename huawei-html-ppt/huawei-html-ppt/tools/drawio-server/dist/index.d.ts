#!/usr/bin/env node
/**
 * MCP Server for Next AI Draw.io
 *
 * Enables AI agents (Claude Desktop, Cursor, etc.) to generate and edit
 * draw.io diagrams with real-time browser preview.
 *
 * Uses an embedded HTTP server - no external dependencies required.
 *
 * Multi-page support
 * ------------------
 * The canonical in-memory shape for the session XML is always an <mxfile>
 * containing one or more <diagram> pages. Legacy callers that pass a bare
 * <mxGraphModel> to create_new_diagram are auto-wrapped into a single-page
 * mxfile. All page-targeting parameters (page_id / page_name / page_index)
 * on edit_diagram, get_diagram, and export_diagram are optional and default
 * to the first page. See packages/mcp-server/src/pages.ts for the helper
 * surface.
 */
export {};
//# sourceMappingURL=index.d.ts.map