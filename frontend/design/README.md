## Figma import guide (best practices)

This folder contains:

- `component_inventory.csv`: a tabular component inventory with variants, states, and interactions
- `tokens.json`: Tokens Studio design tokens mapped from the live MUI theme

### 1) Import tokens.json into Figma (Tokens Studio)

Prerequisites: Install the Figma plugin “Tokens Studio for Figma”.

Steps:
1. Open your Figma file (design system or working file).
2. Plugins → Tokens Studio.
3. In Tokens Studio, click the kebab menu (⋯) → Import/Export → Import.
4. Choose “JSON” and select `frontend/design/tokens.json`.
5. Import as a new set. Confirm the groups (color, radius, elevation, space, typography).
6. Click “Apply to document” to sync tokens to Figma styles.

Best practices:
- Keep tokens in a separate Figma page named “Foundations / Tokens”.
- Use Tokens Studio “Sync styles” to generate Figma color/text styles.
- If you create dark mode, add a second tokens set (e.g., `color.dark.*`) and use Tokens Studio themes.

### 2) Import component_inventory.csv into Figma

Option A: FigJam or Google Sheets → Figma
1. Open `component_inventory.csv` in Google Sheets (File → Import → Upload → CSV).
2. Clean columns if needed.
3. In Figma, create a Components page.
4. Use a table plugin (e.g., “Convert CSV to Table”, “Google Sheets Sync”) to bring the table into Figma.

Option B: CSV-to-table Figma plugin (direct)
1. In your Figma file, Plugins → search “CSV to Table” or “Table Generator”.
2. Paste the CSV content from `component_inventory.csv`.
3. Generate a table frame. Place it in a “Inventory / Matrix” section.

Best practices:
- Keep the inventory table as a living source of truth next to components.
- Link code refs (e.g., `src/App.js`) in notes for quick lookup.

### 3) Build component variants

For each row in the inventory:
1. Create a component (e.g., “Thread Item”).
2. Add variant properties (e.g., `selected=true/false`, `editing=true/false`).
3. Add interaction notes (hover, focus, pressed, disabled) as a variant or via prototype interactions + annotations.
4. Use tokens from Tokens Studio for colors, radius, elevation, spacing, typography.

Tips:
- Use Figma’s properties for Boolean/Variant/Instance swap.
- Keep names consistent with code: `App / Drawer / ThreadItem`.
- Document keyboard/focus behavior in description for dev parity.

### 4) Use the architecture diagram

We included a Mermaid diagram in the brief. You can recreate it in FigJam or export as an SVG and paste into a “Architecture” page for context.

### 5) Sync with development

- If design tokens change, update Tokens Studio and re-sync styles.
- If component structure changes, update `component_inventory.csv` and re-generate the table in Figma.

### Troubleshooting

- Tokens not applying: ensure Tokens Studio “Apply to document” is used, and styles are generated.
- CSV import misaligned: ensure commas are quoted in the CSV if any text includes commas.
- Missing fonts: set Figma file fonts to match tokens `fontFamily` or define replacements.


