

export const index = 2;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/pages/_page.svelte.js')).default;
export const imports = ["_app/immutable/nodes/2.Yg-zqMPh.js","_app/immutable/chunks/BcVz4hyW.js","_app/immutable/chunks/DEDqjojZ.js"];
export const stylesheets = [];
export const fonts = [];
