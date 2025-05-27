import { createHighlighter } from 'shiki';

let highlighter;

async function ensureHighlighter() {
  if (!highlighter) {
    highlighter = await createHighlighter({ themes: ['vitesse-dark'] });
  }
}

export async function createRenderers() {
  await ensureHighlighter();

  return {
    code({ value, language, theme }) {
      const html = highlighter.codeToHtml(value, { lang: language || 'txt', theme: theme || 'vitesse-dark' });
      // Remove outer <pre class="shiki"> wrapper — or keep if you want
      return {
        html,
      };
    },
  };
}
