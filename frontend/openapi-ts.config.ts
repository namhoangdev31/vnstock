import { defineConfig } from "@hey-api/openapi-ts";

export default defineConfig({
	input: "./openapi.json",
	output: "./client",

	plugins: [
		{ name: "@hey-api/client-axios", throwOnError: true },
		{ name: "@hey-api/typescript", case: "preserve" },
		{
			name: "@hey-api/sdk",
			operations: {
				strategy: "byTags",
				methods: "static",
				containerName: "{{name}}Service",
				methodName: (name: string): string => name.replace(/^[^-]*-/, ""),
			},
		},
	],
});
