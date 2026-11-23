import { fileURLToPath } from 'node:url'
import { mergeConfig, defineConfig, configDefaults } from 'vitest/config'
import viteConfig from './vite.config.ts'

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: 'jsdom',
      exclude: [...configDefaults.exclude, 'e2e/**'],
      root: fileURLToPath(new URL('./', import.meta.url)),
      setupFiles: ['src/test/setup.ts'],
      // The persistent transform cache misses files added later to import.meta.glob
      // (feature locales, route files) and then tests fail for no visible reason.
      fsModuleCache: false,
      coverage: {
        provider: 'v8',
        include: ['src/**'],
        exclude: [
          'src/components/ui/**',
          'src/api/schema.d.ts',
          'src/main.ts',
          'src/test/**',
          '**/*.d.ts',
          '**/__tests__/**',
        ],
        thresholds: { lines: 90, functions: 90, branches: 90, statements: 90 },
      },
    },
  }),
)
