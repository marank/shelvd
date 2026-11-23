import { globalIgnores } from 'eslint/config'
import { defineConfigWithVueTs, vueTsConfigs } from '@vue/eslint-config-typescript'
import pluginVue from 'eslint-plugin-vue'
import pluginVueA11y from 'eslint-plugin-vuejs-accessibility'
import pluginVitest from '@vitest/eslint-plugin'
import pluginOxlint from 'eslint-plugin-oxlint'
import skipFormatting from 'eslint-config-prettier/flat'
import sonarjs from 'eslint-plugin-sonarjs'
import comments from '@eslint-community/eslint-plugin-eslint-comments'

// To allow more languages other than `ts` in `.vue` files, uncomment the following lines:
// import { configureVueProject } from '@vue/eslint-config-typescript'
// configureVueProject({ scriptLangs: ['ts', 'tsx'] })
// More info at https://github.com/vuejs/eslint-config-typescript/#advanced-setup

// Import boundaries. Pages (`views/`) sit on top: they may use anything, nothing shared uses them.
const pages = {
  group: ['@/features/*/views/*', '**/views/*'],
  message:
    'Only pages and routes may import a page (views/). Move the shared part into components/ or composables/.',
}
// src/lib and src/utils hold plain helpers: field registry, dates, labels, enums. No UI, no server
// state, no features.
const impure = {
  group: [
    '@/components/*',
    '@/features/*',
    '@/stores/*',
    '@/layouts/*',
    '@/router/*',
    '@/api/client',
    '**/*.vue',
  ],
  message:
    'src/lib and src/utils stay pure: no components, features, stores, router or API calls (types from @/api/types are fine).',
}

export default defineConfigWithVueTs(
  {
    name: 'app/files-to-lint',
    files: ['**/*.{vue,ts,mts,tsx}'],
  },

  globalIgnores(['**/dist/**', '**/dist-ssr/**', '**/coverage/**']),

  ...pluginVue.configs['flat/strongly-recommended'],
  ...pluginVueA11y.configs['flat/recommended'],
  vueTsConfigs.recommendedTypeChecked,

  {
    ...pluginVitest.configs.recommended,
    files: ['src/**/__tests__/*'],
  },

  ...pluginOxlint.buildFromOxlintConfigFile('.oxlintrc.json'),

  {
    // Vendored shadcn-vue components keep their upstream (single-word) names.
    name: 'app/vendored-ui',
    files: ['src/components/ui/**'],
    rules: { 'vue/multi-word-component-names': 'off' },
  },

  skipFormatting,

  // ── House rules: kept after eslint-plugin-oxlint, which would otherwise switch them off. ──

  // No silenced checks: every disable names its rules and says why; unused ones fail.
  { name: 'project/linter', linterOptions: { reportUnusedDisableDirectives: 'error' } },
  {
    name: 'project/no-silencing',
    files: ['src/**/*.{ts,tsx,vue}'],
    plugins: { '@eslint-community/eslint-comments': comments },
    rules: {
      '@eslint-community/eslint-comments/no-unlimited-disable': 'error',
      '@eslint-community/eslint-comments/require-description': 'error',
      '@typescript-eslint/ban-ts-comment': [
        'error',
        { 'ts-expect-error': 'allow-with-description' },
      ],
    },
  },
  // Tests that test: every test asserts, no `.only` or skipped test is committed.
  {
    name: 'project/tests',
    files: ['src/**/__tests__/**/*.{ts,tsx}', 'src/**/*.{test,spec}.{ts,tsx}'],
    plugins: { vitest: pluginVitest },
    rules: {
      'vitest/expect-expect': 'error',
      'vitest/no-focused-tests': 'error',
      'vitest/no-disabled-tests': 'error',
    },
  },
  {
    name: 'project/readability',
    files: ['src/**/*.{ts,tsx,vue}'],
    plugins: { sonarjs },
    rules: {
      complexity: ['error', 15],
      'sonarjs/cognitive-complexity': ['error', 15],
      'max-depth': ['error', 4],
      '@typescript-eslint/no-unnecessary-condition': 'error',
      '@typescript-eslint/no-floating-promises': 'error',
      '@typescript-eslint/no-misused-promises': 'error',
      '@typescript-eslint/switch-exhaustiveness-check': 'error',
      '@typescript-eslint/prefer-nullish-coalescing': 'error',
      'vue/no-v-html': 'error',
      // A label works when it wraps its control or names it with `for` (HTML allows either);
      // the shadcn `Label` is checked like a `<label>`.
      'vuejs-accessibility/label-has-for': [
        'error',
        {
          components: ['Label'],
          controlComponents: ['Checkbox', 'Input', 'NativeSelect', 'Switch', 'Textarea'],
          required: { some: ['nesting', 'id'] },
        },
      ],
      'vuejs-accessibility/form-control-has-label': ['error', { labelComponents: ['Label'] }],
      'vue/no-unused-properties': [
        'error',
        { groups: ['props', 'data', 'computed', 'methods', 'setup'] },
      ],
    },
  },
  {
    // Vendored shadcn-vue components hand their props on with useForwardProps/reactiveOmit,
    // which these rules don't count as use. Kept as upstream ships them, so `shadcn-vue add`
    // updates stay simple.
    name: 'project/vendored-ui',
    files: ['src/components/ui/**'],
    rules: { 'vue/no-unused-properties': 'off', 'vue/require-default-prop': 'off' },
  },
  // Later blocks replace the rule's options, so each lists every pattern that applies.
  {
    name: 'project/shared',
    files: [
      'src/components/**',
      'src/stores/**',
      'src/layouts/**',
      'src/features/*/components/**',
      'src/features/*/composables/**',
    ],
    rules: { 'no-restricted-imports': ['error', { patterns: [pages] }] },
  },
  {
    name: 'project/lib',
    files: ['src/lib/**', 'src/utils/**'],
    rules: { 'no-restricted-imports': ['error', { patterns: [pages, impure] }] },
  },
)
