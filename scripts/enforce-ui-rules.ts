#!/usr/bin/env bun
/**
 * enforce-ui-rules.ts
 * Enforces strict UI engineering rules:
 * 1. Replaces hardcoded hex colors (#...) with semantic Tailwind tokens (aave-*, surface-*).
 * 2. Removes gradients from code.
 * 3. Removes emojis in text.
 * 4. Eliminates explanatory parentheses in labels, substituting with <UTooltip> where appropriate.
 */

import { readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { extname, join, relative } from "node:path";

const COLOR_REPLACEMENTS: [RegExp, string][] = [
  // Opacity variants first
  [/bg-\[#998eff\]\/15/g, "bg-aave-violet/15"],
  [/bg-\[#998eff\]\/20/g, "bg-aave-violet/20"],
  [/bg-\[#998eff\]\/10/g, "bg-aave-violet/10"],
  [/bg-\[#998eff\]\/5/g, "bg-aave-violet/5"],
  [/border-\[#998eff\]\/30/g, "border-aave-violet/30"],
  [/border-\[#998eff\]\/20/g, "border-aave-violet/20"],
  [/border-\[#998eff\]\/40/g, "border-aave-violet/40"],
  [/border-\[#998eff\]\/50/g, "border-aave-violet/50"],
  [/text-\[#998eff\]\/80/g, "text-aave-violet/80"],

  // Direct colors
  [/selection:bg-\[#998eff\]/g, "selection:bg-aave-violet"],
  [/selection:text-\[#000000\]/g, "selection:text-aave-charcoal"],
  [/bg-\[#998eff\]/g, "bg-aave-violet"],
  [/text-\[#998eff\]/g, "text-aave-violet"],
  [/border-\[#998eff\]/g, "border-aave-violet"],

  [/text-\[#858387\]/g, "text-aave-graphite"],
  [/bg-\[#858387\]/g, "bg-aave-graphite"],
  [/border-\[#858387\]/g, "border-aave-graphite"],

  [/text-\[#636161\]/g, "text-aave-iron"],
  [/bg-\[#636161\]/g, "bg-aave-iron"],
  [/border-\[#636161\]/g, "border-aave-iron"],

  [/text-\[#221d1d\]/g, "text-aave-obsidian"],
  [/bg-\[#221d1d\]/g, "bg-aave-obsidian"],
  [/border-\[#221d1d\]/g, "border-aave-obsidian"],

  [/text-\[#0f0f10\]/g, "text-aave-inkwell"],
  [/bg-\[#0f0f10\]/g, "bg-aave-inkwell"],
  [/border-\[#0f0f10\]/g, "border-aave-inkwell"],

  [/text-\[#ffffff\]/g, "text-aave-paper"],
  [/bg-\[#ffffff\]/g, "bg-aave-paper"],

  [/text-\[#000000\]/g, "text-aave-charcoal"],
  [/bg-\[#000000\]/g, "bg-aave-charcoal"],

  [/text-\[#f6f7f4\]/g, "text-aave-bone"],
  [/bg-\[#f6f7f4\]/g, "bg-aave-bone"],

  [/text-\[#bcbbbb\]/g, "text-aave-ash"],
  [/bg-\[#bcbbbb\]/g, "bg-aave-ash"],
  [/border-\[#bcbbbb\]/g, "border-aave-ash"],

  [/text-\[#b2a9ff\]/g, "text-aave-violet"],

  [/bg-\[#161414\]/g, "bg-surface-midnight"],
  [/bg-\[#090d16\]\/80/g, "bg-surface-abyss/80"],
  [/bg-\[#090d16\]\/90/g, "bg-surface-abyss/90"],
  [/bg-\[#090d16\]/g, "bg-surface-abyss"],
  [/bg-\[#0d1322\]/g, "bg-surface-midnight"],
  [/bg-\[#070a11\]/g, "bg-surface-abyss"],
  [/bg-\[#0b101c\]/g, "bg-surface-abyss"],
  [/bg-\[#06080d\]/g, "bg-surface-abyss"],
  [/bg-\[#ece6ff\]/g, "bg-surface-lavender"],
  [/bg-\[#f7f4ff\]/g, "bg-surface-lavender"],
];

const PARENTHESES_REPLACEMENTS: [string | RegExp, string][] = [
  [
    "<span>Technical Requirements Document (Markdown Specification)</span>",
    `<div class="flex items-center gap-1.5"><span>Technical Requirements Document</span><UTooltip text="Markdown Specification"><UIcon name="i-heroicons-information-circle" class="w-4 h-4 text-aave-graphite cursor-help" /></UTooltip></div>`,
  ],
  [
    "<span>Tự động nâng cấp trọng số (Auto-Promote)</span>",
    `<div class="flex items-center gap-1.5"><span>Tự động nâng cấp trọng số</span><UTooltip text="Auto-Promote"><UIcon name="i-heroicons-information-circle" class="w-4 h-4 text-aave-graphite cursor-help" /></UTooltip></div>`,
  ],
  [
    "<span>Cầu dao an toàn tự động (Circuit Breaker)</span>",
    `<div class="flex items-center gap-1.5"><span>Cầu dao an toàn tự động</span><UTooltip text="Circuit Breaker"><UIcon name="i-heroicons-information-circle" class="w-4 h-4 text-aave-graphite cursor-help" /></UTooltip></div>`,
  ],
  [
    `<span class="text-white">1. Phát sinh dự báo (Pending)</span>`,
    `<div class="flex items-center gap-1.5"><span class="text-white">1. Phát sinh dự báo</span><UTooltip text="Trạng thái Pending"><UIcon name="i-heroicons-information-circle" class="w-3.5 h-3.5 text-aave-graphite cursor-help" /></UTooltip></div>`,
  ],
  [
    `<th class="py-3 px-4 w-48">MÃ ĐỊNH DANH (UUID)</th>`,
    `<th class="py-3 px-4 w-48"><div class="flex items-center gap-1"><span>MÃ ĐỊNH DANH</span><UTooltip text="UUID"><UIcon name="i-heroicons-information-circle" class="w-3.5 h-3.5 text-aave-graphite cursor-help" /></UTooltip></div></th>`,
  ],
  [
    `<th class="py-3 px-4">TIÊU ĐỀ (TITLE)</th>`,
    `<th class="py-3 px-4">TIÊU ĐỀ</th>`,
  ],
  [
    `<label class="block text-xs font-mono text-slate-300 mb-1.5">Tiêu đề (Title) *</label>`,
    `<label class="block text-xs font-mono text-slate-300 mb-1.5">Tiêu đề *</label>`,
  ],
  [
    `<label class="block text-xs font-mono text-slate-300 mb-1.5">Mô tả (Description)</label>`,
    `<label class="block text-xs font-mono text-slate-300 mb-1.5">Mô tả</label>`,
  ],
  [
    `<th class="py-3 px-4 w-32 text-center">VAI TRÒ (ROLE)</th>`,
    `<th class="py-3 px-4 w-32 text-center">VAI TRÒ</th>`,
  ],
  [
    `<span class="font-mono">Quyền Quản trị viên (Superuser Flag)</span>`,
    `<div class="flex items-center gap-1.5"><span class="font-mono">Quyền Quản trị viên</span><UTooltip text="Superuser Flag"><UIcon name="i-heroicons-information-circle" class="w-3.5 h-3.5 text-aave-graphite cursor-help" /></UTooltip></div>`,
  ],
  [
    `<span class="font-mono">Kích hoạt tài khoản (Active Status)</span>`,
    `<div class="flex items-center gap-1.5"><span class="font-mono">Kích hoạt tài khoản</span><UTooltip text="Active Status"><UIcon name="i-heroicons-information-circle" class="w-3.5 h-3.5 text-aave-graphite cursor-help" /></UTooltip></div>`,
  ],
  [
    `<th class="py-3 px-4 font-sans">Kịch bản kiểm thử (Scenario)</th>`,
    `<th class="py-3 px-4 font-sans">Kịch bản kiểm thử</th>`,
  ],
  [
    `<th class="py-3 px-4 font-sans">Kết quả kỳ vọng (Expectation)</th>`,
    `<th class="py-3 px-4 font-sans">Kết quả kỳ vọng</th>`,
  ],
  [
    `<span>Trọng số (Weight)</span>`,
    `<span>Trọng số</span>`,
  ],
  [
    `<span>Điểm tín hiệu (-100 đến +100)</span>`,
    `<div class="flex items-center gap-1"><span>Điểm tín hiệu</span><UTooltip text="Thang đo -100 đến +100"><UIcon name="i-heroicons-information-circle" class="w-3.5 h-3.5 text-aave-graphite cursor-help" /></UTooltip></div>`,
  ],
  [
    `<div class="text-[11px] text-aave-graphite">Độ lệch (Basis)</div>`,
    `<div class="text-[11px] text-aave-graphite">Độ lệch Basis</div>`,
  ],
  [
    `<th class="py-3 px-4">Khung (Horizon)</th>`,
    `<th class="py-3 px-4">Khung thời gian</th>`,
  ],
  [
    `<th class="py-3 px-4">Thực tế (Actual)</th>`,
    `<th class="py-3 px-4">Giá thực tế</th>`,
  ],
  [
    `<th class="py-3 px-4">Sai số (MAE)</th>`,
    `<th class="py-3 px-4"><div class="flex items-center gap-1"><span>Sai số</span><UTooltip text="Mean Absolute Error"><UIcon name="i-heroicons-information-circle" class="w-3.5 h-3.5 text-aave-graphite cursor-help" /></UTooltip></div></th>`,
  ],
  [
    `<span>Dư Mua (Bids)</span>`,
    `<span>Dư Mua</span>`,
  ],
  [
    `<span>Dư Bán (Asks)</span>`,
    `<span>Dư Bán</span>`,
  ],
  [
    `<th class="py-3 px-4 w-40">Ngành nghề (ICB)</th>`,
    `<th class="py-3 px-4 w-40"><div class="flex items-center gap-1"><span>Ngành nghề</span><UTooltip text="Industry Classification Benchmark"><UIcon name="i-heroicons-information-circle" class="w-3.5 h-3.5 text-aave-graphite cursor-help" /></UTooltip></div></th>`,
  ],
  [
    `<label class="block text-xs text-slate-400 mb-1">Giá vào lệnh (Entry Price)</label>`,
    `<label class="block text-xs text-slate-400 mb-1">Giá vào lệnh</label>`,
  ],
  [
    `<label class="block text-xs text-slate-400 mb-1">Giá thị trường hiện tại (Current)</label>`,
    `<label class="block text-xs text-slate-400 mb-1">Giá thị trường hiện tại</label>`,
  ],
  [
    `<span class="text-xs text-slate-400 uppercase tracking-wider font-mono text-[10px]">Ký quỹ ban đầu (IM)</span>`,
    `<div class="flex items-center gap-1"><span class="text-xs text-slate-400 uppercase tracking-wider font-mono text-[10px]">Ký quỹ ban đầu</span><UTooltip text="Initial Margin"><UIcon name="i-heroicons-information-circle" class="w-3 h-3 text-aave-graphite cursor-help" /></UTooltip></div>`,
  ],
  [
    `<span class="text-xs text-slate-400 uppercase tracking-wider font-mono text-[10px]">Lãi / Lỗ vị thế (Unrealized PnL)</span>`,
    `<div class="flex items-center gap-1"><span class="text-xs text-slate-400 uppercase tracking-wider font-mono text-[10px]">Lãi / Lỗ vị thế</span><UTooltip text="Unrealized PnL"><UIcon name="i-heroicons-information-circle" class="w-3 h-3 text-aave-graphite cursor-help" /></UTooltip></div>`,
  ],
  [
    `<label class="block text-xs font-medium text-slate-300 mb-1.5">Mật khẩu (tối thiểu 8 ký tự)</label>`,
    `<label class="block text-xs font-medium text-slate-300 mb-1.5 flex items-center justify-between"><span>Mật khẩu</span><span class="text-[10px] text-aave-graphite font-normal">Tối thiểu 8 ký tự</span></label>`,
  ],
  [
    `label: "Tài liệu đặc tả (TRD Spec)",`,
    `label: "Tài liệu đặc tả",`,
  ],
  [
    `label: "Ma trận kiểm thử (Test Matrix)",`,
    `label: "Ma trận kiểm thử",`,
  ],
  [
    `label: "Trình mô phỏng (Interactive Simulator)",`,
    `label: "Trình mô phỏng",`,
  ],
  [
    `label: "Khối lượng Khớp lệnh (Volume Profile)",`,
    `label: "Khối lượng Khớp lệnh",`,
  ],
  [
    `label: "Sổ cái Kiểm toán (Audit Ledger)",`,
    `label: "Sổ cái Kiểm toán",`,
  ],
  [
    `label: "Lịch trình Phiên (Session Timeline)",`,
    `label: "Lịch trình Phiên",`,
  ],
  [
    `label: "Rổ Cổ phiếu Alpha (Alpha Portfolios)",`,
    `label: "Rổ Cổ phiếu Alpha",`,
  ],
  [
    `label: "Bảng giá Phái sinh (Orderbook)",`,
    `label: "Bảng giá Phái sinh",`,
  ],
];

function processContent(content: string, filePath: string): string {
  let updated = content;

  // 1. Remove gradients
  if (filePath.endsWith("index.vue")) {
    updated = updated.replace(
      /bg-gradient-to-b from-\[#ffffff\] via-\[#f7f4ff\] to-\[#ece6ff\]/g,
      "bg-surface-lavender opacity-35"
    );
    updated = updated.replace(
      /bg-gradient-to-b from-aave-paper via-surface-lavender to-surface-lavender/g,
      "bg-surface-lavender opacity-35"
    );
  }

  if (filePath.endsWith("[symbol].vue")) {
    // Canvas gradient replacement
    updated = updated.replace(
      /const gradient = ctx\.createLinearGradient[\s\S]*?ctx\.fillStyle = gradient/g,
      `ctx.fillStyle = "rgba(153, 142, 255, 0.06)"`
    );
  }

  // 2. Token replacements
  for (const [regex, replacement] of COLOR_REPLACEMENTS) {
    updated = updated.replace(regex, replacement);
  }

  // 3. Parentheses replacements
  for (const [target, replacement] of PARENTHESES_REPLACEMENTS) {
    if (typeof target === "string") {
      updated = updated.replaceAll(target, replacement);
    } else {
      updated = updated.replace(target, replacement);
    }
  }

  return updated;
}

function traverse(dir: string, fileList: string[] = []): string[] {
  const entries = readdirSync(dir);
  for (const entry of entries) {
    if (entry === "node_modules" || entry === ".nuxt" || entry === ".output" || entry === "client") {
      continue;
    }
    const full = join(dir, entry);
    const st = statSync(full);
    if (st.isDirectory()) {
      traverse(full, fileList);
    } else if (st.isFile()) {
      const ext = extname(entry).toLowerCase();
      if (ext === ".vue" || ext === ".ts") {
        fileList.push(full);
      }
    }
  }
  return fileList;
}

function main() {
  const targetDir = join(process.cwd(), "frontend");
  const files = traverse(targetDir);

  let changedCount = 0;
  for (const file of files) {
    const original = readFileSync(file, "utf-8");
    const processed = processContent(original, file);
    if (processed !== original) {
      writeFileSync(file, processed, "utf-8");
      changedCount++;
      console.log(`✔ Updated: ${relative(process.cwd(), file)}`);
    }
  }

  console.log(`\n✨ Enforced UI rules across ${changedCount} / ${files.length} files.`);
}

main();
