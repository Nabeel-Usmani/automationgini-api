"""
10 layouts - bold/contemporary, real stylistic range spanning dark and
light aesthetics (Neon Tech / Dark Cinematic dark-first, Editorial Luxury /
Minimalist Gallery light-first, etc).

Each layout has a short id, display name/description (for the gallery), and
a detailed design_brief - fed directly into the page-generation prompt in
place of the generic "modernDesign" block.
"""

LAYOUTS = [
    {
        "id": "brutalist-edge",
        "name": "Brutalist Edge",
        "description": "Raw, high-contrast, unpolished-on-purpose.",
        "design_brief": "Pure black and white with zero gradients, zero soft shadows - flat, raw, and intentional. Thick black borders (2-3px) around major blocks, no rounded corners anywhere. Oversized, condensed, tightly-tracked headline type - almost aggressive in scale. Monospace font used for labels, numbers, and small UI text (nav links, tags) as a structural accent. Sections are stark rectangular blocks with hard edges, deliberately unpolished-feeling in a confident way. Feels like a design studio's own bold, uncompromising site."
    },
    {
        "id": "editorial-luxury",
        "name": "Editorial Luxury",
        "description": "Magazine-style, huge serif type, high-end feel.",
        "design_brief": "Cream/off-white background with a single deep-black or burgundy accent. Massive, elegant serif display headlines (like a high-fashion magazine cover) paired with a refined thin sans-serif for body text. Extremely generous whitespace - content breathes like a print magazine layout. Full-bleed editorial-style image placement with pull-quote-style testimonials in large italic serif type. Thin gold or black hairline rules as section dividers. Feels like a premium lifestyle brand, not a local service business."
    },
    {
        "id": "neon-tech",
        "name": "Neon Tech",
        "description": "Dark mode, neon accents, startup energy.",
        "design_brief": "Near-black background (#0a0a0f) with one electric neon accent color (cyan or magenta) used for glows, borders, and CTAs. Glowing box-shadow effects on buttons and cards on hover (soft neon blur). Modern geometric sans-serif, slightly futuristic. Subtle animated gradient mesh or grid-pattern background behind the hero. Service cards have a thin neon-glow border on hover. Feels like a cutting-edge tech-forward company, unexpected and memorable for a local service business."
    },
    {
        "id": "minimalist-gallery",
        "name": "Minimalist Gallery",
        "description": "Ultra-minimal, huge photography, art-gallery feel.",
        "design_brief": "Almost entirely white/black and white, with photography doing all the visual work - massive full-bleed images with minimal text overlay. Extremely restrained typography - one weight, one size scale, used sparingly. No decorative elements, no icons, no colored accents beyond near-black. Huge negative space between sections (more empty space than content in places). Numbered sections (simple '01', '02' in thin type) instead of icons or graphics. Feels like a high-end architecture or design portfolio, not a typical business site."
    },
    {
        "id": "kinetic-grid",
        "name": "Kinetic Grid",
        "design_brief": "Bold primary-color blocks (one saturated color like cobalt-blue or hot-pink) arranged in an asymmetric grid of varying-sized rectangles. Strong geometric shapes (circles, triangles) used as decorative accents behind content. Bold, chunky sans-serif headlines. Grid cells have staggered entrance animations (already covered by the reveal system, but design the grid to visually support it - offset rectangles at different scales). Energetic, busy-but-organized composition. Feels dynamic, current, and attention-grabbing.",
        "description": "Bold geometric grid, energetic and dynamic."
    },
    {
        "id": "monochrome-architectural",
        "name": "Monochrome Architectural",
        "description": "Single accent color, sharp geometric sectioning.",
        "design_brief": "Strict black, white, and ONE accent color (nothing else) - disciplined and architectural. Sharp, precise geometric section divisions using clip-path (angular cuts, not curves). Structural grid lines visible as a subtle design element (thin vertical/horizontal rules dividing content areas, like architectural blueprints). Bold, wide, all-caps headline type with generous letter-spacing. Feels precise, confident, and design-forward, like a modern architecture or design firm."
    },
    {
        "id": "gentlemans-study",
        "name": "Gentleman's Study",
        "description": "Deep green and brass, private-library feel.",
        "design_brief": "Deep forest-green and walnut-brown palette with a single brass or aged-gold accent, on a near-black or deep-green background (not white). Classic serif display headlines with wide letter-spacing, evoking hand-lettered study/library signage. Thin brass hairline rules as section dividers. Subtle leather/wood-grain texture (via CSS gradient, not an image) behind the hero only. Trust badges and icons rendered as small line-art in the brass accent, not filled shapes. Feels like a private members' study or old-money law office - composed, unhurried, quietly confident."
    },
    {
        "id": "savile-row",
        "name": "Savile Row",
        "description": "Charcoal and pewter, bespoke-tailor precision.",
        "design_brief": "Charcoal and deep-navy palette with a single pewter or silver accent, crisp white space used sparingly for contrast. Sharp, exact geometric layouts - thin 1px pewter rules instead of shadows, everything measured to the pixel. A subtle pinstripe motif (very thin, widely-spaced vertical lines at low opacity) behind the hero section only. Refined serif or classic grotesque headline type, no rounding anywhere on buttons or cards. Feels like a bespoke tailor's own site - exacting, understated, precise."
    },
    {
        "id": "whiskey-oak",
        "name": "Whiskey & Oak",
        "description": "Amber and mahogany, warm low-lit lounge feel.",
        "design_brief": "Warm amber and deep mahogany-red palette on a near-black base, like low lighting in a wood-paneled room. Bold, confident slab-serif headlines. High-contrast, slightly desaturated photography treatment (CSS filter) to match the warm low-light mood. Buttons and CTAs styled as solid, substantial physical buttons (thicker padding, warm amber glow on hover, not a bright neon glow). Section dividers are thin horizontal rules in the amber accent. Feels like a whiskey bar or cigar lounge - rich, warm, unmistakably masculine without being loud."
    },
    {
        "id": "dark-cinematic",
        "name": "Dark Cinematic",
        "description": "Near-black backgrounds, dramatic single accent, film-style type.",
        "design_brief": "Near-black (#0d0d0d) background throughout, with one dramatic accent color (deep red, amber, or cool blue) used sparingly for maximum impact. Wide, cinematic-feeling hero with heavy dark vignette/gradient overlay. Elegant, wide-tracked uppercase headline type reminiscent of film title cards. High-contrast black-and-white photography treatment (desaturate or add contrast filter to hero images via CSS filter) for a cinematic, dramatic mood. Minimal chrome, content takes center stage. Feels premium, dramatic, and unforgettable."
    },
]
