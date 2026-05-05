import "../../chunks/index-server.js";
import { F as escape_html, a as stringify, n as attr_style } from "../../chunks/dev.js";
import { Node, mergeAttributes } from "@tiptap/core";
import "@tiptap/starter-kit";
Node.create({
	name: "placeholderQuote",
	group: "inline",
	inline: true,
	atom: true,
	addAttributes() {
		return { type: { default: "quote" } };
	},
	parseHTML() {
		return [{ tag: "span[data-placeholder-type=\"quote\"]" }];
	},
	renderHTML({ HTMLAttributes }) {
		return [
			"span",
			mergeAttributes(HTMLAttributes, {
				"data-placeholder-type": "quote",
				class: "placeholder-hook placeholder-hook--quote",
				contenteditable: "false",
				style: "display:inline-block;background:#1a3a2a;border:1px solid #2a6a4a;color:#5aaa7a;font-family:Menlo,Consolas,monospace;font-size:13px;padding:2px 8px;border-radius:3px;cursor:default"
			}),
			"JOURNALIST: Add quote"
		];
	}
});
Node.create({
	name: "placeholderContext",
	group: "inline",
	inline: true,
	atom: true,
	addAttributes() {
		return { type: { default: "context" } };
	},
	parseHTML() {
		return [{ tag: "span[data-placeholder-type=\"context\"]" }];
	},
	renderHTML({ HTMLAttributes }) {
		return [
			"span",
			mergeAttributes(HTMLAttributes, {
				"data-placeholder-type": "context",
				class: "placeholder-hook placeholder-hook--context",
				contenteditable: "false",
				style: "display:inline-block;background:#1a2a3a;border:1px solid #2a4a6a;color:#5a8aaa;font-family:Menlo,Consolas,monospace;font-size:13px;padding:2px 8px;border-radius:3px;cursor:default"
			}),
			"JOURNALIST: Add context"
		];
	}
});
Node.create({
	name: "placeholderCausal",
	group: "inline",
	inline: true,
	atom: true,
	addAttributes() {
		return { type: { default: "causal" } };
	},
	parseHTML() {
		return [{ tag: "span[data-placeholder-type=\"causal\"]" }];
	},
	renderHTML({ HTMLAttributes }) {
		return [
			"span",
			mergeAttributes(HTMLAttributes, {
				"data-placeholder-type": "causal",
				class: "placeholder-hook placeholder-hook--causal",
				contenteditable: "false",
				style: "display:inline-block;background:#2a2a1a;border:1px solid #5a4a2a;color:#aaaa5a;font-family:Menlo,Consolas,monospace;font-size:13px;padding:2px 8px;border-radius:3px;cursor:default"
			}),
			"JOURNALIST: Add causal reasoning"
		];
	}
});
//#endregion
//#region src/lib/components/BeatEditorSpike.svelte
function BeatEditorSpike($$renderer, $$props) {
	$$renderer.component(($$renderer) => {
		let jsonOutput = "";
		let spikeResult = "Not run yet";
		$$renderer.push(`<div style="padding: 24px; background: #0f0f0f; min-height: 100vh; color: #e0e0e0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;"><h1 style="font-size: 20px; font-weight: 600; margin-bottom: 16px;">TipTap + Svelte 5 Spike (D-10)</h1> <div style="background: #1a1a1a; border: 1px solid #2e2e2e; border-radius: 8px; padding: 16px; margin-bottom: 16px;"><p style="font-size: 13px; color: #999; margin-bottom: 8px;">Spike Result:</p> <pre${attr_style(`font-size: 13px; color: ${stringify(spikeResult.startsWith("SPIKE PASS") ? "#6acc8a" : "#cf4444")};`)}>${escape_html(spikeResult)}</pre></div> <div style="background: #1a1a1a; border: 1px solid #2e2e2e; border-radius: 8px; padding: 16px; margin-bottom: 16px;"><p style="font-size: 13px; color: #999; margin-bottom: 8px;">TipTap Editor (contains three placeholder nodes):</p> <div style="background: #0f0f0f; padding: 16px; min-height: 80px; border: 1px solid #2e2e2e; border-radius: 4px;"></div></div> <div style="background: #1a1a1a; border: 1px solid #2e2e2e; border-radius: 8px; padding: 16px;"><p style="font-size: 13px; color: #999; margin-bottom: 8px;">getJSON() output (must contain placeholderQuote, placeholderContext, placeholderCausal nodes):</p> <pre style="font-size: 12px; color: #777; overflow: auto; max-height: 300px;">${escape_html(jsonOutput)}</pre></div></div>`);
	});
}
//#endregion
//#region src/routes/+page.svelte
function _page($$renderer) {
	BeatEditorSpike($$renderer, {});
}
//#endregion
export { _page as default };
