import { describe, expect, it } from "bun:test";
import {
  cleanCodeLayout,
  stripCssComments,
  stripHtmlComments,
  stripJsComments,
  stripPythonComments,
  stripVueComments,
} from "./strip-comments";

describe("stripJsComments", () => {
  it("strips single line comments", () => {
    const input = `const a = 1; // remove this\nconst b = 2;`;
    const res = stripJsComments(input);
    expect(res.code).toBe(`const a = 1; \nconst b = 2;`);
    expect(res.count).toBe(1);
  });

  it("preserves compiler and linter directives", () => {
    const input = `// @ts-expect-error\nconst a: number = 'str';\n// eslint-disable-next-line\nconst b = 2;\n// biome-ignore lint: explanation\nconst c = 3;`;
    const res = stripJsComments(input);
    expect(res.code).toBe(input);
    expect(res.count).toBe(0);
  });

  it("preserves URLs and slashes inside string literals", () => {
    const input = `const url = "https://aave.com/api";\nconst single = 'http://test.org';`;
    const res = stripJsComments(input);
    expect(res.code).toBe(input);
    expect(res.count).toBe(0);
  });

  it("preserves template literals with markdown and slashes", () => {
    const input = "const doc = `# TRD Phase 5 // Markdown text\nLine 2 // note in string`;";
    const res = stripJsComments(input);
    expect(res.code).toBe(input);
    expect(res.count).toBe(0);
  });

  it("handles template literal interpolations ${...} and strips comments inside them", () => {
    const input = "const greeting = `Hello ${name /* strip this */}!`;";
    const res = stripJsComments(input);
    expect(res.code).toBe("const greeting = `Hello ${name }!`;");
    expect(res.count).toBe(1);
  });

  it("preserves regex literals", () => {
    const input = `const pattern = /\\/\\/test/g;\nconst slash = /abc/i;`;
    const res = stripJsComments(input);
    expect(res.code).toBe(input);
    expect(res.count).toBe(0);
  });
});

describe("stripVueComments", () => {
  it("strips HTML comments from template but preserves UI text containing //", () => {
    const input = `<template>
  <div>
    <!-- Hero Title Comment -->
    <span>VN30F1M // DESK PULSE PREVIEW</span>
    <p>01 // Tổng quan</p>
  </div>
</template>
<script setup lang="ts">
// Simulator state
const count = ref(0);
</script>
<style scoped>
/* Card style */
.card { color: red; }
</style>`;

    const res = stripVueComments(input);
    expect(res.code).not.toContain("Hero Title Comment");
    expect(res.code).not.toContain("Simulator state");
    expect(res.code).not.toContain("Card style");
    // Crucial check: UI text with // must be preserved!
    expect(res.code).toContain("VN30F1M // DESK PULSE PREVIEW");
    expect(res.code).toContain("01 // Tổng quan");
    expect(res.count).toBe(3);
  });
});

describe("stripCssComments", () => {
  it("strips CSS block comments", () => {
    const input = `/* Aave Colors */\n:root {\n  --color-violet: #998eff;\n}`;
    const res = stripCssComments(input);
    expect(res.code).toBe(`\n:root {\n  --color-violet: #998eff;\n}`);
    expect(res.count).toBe(1);
  });
});

describe("stripPythonComments", () => {
  it("strips Python comments while keeping shebang and noqa", () => {
    const input = `#!/usr/bin/env python3\n# A comment to strip\nimport os  # noqa: F401\nprint('hello')  # print note`;
    const res = stripPythonComments(input);
    expect(res.code).toContain("#!/usr/bin/env python3");
    expect(res.code).toContain("# noqa: F401");
    expect(res.code).not.toContain("A comment to strip");
    expect(res.code).not.toContain("print note");
    expect(res.count).toBe(2);
  });
});

describe("cleanCodeLayout", () => {
  it("removes trailing whitespace and collapses multiple blank lines", () => {
    const input = "const a = 1;   \n\n\n\nconst b = 2;\n\n";
    const res = cleanCodeLayout(input);
    expect(res.code).toBe("const a = 1;\n\nconst b = 2;\n");
  });
});
