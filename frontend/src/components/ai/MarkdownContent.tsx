import React from "react";

interface MarkdownContentProps {
  content: string;
  className?: string;
}

/**
 * Format inline tokens like **bold**, *italic*, and `code`.
 */
function renderInlineFormatting(text: string): React.ReactNode {
  // Regex to split on bold (**text**), code (`text`), or italic (*text*)
  const tokens = text.split(/(\*\*.*?\*\*|`.*?`|\*.*?\*)/g);

  return tokens.map((token, idx) => {
    if (token.startsWith("**") && token.endsWith("**")) {
      return (
        <strong key={idx} className="font-semibold text-slate-900">
          {token.slice(2, -2)}
        </strong>
      );
    }
    if (token.startsWith("`") && token.endsWith("`")) {
      return (
        <code
          key={idx}
          className="rounded bg-slate-100 px-1 py-0.5 font-mono text-xs text-blue-700"
        >
          {token.slice(1, -1)}
        </code>
      );
    }
    if (token.startsWith("*") && token.endsWith("*") && token.length > 2) {
      return (
        <em key={idx} className="italic text-slate-600">
          {token.slice(1, -1)}
        </em>
      );
    }
    return token;
  });
}

/**
 * Renders structured markdown content including headings, bullet lists,
 * tables, and paragraphs with professional typography.
 */
export function MarkdownContent({ content, className = "" }: MarkdownContentProps) {
  if (!content) return null;

  // Split lines and group into structural blocks
  const lines = content.split("\n");
  const blocks: React.ReactNode[] = [];
  let currentList: string[] = [];
  let currentTable: string[] = [];

  const flushList = () => {
    if (currentList.length > 0) {
      const listItems = [...currentList];
      currentList = [];
      blocks.push(
        <ul
          key={`list-${blocks.length}`}
          className="my-2 space-y-1 pl-4 text-sm leading-relaxed text-slate-700 list-disc"
        >
          {listItems.map((item, idx) => (
            <li key={idx} className="pl-1">
              {renderInlineFormatting(item)}
            </li>
          ))}
        </ul>
      );
    }
  };

  const flushTable = () => {
    if (currentTable.length > 0) {
      const tableLines = [...currentTable];
      currentTable = [];

      const rows = tableLines.map((row) =>
        row
          .split("|")
          .map((c) => c.trim())
          .filter((_, idx, arr) => idx > 0 && idx < arr.length - 1)
      );

      if (rows.length >= 2) {
        const headers = rows[0];
        // skip separator line (e.g. |---|---|)
        const dataRows = rows.slice(rows[1][0]?.includes("-") ? 2 : 1);

        blocks.push(
          <div
            key={`table-${blocks.length}`}
            className="my-3 overflow-x-auto rounded-lg border border-slate-200"
          >
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-semibold">
                <tr>
                  {headers.map((h, idx) => (
                    <th key={idx} className="px-3 py-2">
                      {renderInlineFormatting(h)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {dataRows.map((r, rIdx) => (
                  <tr key={rIdx} className="hover:bg-slate-50/50">
                    {r.map((cell, cIdx) => (
                      <td key={cIdx} className="px-3 py-2 text-slate-700">
                        {renderInlineFormatting(cell)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      }
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i];
    const trimmed = rawLine.trim();

    // Table line
    if (trimmed.startsWith("|") && trimmed.endsWith("|")) {
      flushList();
      currentTable.push(trimmed);
      continue;
    } else {
      flushTable();
    }

    // List line (- or *)
    if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      currentList.push(trimmed.slice(2).trim());
      continue;
    } else {
      flushList();
    }

    // Empty line
    if (!trimmed) {
      continue;
    }

    // Heading lines
    if (trimmed.startsWith("### ")) {
      blocks.push(
        <h4
          key={`h4-${blocks.length}`}
          className="mt-3 mb-1 text-base font-semibold text-slate-900 tracking-tight"
        >
          {renderInlineFormatting(trimmed.slice(4))}
        </h4>
      );
      continue;
    }

    if (trimmed.startsWith("## ")) {
      blocks.push(
        <h3
          key={`h3-${blocks.length}`}
          className="mt-3.5 mb-1.5 text-lg font-semibold text-slate-900 tracking-tight"
        >
          {renderInlineFormatting(trimmed.slice(3))}
        </h3>
      );
      continue;
    }

    if (trimmed.startsWith("# ")) {
      blocks.push(
        <h2
          key={`h2-${blocks.length}`}
          className="mt-4 mb-2 text-xl font-bold text-slate-900 tracking-tight"
        >
          {renderInlineFormatting(trimmed.slice(2))}
        </h2>
      );
      continue;
    }

    // Footer note (*Data source: ...*)
    if (trimmed.startsWith("*Data source:") && trimmed.endsWith("*")) {
      // Handled via ResponseEvidence or rendered as a subtle muted line
      blocks.push(
        <p
          key={`footer-${blocks.length}`}
          className="mt-2 text-xs italic text-slate-500 border-t border-slate-100 pt-1.5"
        >
          {trimmed.slice(1, -1)}
        </p>
      );
      continue;
    }

    // Normal paragraph
    blocks.push(
      <p
        key={`p-${blocks.length}`}
        className="my-1.5 text-sm leading-relaxed text-slate-800 font-normal"
      >
        {renderInlineFormatting(trimmed)}
      </p>
    );
  }

  flushList();
  flushTable();

  return <div className={`space-y-1 ${className}`}>{blocks}</div>;
}

