import adapter from '@sveltejs/adapter-static';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  compilerOptions: {
    dev: process.env.NODE_ENV !== 'production',
    sourcemap: true
  },
  kit: {
    adapter: adapter()
  }
};

export default config;
