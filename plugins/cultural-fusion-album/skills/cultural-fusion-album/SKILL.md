---
name: cultural-fusion-album
description: >-
  Use when the user wants a concept album or set of songs about a culture, people, tradition
  or period of history, fused with modern genres or kept traditional ("make an album about
  Punjabi qawwali history with dubstep," "Hawaiian music fused with industrial metal,"
  "traditional Balinese gamelan versions"). Asks for the culture and the fusion, researches
  the history, musical forms and period-correct instruments, builds an album doc with Suno
  style prompts, original-language lyrics, translations and 500-character Suno notes, then
  creates the album in Suno through the bundled Suno MCP.
---

# Cultural Fusion Album

Turns "I want an album about <culture/history> fused with <genres>" into a researched,
historically honest concept album: a doc with per-track history, period-correct instruments,
Suno style prompts, original-language lyrics with translations, and 500-character Suno notes.
Then it creates the album in Suno.

## Requires: the Suno MCP

This plugin bundles the official Suno MCP server (`https://api.suno.com/mcp`, see
https://suno.com/mcp). Before step 4, check that Suno MCP tools are available:

- **Claude Code:** if the `suno` server shows as needing auth, run `/mcp` and sign in to Suno.
  If the plugin's server is missing, add it manually:
  `claude mcp add --transport http suno https://api.suno.com/mcp`.
- **claude.ai:** Customize -> Connectors -> + -> Add custom connector, name `Suno`,
  URL `https://api.suno.com/mcp`, then sign in to Suno.

Songs use the user's own Suno credits. No API key is needed.

## 1. Ask first (one AskUserQuestion call, up to 4 questions)

1. **Culture / history:** which people, region, tradition or era (e.g. Punjabi Sufi qawwali,
   Hawaiian, Balinese gamelan, Arabic maqam).
2. **Fusion:** which modern genres to blend in (e.g. dubstep, industrial harmonic metal, heavy
   pop, 90s R&B). Always offer **"Traditional only (no outside influence)"** and **"Both:
   fusion + traditional version of each track"**.
3. **Vocals:** original-language vocals / instrumental only / mixed.
4. **Shape:** number of tracks (default 10-12) and whether to use a narrator story arc
   (default: yes, a modern member of the culture telling their people's history, then their
   own story).

If the user is away, default to: fusion + traditional versions, original-language vocals,
11 tracks, narrator arc. Say which defaults you took.

## 2. Research (do it yourself, cite everything)

Search and open sources for:

- **Timeline:** 8-12 major events, figures and turning points (founding figures, poets,
  migrations, wars/partitions, diaspora, modern revival). Prefer Wikipedia, Britannica, major
  newspapers, academic and museum pages.
- **Musical forms:** the genre's structure (e.g. qawwali's build from slow alap to ecstatic
  climax), scales/modes (raga, maqam, pelog/slendro), rhythms (keherwa, maqsum, dhamaal).
- **Instruments with dates:** when each instrument actually appeared in that culture. This is
  the most important accuracy check. Example: the harmonium only reached India in the
  mid-19th century; the modern tabla dates to the 18th century. No track may use an instrument
  that did not exist in its era.
- **Public-domain texts:** short traditional lines or verses by pre-1929 poets that can serve
  as refrains (e.g. Khusrau, Baba Farid, Bulleh Shah). Never use copyrighted lyrics, modern
  melodies or artist names.
- **Language:** what each era/story was sung in.

Label legends as legends. Do not state dates or facts you did not find in a source.

## 3. Build the album doc

Make it a Docs artifact where available (otherwise a markdown file). Create the skeleton
first, then fill one track per write. Sections:

- **The story and how to use it:** narrator concept, shared base sound, Suno settings.
- **One section per track:**
  - **History:** 2-4 sentences with linked sources.
  - **Instruments:** what is used and why it fits the era, with sources.
  - **Style:** Suno style prompt, <= 1000 characters, starting with "Sung in <language>."
    For fusion: the traditional root leads, modern genres blend underneath ("low in the mix",
    "never louder than the voice"). For eras before an instrument existed, write "Period
    instruments only: ...; no <anachronistic instrument>".
  - **Traditional version style** (when asked): the same track with only period instruments
    and no modern genres.
  - **Exclude styles:** anachronistic instruments plus e.g. "heavy distortion, guitar solo,
    screaming, EDM, brostep, English lyrics".
  - **Lyrics:** in the original language, romanized, with `[Section: arrangement notes]`
    tags. Original lines plus public-domain traditional refrains.
  - **Translation:** English, section by section.
  - **Suno notes:** <= 500 characters (count with code, not by eye). History + chorus meaning
    + an "Instruments:" line + one full source URL.
- **Sources:** all pages used.

Flag any non-traditional lines you wrote in a non-English language for native-speaker review.

### Suno prompt rules

- No artist, band or franchise names (Suno blocks them). Describe the sound instead.
- Put the most important instruments first; Suno weighs early words most.
- Dubstep: write "140 BPM half-time" or a plain slow BPM; drop snare-roll build tags if tracks
  come out too fast.
- Keep the cultural voice leading: "qawwali voice leads", "guitars low in the mix".

## 4. Create in Suno

Confirm before spending credits: say how many generations (each Create = 2 clips) and get a
clear yes.

### Primary: the Suno MCP

Use the Suno MCP tools to check credits, then create each track with its lyrics, style and
title. Read the tool schemas; pass the exclude list and vocal gender where the tools accept
them. After creating, list the new songs and report their links.

The MCP does not document workspaces or captions. If those tools are missing, finish them with
the browser fallback below (only steps 2 and 4).

### Fallback: Claude in Chrome on suno.com/create

Use when the MCP is unavailable, or for workspaces and captions. Load the chrome-browser skill
first. Do not use unofficial cookie-based Python libraries (SunoAI, suno-api): they rely on
copied session cookies, are unmaintained, and break Suno's terms.

1. Open `https://suno.com/create`, switch to **Advanced**, expand **More Options**, set
   **Vocal Gender**.
2. Click **Save to...** and create a workspace named after the album; select it.
3. Define a fill helper with `javascript_tool`, call it once per track, then click the
   **Create song** button:

```js
window.__fill = async ({lyrics, style, exclude, title}) => {
  const setVal = (el, v) => { const p = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype; Object.getOwnPropertyDescriptor(p, 'value').set.call(el, v); el.dispatchEvent(new Event('input', {bubbles: true})); };
  const clr = document.querySelector('button[aria-label="Clear lyrics"]'); if (clr && !clr.disabled) clr.click();
  await new Promise(r => setTimeout(r, 500));
  const ed = document.querySelector('[aria-label="Lyrics editor"]'); ed.focus();
  const dt = new DataTransfer(); dt.setData('text/plain', lyrics);
  ed.dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true}));
  setVal(document.querySelector('textarea[aria-label="Styles"]'), style);
  setVal(document.querySelector('input[placeholder="Exclude styles"]'), exclude);
  setVal(document.querySelector('input[placeholder="Song Title (Optional)"]'), title);
  await new Promise(r => setTimeout(r, 800));
  return ed.innerText.slice(0, 60);
};
```

The lyrics box is a contenteditable div: form_input fails on it; the synthetic paste works.

4. **Notes (captions):** collect song IDs from `a[href^="/song/"]` in the workspace list
   (scroll the list container to load all). Open one song page, then run this loop; it uses
   Next.js client navigation so the helper survives between songs:

```js
window.__runCaps = async (jobs) => { // jobs = [[songId, caption], ...]
  const wait = ms => new Promise(r => setTimeout(r, ms)); const out = [];
  for (const [id, cap] of jobs) {
    window.next.router.push('/song/' + id);
    for (let i = 0; i < 40; i++) { await wait(300); if (location.pathname.includes(id)) break; }
    await wait(2000);
    const pill = [...document.querySelectorAll('button, div, span, p')].find(e => e.children.length === 0 && /^Add a caption/.test(e.innerText.trim()));
    if (!pill) { out.push([id, 'no pill']); continue; }
    pill.click();
    let ta; for (let i = 0; i < 25 && !ta; i++) { ta = document.querySelector('[role=dialog] textarea[placeholder="Add a caption"]'); if (!ta) await wait(200); }
    const dlg = ta && ta.closest('[role=dialog]');
    if (!ta || !dlg.innerText.includes('Edit song details')) { out.push([id, 'wrong dialog']); continue; }
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set.call(ta, cap); ta.dispatchEvent(new Event('input', {bubbles: true}));
    await wait(300); [...dlg.querySelectorAll('button')].find(b => b.innerText.trim() === 'Save').click();
    await wait(1500); out.push([document.title, 'saved']);
  }
  return out; };
```

Run it in batches of 5-7 songs per call. Spot-check one song after a reload.

**Never publish.** The song page also has a Publish dialog; if one opens, click Cancel. Close
any tabs you opened.

## 5. Finish

Tell the user: the doc link, the Suno workspace name, how many clips were made, which lines
need native-speaker review, and offer the traditional-only versions if not made yet.
