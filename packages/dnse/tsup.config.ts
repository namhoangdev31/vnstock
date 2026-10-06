import { defineConfig } from "tsup";

export default defineConfig({
	entry: ["src/index.ts", "src/api/index.ts", "src/websocket/index.ts"],
	format: ["cjs", "esm"],
	dts: false,
	clean: true,
	sourcemap: true,
	minify: false,
	splitting: false,
});
