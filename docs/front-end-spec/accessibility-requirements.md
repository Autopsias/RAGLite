# Accessibility Requirements

## MCP Client Responsibility

**Level: N/A for Custom UI** - RAGLite has no custom interface; accessibility is handled by MCP-compatible clients (Claude Desktop, etc.)

**RAGLite's Accessibility Contribution:**

While we don't control the visual presentation, RAGLite ensures responses are inherently accessible:

1. **Text-Native Responses**
   - All responses are plain text or markdown (no visual-only content)
   - No reliance on color, images, or visual formatting to convey meaning
   - Screen readers can process all response content without loss of information

2. **Structured, Scannable Content**
   - Clear headings (**bold** for sections like "Sources:", "Key Findings:")
   - Bulleted lists for scannable information
   - Tables use proper markdown structure with headers
   - Semantic hierarchy maintained (summary → details → sources)

3. **Clear Language & Terminology**
   - Professional but plain language (avoiding unnecessary jargon)
   - Financial terms used appropriately for domain (not oversimplified)
   - Abbreviations explained on first use in context (e.g., "YoY (Year-over-Year)")
   - Numbers formatted with clear units ($, %, dates)

4. **Alternative Text Approach**
   - No images/charts in MVP responses (text-only)
   - Mermaid diagrams in spec documentation only (not runtime responses)
   - Future: If visualizations added, ensure text equivalents provided

5. **Cognitive Accessibility**
   - Concise responses (max 3 paragraphs for simple queries)
   - Progressive disclosure (simple answer first, details follow)
   - Clear error messages with actionable next steps
   - Consistent response formats reduce cognitive load

## Future Considerations (Custom Web UI Post-MVP)

If custom UI is built, ensure:
- WCAG 2.1 Level AA compliance minimum
- Keyboard navigation for all interactive elements
- Color contrast ratios 4.5:1 for text, 3:1 for UI components
- Focus indicators visible and high-contrast
- Form labels and ARIA attributes for dynamic content

---
