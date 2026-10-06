import { defineConfig } from "tsup";

export default defineConfig({
	entry: {
		index: "src/index.ts",
		"api/index": "src/api/index.ts",
		"websocket/index": "src/websocket/index.ts",
	},
	format: ["cjs", "esm"],
	dts: true,
	clean: true,
	sourcemap: true,
	minify: false,
	splitting: false,
});
