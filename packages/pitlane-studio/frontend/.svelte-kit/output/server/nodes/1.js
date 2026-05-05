

export const index = 1;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/fallbacks/error.svelte.js')).default;
export const imports = ["_app/immutable/nodes/1.Cd0wXPR6.js","_app/immutable/chunks/BcVz4hyW.js","_app/immutable/chunks/BwYiMlAF.js","_app/immutable/chunks/DEDqjojZ.js"];
export const stylesheets = [];
export const fonts = [];
