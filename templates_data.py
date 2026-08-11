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
        "id": "glassmorphism-premium",
        "name": "Glassmorphism Premium",
        "description": "Frosted glass panels, soft gradients, premium feel.",
        "design_brief": "Soft pastel-to-deep gradient background (e.g., indigo-to-violet) with frosted-glass 'glassmorphism' cards floating on top (semi-transparent white background, backdrop-blur, thin light border) for services/testimonials. Rounded, soft geometric shapes throughout. Modern, slightly rounded sans-serif typography. Subtle floating gradient orbs (soft blurred circles) as background decoration. Feels premium, soft, and current - a modern SaaS-product aesthetic applied to a local business."
    },
    {
        "id": "retro-futurism",
        "name": "Retro Futurism",
        "description": "Bold gradients, rounded shapes, playful yet premium.",
        "design_brief": "Bold sunset-style gradient (purple-to-orange or pink-to-yellow) used boldly in hero backgrounds and accent shapes. Rounded, chunky geometric shapes (large circles, soft blob shapes) as decorative background elements. Retro-inspired but clean display typography - slightly rounded, confident letterforms. Bright, saturated, high-energy color combinations. CTAs styled as bold rounded-pill buttons with gradient fills. Feels playful, optimistic, and distinctive without looking unprofessional."
    },
    {
        "id": "monochrome-architectural",
        "name": "Monochrome Architectural",
        "description": "Single accent color, sharp geometric sectioning.",
        "design_brief": "Strict black, white, and ONE accent color (nothing else) - disciplined and architectural. Sharp, precise geometric section divisions using clip-path (angular cuts, not curves). Structural grid lines visible as a subtle design element (thin vertical/horizontal rules dividing content areas, like architectural blueprints). Bold, wide, all-caps headline type with generous letter-spacing. Feels precise, confident, and design-forward, like a modern architecture or design firm."
    },
    {
        "id": "vibrant-maximalist",
        "name": "Vibrant Maximalist",
        "description": "Bold multi-color blocks, playful and youthful.",
        "design_brief": "Multiple bold saturated colors used confidently together (not just one accent - a full vibrant palette of 3-4 colors across different sections). Each major section has its own bold background color, creating a colorful, segmented scroll experience. Bold, rounded, friendly display typography. Playful decorative shapes (stars, squiggles, dots) as small accents. High energy throughout, embraces color rather than restraining it. Feels young, energetic, and impossible to ignore."
    },
    {
        "id": "dark-cinematic",
        "name": "Dark Cinematic",
        "description": "Near-black backgrounds, dramatic single accent, film-style type.",
        "design_brief": "Near-black (#0d0d0d) background throughout, with one dramatic accent color (deep red, amber, or cool blue) used sparingly for maximum impact. Wide, cinematic-feeling hero with heavy dark vignette/gradient overlay. Elegant, wide-tracked uppercase headline type reminiscent of film title cards. High-contrast black-and-white photography treatment (desaturate or add contrast filter to hero images via CSS filter) for a cinematic, dramatic mood. Minimal chrome, content takes center stage. Feels premium, dramatic, and unforgettable."
    },
]
