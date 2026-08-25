# Icons — LLM Share Buttons

## The position

**Wordmark-only is the safe default, and it is what this skill ships.**

Each button shows the assistant's name set in the client's own typography and brand palette. No third-party logo is reproduced. That is the recommended shipping state and it is what the demo file renders by default.

The reasoning is not aesthetic:

- **Anthropic requires prior written approval** before its marks are used. A compatibility-indicator argument is not a substitute for that approval.
- **Google prohibits composite logo lockups** and restricts uses that imply endorsement. Note also that the AI Mode button targets Google Search's AI Mode surface — it is not Gemini, and must not be badged with the Gemini logo.
- **OpenAI's brand policy is the most restrictive of the set** and its mark is the most frequently targeted for takedown.
- Reproducing five protected marks across every client build multiplies one approval problem into five, on every site the skill touches.

A wordmark button is understood instantly, carries no trademark exposure, needs no external approval, and cannot break when a CDN pulls a file.

## This directory ships exactly one glyph

**`generic-ai.svg`** — a neutral, original, monochrome chat-and-sparkle mark. 24x24 viewBox, `currentColor`, no text, no resemblance to any provider's logo. It exists so the widget renders correctly out of the box in icon mode without shipping anyone's trademark.

No real company logo is included in this repository, and none should ever be committed to it. Client logo files live in the client's own repository.

## If the client wants real logos

They must be downloaded from each provider's official brand resources and **self-hosted on the client's own domain or CDN**. Do not link to a third-party SVG mirror or icon CDN. Those get taken down at brand owners' request — the OpenAI mark has already been pulled from one widely used third-party SVG CDN, which turns every button on every page into a broken image with no warning.

Official sources:

| Platform | Where to get the asset |
| --- | --- |
| ChatGPT (OpenAI) | https://openai.com/brand |
| Claude (Anthropic) | https://www.anthropic.com/legal/trademark-guidelines — read first; prior written approval is required |
| Grok (xAI) | https://x.ai/legal/brand-guidelines |
| Google AI Mode | https://about.google/brand-resource-center/brand-terms/ |
| Perplexity | Perplexity's brand system — request access via Perplexity's brand contact |

## Path convention and filenames

Self-host at:

```
/icons/llm-share/{platform}.svg
```

where `{platform}` is the platform `id` from `_shared/platform-endpoints.json`. Expected filenames:

```
/icons/llm-share/chatgpt.svg
/icons/llm-share/claude.svg
/icons/llm-share/perplexity.svg
/icons/llm-share/grok.svg
/icons/llm-share/googleai.svg
/icons/llm-share/generic-ai.svg   <- the neutral fallback, always present
```

The base path is configurable via the `{{ICON_BASE_PATH}}` placeholder; `/icons/llm-share` is the default.

## Implementation rules

1. **Ship wordmark-only until brand and legal sign-off is in writing.** Icon mode is opt-in, per client, after approval.
2. **Fall back to `generic-ai.svg`** for any platform whose logo has not been approved or supplied. Never leave a broken `<img>`.
3. **Inline the SVG in the component** rather than referencing it with `<img src>`. This removes the broken-image failure mode entirely and the icon ships inside the bundle. It also lets the glyph inherit `currentColor` so it flips with the button's hover state.
4. **Do not recolour, crop, rotate, add effects to, or lock up a provider's logo** with the client's own mark. That breaks every one of the brand guidelines linked above.
5. **The icon is decorative** when a text wordmark is present — mark it `aria-hidden="true" focusable="false"` and let the visible label carry the accessible name.
6. **Buttons take the client's brand palette, not the providers' brand colours.** Platform identity is carried by the wordmark. This keeps every client build visually distinct and avoids reproducing five brand colour systems on one page.
