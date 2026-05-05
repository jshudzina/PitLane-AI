import adapter from '@sveltejs/adapter-static'

/** @type {import('@sveltejs/kit').Config} */
const config = {
  kit: {
    adapter: adapter({
      pages: '../src/pitlane_studio/static',
      assets: '../src/pitlane_studio/static',
      fallback: '200.html',
      precompress: false,
      strict: false,
    }),
    prerender: {
      handleHttpError: 'ignore',
    },
  },
}

export default config
