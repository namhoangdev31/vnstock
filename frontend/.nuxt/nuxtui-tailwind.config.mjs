
      import { defaultExtractor as createDefaultExtractor } from "tailwindcss/lib/lib/defaultExtractor.js";
<<<<<<< HEAD
      import { customSafelistExtractor, generateSafelist } from "/home/lkct-lee-park/var/vnstock/node_modules/@nuxt/ui/dist/runtime/utils/colors";
=======
      import { customSafelistExtractor, generateSafelist } from "/Volumes/developer101/code/vnstock/node_modules/.pnpm/@nuxt+ui@2.22.3_@nuxt+schema@3.21.11_axios@1.20.0_debug@4.4.3_supports-color@10.2.2__su_55443b908975645970aac7c89ceba0c4/node_modules/@nuxt/ui/dist/runtime/utils/colors";
>>>>>>> 3083472 (refactor: update dependencies and configure pnpm workspace for monorepo structure)
      import formsPlugin from "@tailwindcss/forms";
      import aspectRatio from "@tailwindcss/aspect-ratio";
      import typography from "@tailwindcss/typography";
      import containerQueries from "@tailwindcss/container-queries";
      import headlessUi from "@headlessui/tailwindcss";

      const defaultExtractor = createDefaultExtractor({ tailwindConfig: { separator: ':' } });

      export default {
        plugins: [
          formsPlugin({ strategy: 'class' }),
          aspectRatio,
          typography,
          containerQueries,
          headlessUi
        ],
        content: {
          files: [
<<<<<<< HEAD
            "/home/lkct-lee-park/var/vnstock/node_modules/@nuxt/ui/dist/runtime/components/**/*.{vue,mjs,ts}",
            "/home/lkct-lee-park/var/vnstock/node_modules/@nuxt/ui/dist/runtime/ui.config/**/*.{mjs,js,ts}"
=======
            "/Volumes/developer101/code/vnstock/node_modules/.pnpm/@nuxt+ui@2.22.3_@nuxt+schema@3.21.11_axios@1.20.0_debug@4.4.3_supports-color@10.2.2__su_55443b908975645970aac7c89ceba0c4/node_modules/@nuxt/ui/dist/runtime/components/**/*.{vue,mjs,ts}",
            "/Volumes/developer101/code/vnstock/node_modules/.pnpm/@nuxt+ui@2.22.3_@nuxt+schema@3.21.11_axios@1.20.0_debug@4.4.3_supports-color@10.2.2__su_55443b908975645970aac7c89ceba0c4/node_modules/@nuxt/ui/dist/runtime/ui.config/**/*.{mjs,js,ts}"
>>>>>>> 3083472 (refactor: update dependencies and configure pnpm workspace for monorepo structure)
          ],
          transform: {
            vue: (content) => {
              return content.replaceAll(/(?:\r\n|\r|\n)/g, ' ')
            }
          },
          extract: {
            vue: (content) => {
              return [
                ...defaultExtractor(content),
                ...customSafelistExtractor("U", content, ["red","orange","amber","yellow","lime","green","emerald","teal","cyan","sky","blue","indigo","violet","purple","fuchsia","pink","rose","aave","surface","tv","quant","ticker","market","primary"], ["primary"])
              ]
            }
          }
        },
        safelist: generateSafelist(["primary"], ["red","orange","amber","yellow","lime","green","emerald","teal","cyan","sky","blue","indigo","violet","purple","fuchsia","pink","rose","aave","surface","tv","quant","ticker","market","primary"]),
      }
    