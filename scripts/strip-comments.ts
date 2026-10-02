#!/usr/bin/env bun
/**
 * stripcomment - High-performance code comment and junk note cleaner.
 * 
 * Cleans up:
 * - HTML comments (<!-- ... -->) in .vue and .html templates
 * - Single-line comments (// ...) in .ts, .js, and Vue <script>
 * - Multi-line comments (/* ... * /) in .ts, .js, .css, and Vue <script>/<style>
 * - Python comments (# ...) in .py files (optional / via flag or target path)
 * 
 * Preserves:
 * - Compiler & linter directives (@ts-*, eslint-*, biome-ignore, noqa, type: ignore, pragma)
 * - Strings ('...', "...", `...` template literals including markdown & URLs)
 * - UI display text (e.g. "VN30F1M // DESK PULSE PREVIEW" inside template markup)
 * - Regex literals (/.../)
 * - Shebang lines (#!/...)
 */

import { existsSync, readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { extname, join, relative, resolve } from "node:path";

interface StripOptions {
  dryRun?: boolean;
  keepJsDoc?: boolean;
  includePy?: boolean;
  quiet?: boolean;
  verbose?: boolean;
}

interface FileResult {
  filePath: string;
  commentsRemoved: number;
  linesRemoved: number;
  bytesSaved: number;
  changed: boolean;
}

// Preserve compiler and toolchain directives
const JS_DIRECTIVE_PATTERN = /^\/\/\s*(@ts-|eslint-|biome-ignore|istanbul|c8|prettier-ignore|vite-ignore|webpack\w+:)/i;
const BLOCK_DIRECTIVE_PATTERN = /^\/\*\s*(@ts-|eslint-|biome-ignore|istanbul|c8|prettier-ignore|vite-ignore)/i;
const PY_DIRECTIVE_PATTERN = /^\s*#\s*(noqa|type:\s*ignore|pragma:\s*no cover|fmt:\s*off|fmt:\s*on|pylint:|mypy:)/i;

/**
 * Strips comments from JavaScript / TypeScript code using a robust state machine.
 */
export function stripJsComments(
  code: string,
  options: { keepJsDoc?: boolean } = {}
): { code: string; count: number } {
  let count = 0;
  let out = "";
  const len = code.length;
  let i = 0;

  // Context stack for template literal interpolations
  // 'root' | 'template' | 'interp'
  type InterpContext = { type: "interp"; braceDepth: number };
  const stack: (string | InterpContext)[] = ["root"];

  // Helper to get previous non-whitespace char for regex detection
  function getPrevNonWs(str: string): string {
    for (let j = str.length - 1; j >= 0; j--) {
      const c = str[j];
      if (c !== " " && c !== "\t" && c !== "\r" && c !== "\n") {
        return c;
      }
    }
    return "";
  }

  while (i < len) {
    const ch = code[i];
    const next = i + 1 < len ? code[i + 1] : "";
    const currentContext = stack[stack.length - 1];
    const inTemplate = currentContext === "template";

    // Handle string escape in template literals
    if (inTemplate) {
      if (ch === "\\") {
        out += ch;
        i++;
        if (i < len) {
          out += code[i];
          i++;
        }
        continue;
      }
      if (ch === "`") {
        out += ch;
        stack.pop();
        i++;
        continue;
      }
      if (ch === "$" && next === "{") {
        out += "${";
        stack.push({ type: "interp", braceDepth: 1 });
        i += 2;
        continue;
      }
      out += ch;
      i++;
      continue;
    }

    // Single quotes string: '...'
    if (ch === "'") {
      out += ch;
      i++;
      while (i < len) {
        const c = code[i];
        out += c;
        if (c === "\\") {
          i++;
          if (i < len) {
            out += code[i];
          }
        } else if (c === "'") {
          i++;
          break;
        }
        i++;
      }
      continue;
    }

    // Double quotes string: "..."
    if (ch === '"') {
      out += ch;
      i++;
      while (i < len) {
        const c = code[i];
        out += c;
        if (c === "\\") {
          i++;
          if (i < len) {
            out += code[i];
          }
        } else if (c === '"') {
          i++;
          break;
        }
        i++;
      }
      continue;
    }

    // Start of template literal: `...`
    if (ch === "`") {
      out += ch;
      stack.push("template");
      i++;
      continue;
    }

    // Track braces inside template interpolation ${ ... }
    if (typeof currentContext === "object" && currentContext.type === "interp") {
      if (ch === "{") {
        currentContext.braceDepth++;
      } else if (ch === "}") {
        currentContext.braceDepth--;
        if (currentContext.braceDepth === 0) {
          out += "}";
          stack.pop();
          i++;
          continue;
        }
      }
    }

    // Single-line comment: //...
    if (ch === "/" && next === "/") {
      let lineEnd = code.indexOf("\n", i);
      if (lineEnd === -1) lineEnd = len;
      const commentText = code.slice(i, lineEnd);

      if (JS_DIRECTIVE_PATTERN.test(commentText)) {
        out += commentText;
      } else {
        count++;
      }
      i = lineEnd;
      continue;
    }

    // Multi-line comment: /*...*/
    if (ch === "/" && next === "*") {
      const commentEnd = code.indexOf("*/", i + 2);
      const endPos = commentEnd === -1 ? len : commentEnd + 2;
      const commentText = code.slice(i, endPos);

      const isJsDoc = commentText.startsWith("/**") && !commentText.startsWith("/***");
      const isDirective = BLOCK_DIRECTIVE_PATTERN.test(commentText);

      if (isDirective || (options.keepJsDoc && isJsDoc)) {
        out += commentText;
      } else {
        count++;
      }
      i = endPos;
      continue;
    }

    // Regex literal check: /pattern/flags
    if (ch === "/") {
      const prev = getPrevNonWs(out);
      // Punctuators before a regex
      const isRegexPredecessor = /^[(=!+\-*%&|^~<?>:;,{}[\]?]/.test(prev) || prev === "";

      if (isRegexPredecessor) {
        // Scan regex
        out += ch;
        i++;
        let inCharClass = false;
        while (i < len) {
          const c = code[i];
          out += c;
          if (c === "\\") {
            i++;
            if (i < len) {
              out += code[i];
            }
          } else if (c === "[") {
            inCharClass = true;
          } else if (c === "]") {
            inCharClass = false;
          } else if (c === "/" && !inCharClass) {
            i++;
            // Read trailing flags
            while (i < len && /[a-z]/i.test(code[i])) {
              out += code[i];
              i++;
            }
            break;
          }
          i++;
        }
        continue;
      }
    }

    out += ch;
    i++;
  }

  return { code: out, count };
}

/**
 * Strips comments from CSS code.
 */
export function stripCssComments(code: string): { code: string; count: number } {
  let count = 0;
  let out = "";
  const len = code.length;
  let i = 0;

  while (i < len) {
    const ch = code[i];
    const next = i + 1 < len ? code[i + 1] : "";

    // Strings in CSS
    if (ch === '"' || ch === "'") {
      const quote = ch;
      out += quote;
      i++;
      while (i < len) {
        const c = code[i];
        out += c;
        if (c === "\\") {
          i++;
          if (i < len) out += code[i];
        } else if (c === quote) {
          i++;
          break;
        }
        i++;
      }
      continue;
    }

    // CSS comment: /*...*/
    if (ch === "/" && next === "*") {
      const commentEnd = code.indexOf("*/", i + 2);
      const endPos = commentEnd === -1 ? len : commentEnd + 2;
      count++;
      i = endPos;
      continue;
    }

    out += ch;
    i++;
  }

  return { code: out, count };
}

/**
 * Strips HTML comments (<!-- ... -->) from HTML / Vue template markup.
 */
export function stripHtmlComments(templateCode: string): { code: string; count: number } {
  let count = 0;
  // Replace <!-- ... --> with empty string
  const cleaned = templateCode.replace(/<!--[\s\S]*?-->/g, (match) => {
    count++;
    return "";
  });
  return { code: cleaned, count };
}

/**
 * Strips comments from Vue Single File Components (.vue).
 */
export function stripVueComments(
  content: string,
  options: { keepJsDoc?: boolean } = {}
): { code: string; count: number } {
  let totalCount = 0;

  // We scan top-level blocks: <script...>, <style...>, and template
  // To avoid breaking nested templates, we find all <script>...</script> and <style>...</style> blocks,
  // process their contents with JS/CSS comment strippers, and process outside regions with HTML comment stripper!
  const blockRegex = /(<script\b[^>]*>)([\s\S]*?)(<\/script>)|(<style\b[^>]*>)([\s\S]*?)(<\/style>)/gi;

  let lastIndex = 0;
  let result = "";
  let match: RegExpExecArray | null;

  while ((match = blockRegex.exec(content)) !== null) {
    const matchStart = match.index;
    const matchEnd = blockRegex.lastIndex;

    // Process preceding template / markup portion
    if (matchStart > lastIndex) {
      const templateChunk = content.slice(lastIndex, matchStart);
      const htmlRes = stripHtmlComments(templateChunk);
      totalCount += htmlRes.count;
      result += htmlRes.code;
    }

    if (match[1]) {
      // Script block
      const openTag = match[1];
      const scriptBody = match[2];
      const closeTag = match[3];

      const jsRes = stripJsComments(scriptBody, options);
      totalCount += jsRes.count;
      result += openTag + jsRes.code + closeTag;
    } else if (match[4]) {
      // Style block
      const openTag = match[4];
      const styleBody = match[5];
      const closeTag = match[6];

      const cssRes = stripCssComments(styleBody);
      totalCount += cssRes.count;
      result += openTag + cssRes.code + closeTag;
    }

    lastIndex = matchEnd;
  }

  // Trailing template portion
  if (lastIndex < content.length) {
    const templateChunk = content.slice(lastIndex);
    const htmlRes = stripHtmlComments(templateChunk);
    totalCount += htmlRes.count;
    result += htmlRes.code;
  }

  return { code: result, count: totalCount };
}

/**
 * Strips comments from Python code (.py).
 */
export function stripPythonComments(code: string): { code: string; count: number } {
  let count = 0;
  const lines = code.split("\n");
  const processedLines: string[] = [];

  for (let idx = 0; idx < lines.length; idx++) {
    const line = lines[idx];

    // Preserve shebang and encoding
    if (idx === 0 && line.startsWith("#!")) {
      processedLines.push(line);
      continue;
    }
    if (idx <= 1 && line.includes("-*- coding:")) {
      processedLines.push(line);
      continue;
    }

    // Preserve linter directives
    if (PY_DIRECTIVE_PATTERN.test(line)) {
      processedLines.push(line);
      continue;
    }

    // Check if line contains inline comment while respecting strings
    let inSingle = false;
    let inDouble = false;
    let inTripleSingle = false;
    let inTripleDouble = false;
    let commentIdx = -1;

    for (let c = 0; c < line.length; c++) {
      const char = line[c];
      const prev = c > 0 ? line[c - 1] : "";
      if (prev === "\\") continue;

      if (!inSingle && !inDouble) {
        if (line.slice(c, c + 3) === "'''") {
          inTripleSingle = !inTripleSingle;
          c += 2;
          continue;
        }
        if (line.slice(c, c + 3) === '"""') {
          inTripleDouble = !inTripleDouble;
          c += 2;
          continue;
        }
      }

      if (!inTripleSingle && !inTripleDouble) {
        if (char === "'" && !inDouble) {
          inSingle = !inSingle;
        } else if (char === '"' && !inSingle) {
          inDouble = !inDouble;
        } else if (char === "#" && !inSingle && !inDouble) {
          // Found comment start
          const commentPart = line.slice(c);
          if (
            commentPart.includes("noqa") ||
            commentPart.includes("type: ignore") ||
            commentPart.includes("pragma:")
          ) {
            // Keep directive comment
            commentIdx = -1;
          } else {
            commentIdx = c;
          }
          break;
        }
      }
    }

    if (commentIdx !== -1) {
      count++;
      const codePart = line.slice(0, commentIdx).trimEnd();
      if (codePart.length > 0) {
        processedLines.push(codePart);
      }
    } else {
      processedLines.push(line);
    }
  }

  return { code: processedLines.join("\n"), count };
}

/**
 * Cleans up empty lines and trailing whitespace.
 */
export function cleanCodeLayout(code: string): { code: string; linesRemoved: number } {
  const originalLines = code.split("\n");
  const cleanedLines: string[] = [];
  let prevWasEmpty = false;

  for (let i = 0; i < originalLines.length; i++) {
    const trimmedRight = originalLines[i].trimEnd();
    const isEmpty = trimmedRight.trim().length === 0;

    if (isEmpty) {
      if (!prevWasEmpty && cleanedLines.length > 0) {
        cleanedLines.push("");
        prevWasEmpty = true;
      }
    } else {
      cleanedLines.push(trimmedRight);
      prevWasEmpty = false;
    }
  }

  // Ensure trailing newline
  while (cleanedLines.length > 0 && cleanedLines[cleanedLines.length - 1] === "") {
    cleanedLines.pop();
  }
  cleanedLines.push("");

  let normalized = cleanedLines.join("\n");
  // Normalize opening braces with empty lines: {\n\n -> {\n
  normalized = normalized.replace(/\{\s*\n\s*\n+/g, "{\n");
  // Normalize empty braces: {\s*\n\s*} -> {}
  normalized = normalized.replace(/\{\s*\n\s*\}/g, "{}");

  const linesRemoved = originalLines.length - normalized.split("\n").length;
  return { code: normalized, linesRemoved };
}

/**
 * Process a single file.
 */
export function processFile(filePath: string, options: StripOptions): FileResult {
  const originalContent = readFileSync(filePath, "utf-8");
  const ext = extname(filePath).toLowerCase();

  let stripped = { code: originalContent, count: 0 };

  if (ext === ".vue") {
    stripped = stripVueComments(originalContent, { keepJsDoc: options.keepJsDoc });
  } else if (ext === ".ts" || ext === ".js" || ext === ".mjs" || ext === ".cjs") {
    stripped = stripJsComments(originalContent, { keepJsDoc: options.keepJsDoc });
  } else if (ext === ".css") {
    stripped = stripCssComments(originalContent);
  } else if (ext === ".html") {
    stripped = stripHtmlComments(originalContent);
  } else if (ext === ".py" && options.includePy) {
    stripped = stripPythonComments(originalContent);
  }

  if (stripped.count === 0) {
    return {
      filePath,
      commentsRemoved: 0,
      linesRemoved: 0,
      bytesSaved: 0,
      changed: false,
    };
  }

  const { code: finalContent, linesRemoved } = cleanCodeLayout(stripped.code);
  const bytesSaved = Buffer.byteLength(originalContent, "utf-8") - Buffer.byteLength(finalContent, "utf-8");

  if (!options.dryRun && finalContent !== originalContent) {
    writeFileSync(filePath, finalContent, "utf-8");
  }

  return {
    filePath,
    commentsRemoved: stripped.count,
    linesRemoved,
    bytesSaved,
    changed: finalContent !== originalContent,
  };
}

/**
 * Recursively find target files.
 */
function findFiles(targetPath: string, includePy: boolean): string[] {
  const ignoreDirs = new Set([
    "node_modules",
    ".nuxt",
    ".output",
    ".git",
    "dist",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
  ]);

  const targetExts = new Set([".vue", ".ts", ".js", ".mjs", ".css", ".html"]);
  if (includePy) {
    targetExts.add(".py");
  }

  const files: string[] = [];

  function traverse(dir: string) {
    const entries = readdirSync(dir);
    for (const entry of entries) {
      if (entry.startsWith(".") && entry !== ".env") {
        if (entry === ".git" || entry === ".nuxt" || entry === ".output") continue;
      }
      if (ignoreDirs.has(entry)) continue;

      const fullPath = join(dir, entry);
      const stat = statSync(fullPath);

      if (stat.isDirectory()) {
        traverse(fullPath);
      } else if (stat.isFile()) {
        const ext = extname(entry).toLowerCase();
        if (targetExts.has(ext)) {
          files.push(fullPath);
        }
      }
    }
  }

  if (statSync(targetPath).isDirectory()) {
    traverse(targetPath);
  } else {
    files.push(targetPath);
  }

  return files;
}

// Main CLI execution
async function main() {
  const args = process.argv.slice(2);

  if (args.includes("--help") || args.includes("-h")) {
    console.log(`
\x1b[35mstripcomment\x1b[0m - Dọn dẹp comment rác và note rác trong codebase

\x1b[1mCÁCH DÙNG:\x1b[0m
  bun scripts/strip-comments.ts [paths...] [tùy chọn]

\x1b[1mTÙY CHỌN:\x1b[0m
  --dry-run       Chạy thử nghiệm (in thống kê mà không ghi đè file)
  --keep-jsdoc    Giữ lại các khối JSDoc (/** ... */)
  --py            Quét và dọn dẹp cả file Python (.py)
  --all           Quét toàn bộ workspace (frontend + apps + packages)
  --quiet         Chỉ in kết quả tổng kết cuối cùng
  --help, -h      Hiện trợ giúp này

\x1b[1mVÍ DỤ:\x1b[0m
  bun scripts/strip-comments.ts frontend/pages
  bun scripts/strip-comments.ts frontend --dry-run
  bun scripts/strip-comments.ts frontend/pages/index.vue
  bun run stripcomment
`);
    process.exit(0);
  }

  const dryRun = args.includes("--dry-run");
  const keepJsDoc = args.includes("--keep-jsdoc");
  const includePy = args.includes("--py");
  const allWorkspace = args.includes("--all");
  const quiet = args.includes("--quiet");

  const pathArgs = args.filter((a) => !a.startsWith("--") && !a.startsWith("-"));

  let searchTargets: string[] = [];

  if (pathArgs.length > 0) {
    searchTargets = pathArgs.map((p) => resolve(process.cwd(), p));
  } else if (allWorkspace) {
    searchTargets = [process.cwd()];
  } else {
    // Default targets: frontend source code
    const cwd = process.cwd();
    const candidateDirs = [
      join(cwd, "frontend", "pages"),
      join(cwd, "frontend", "components"),
      join(cwd, "frontend", "layouts"),
      join(cwd, "frontend", "composables"),
      join(cwd, "frontend", "assets"),
      join(cwd, "frontend", "app.vue"),
    ];

    searchTargets = candidateDirs.filter((p) => existsSync(p));
    if (searchTargets.length === 0) {
      searchTargets = [cwd];
    }
  }

  console.log(`\x1b[35m✨ Bắt đầu quét & dọn dẹp comment rác...\x1b[0m ${dryRun ? "\x1b[33m[DRY-RUN]\x1b[0m" : ""}`);

  const allFiles: string[] = [];
  for (const target of searchTargets) {
    if (existsSync(target)) {
      allFiles.push(...findFiles(target, includePy));
    }
  }

  // Deduplicate files
  const uniqueFiles = Array.from(new Set(allFiles));
  console.log(`📁 Tìm thấy \x1b[36m${uniqueFiles.length}\x1b[0m tệp phù hợp để phân tích.`);

  let totalComments = 0;
  let totalLines = 0;
  let totalBytes = 0;
  let totalChangedFiles = 0;

  for (const file of uniqueFiles) {
    const res = processFile(file, {
      dryRun,
      keepJsDoc,
      includePy,
      quiet,
    });

    if (res.changed || res.commentsRemoved > 0) {
      totalComments += res.commentsRemoved;
      totalLines += res.linesRemoved;
      totalBytes += res.bytesSaved;
      totalChangedFiles++;

      if (!quiet) {
        const rel = relative(process.cwd(), file);
        console.log(
          `  \x1b[32m✔\x1b[0m \x1b[1m${rel}\x1b[0m: -\x1b[33m${res.commentsRemoved}\x1b[0m comments, -\x1b[36m${res.linesRemoved}\x1b[0m dòng (${res.bytesSaved > 0 ? `-${res.bytesSaved} bytes` : ""})`
        );
      }
    }
  }

  console.log("\n\x1b[35m═══════════════════════════════════════════════════\x1b[0m");
  console.log(`\x1b[1mKẾT QUẢ DỌN DẸP COMMENT RÁC:\x1b[0m`);
  console.log(`- Số tệp được tối ưu: \x1b[32m${totalChangedFiles}\x1b[0m / ${uniqueFiles.length}`);
  console.log(`- Tổng comment rác đã xóa: \x1b[33m${totalComments}\x1b[0m`);
  console.log(`- Dòng thừa đã rút gọn: \x1b[36m${totalLines}\x1b[0m dòng`);
  console.log(`- Dung lượng mã nguồn tiết kiệm: \x1b[32m${totalBytes}\x1b[0m bytes`);
  if (dryRun) {
    console.log(`\x1b[33m(Chế độ dry-run: Không có file nào trên đĩa bị thay đổi)\x1b[0m`);
  } else {
    console.log(`\x1b[32m✔ Đã cập nhật trực tiếp mã nguồn sạch sẽ!\x1b[0m`);
  }
  console.log("\x1b[35m═══════════════════════════════════════════════════\x1b[0m");
}

if (import.meta.main) {
  main().catch((err) => {
    console.error("Lỗi:", err);
    process.exit(1);
  });
}
