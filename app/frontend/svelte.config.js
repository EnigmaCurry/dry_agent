import preprocess from 'svelte-preprocess';
import adapter from '@sveltejs/adapter-static';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  preprocess: preprocess({
    scss: {
      // optionally let `@use "bulma"` resolve to node_modules
      includePaths: ['src', 'node_modules']
    }
  }),
  compilerOptions: {
    dev: process.env.NODE_ENV !== 'production',
    sourcemap: true
  },
  kit: {
    adapter: adapter()
  }
};

export default config;
