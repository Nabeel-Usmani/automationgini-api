"""
20 website templates: 10 Normal Architecture (traditional/trustworthy, real stylistic range)
+ 10 Modern Architecture (bold/contemporary, real stylistic range).

Each template has a short id, display name/description (for the gallery), and a
detailed design_brief - fed directly into the page-generation prompt in place of
the old single generic "normalDesign"/"modernDesign" block.
"""

NORMAL_TEMPLATES = [
    {
        "id": "classic-corporate",
        "name": "Classic Corporate",
        "description": "Formal, symmetrical, serif headings — the look of an established firm.",
        "design_brief": "Navy and charcoal-gray palette with a single muted gold or steel-blue accent. Centered, symmetrical layouts with generous, formal whitespace. Serif headings (Georgia/Times-style) paired with a clean sans-serif body. Two-tier header: slim utility bar above a solid nav bar, both sticky. Services and testimonials in perfectly uniform bordered card grids. Straight rectangular section edges throughout - no diagonals or curves. Feels like a firm that's been trusted for 30+ years."
    },
    {
        "id": "warm-neighborhood",
        "name": "Warm Neighborhood",
        "description": "Earth tones, rounded corners, approachable and friendly.",
        "design_brief": "Warm terracotta, cream, and sage-green palette. Generously rounded corners on every card, button, and image (16-24px radius). Friendly, slightly informal sans-serif throughout (rounded letterforms preferred). Soft drop shadows, never harsh. Services presented as warm rounded cards with icon circles. Hero has a warm gradient overlay, not stark black. Feels like a friendly local business you'd wave to on the street, not a faceless company."
    },
    {
        "id": "bold-trade",
        "name": "Bold Trade",
        "description": "High-contrast, thick borders, built for contractors and trade services.",
        "design_brief": "One loud, saturated primary color (safety-orange, fire-engine red, or electric blue) against white and near-black. Thick (3-4px) solid borders on cards and buttons - no subtle shadows, bold outlines instead. Bold, condensed, all-caps headings that feel industrial and confident. Two-tier header with an unmissable phone-CTA button in the accent color. Square corners throughout, no rounding. Feels like a no-nonsense trade business that gets the job done."
    },
    {
        "id": "coastal-clean",
        "name": "Coastal Clean",
        "description": "Airy blues and whites, light and spacious.",
        "design_brief": "Soft ocean-blue, white, and warm sand-beige palette. Extremely generous whitespace and breathing room between sections - nothing feels cramped. Light, thin-weight sans-serif headings. Hero uses a full-width light photo with minimal, translucent-white text overlay (not dark). Wave-like soft curved section dividers (subtle border-radius on section tops, not sharp diagonals). Feels bright, clean, and unhurried."
    },
    {
        "id": "heritage-craft",
        "name": "Heritage Craft",
        "design_brief": "Deep forest-green, walnut-brown, and cream palette. Subtle textured background (very light noise/paper-grain via CSS gradient, not an image) behind key sections. Classic serif headings with wide letter-spacing, evoking hand-lettered signage. Ornamental thin-line dividers between sections. Services presented with a small decorative flourish (a thin rule or small icon) above each heading. Feels artisanal, established, and proud of craftsmanship.",
        "description": "Deep greens and browns, textured, artisanal feel."
    },
    {
        "id": "medical-trust",
        "name": "Medical Trust",
        "description": "Clean whites and teals, clinical and reassuring.",
        "design_brief": "Crisp white background with a calm teal or medical-blue accent, used sparingly. Extremely clean, uncluttered layouts with lots of negative space - nothing decorative or busy. Simple geometric sans-serif throughout, no flourishes. Rounded-square icon badges (not circles, not sharp squares) for trust signals. Subtle, soft shadows only. Feels clinical, calm, and immediately trustworthy - appropriate for healthcare, dental, or wellness services."
    },
    {
        "id": "family-business",
        "name": "Family Business",
        "description": "Soft pastels, photo-heavy, personal and warm.",
        "design_brief": "Soft pastel palette (dusty rose, muted yellow, soft blue) with cream backgrounds. Photo-heavy layout - real stock photos used generously and large, not just as accents. Handwritten-style accent font for one or two special headings (a signature/welcome message feel), paired with a simple sans-serif for the rest. Testimonials presented prominently with large quote marks and a personal, warm framing. Feels like a genuinely family-run business that knows its customers by name."
    },
    {
        "id": "metro-professional",
        "name": "Metro Professional",
        "description": "Sleek grays and blues, sharp urban lines.",
        "design_brief": "Cool slate-gray and steel-blue palette with crisp white space. Sharp, precise geometric layouts - thin 1px borders instead of shadows, everything feels measured and exact. Modern grotesque sans-serif (like Helvetica/Inter) throughout, no serifs anywhere. Services in a tight, precise grid with thin dividing lines between items rather than card boxes. Feels like a sharp, no-fuss professional operation in a big city."
    },
    {
        "id": "rustic-reliable",
        "name": "Rustic Reliable",
        "description": "Warm wood tones, rugged and dependable.",
        "design_brief": "Warm wood-brown, rust-orange, and off-white palette. Slightly rugged, sturdy-feeling typography - bold, slightly condensed headings. Subtle wood-grain-style gradient texture behind the hero section only. Buttons and CTAs styled like solid, chunky physical buttons (thicker padding, stronger shadow on hover). Section dividers are simple thick horizontal rules in the accent color. Feels dependable, hardworking, built to last."
    },
    {
        "id": "fresh-local",
        "name": "Fresh Local",
        "description": "Bright greens and yellows, modern but approachable.",
        "design_brief": "Bright lime-green and sunny-yellow accents against clean white. Playful but professional - rounded pill-shaped buttons and badges. Modern sans-serif headings with slightly bold weight, friendly not corporate. Service cards have a colorful top accent bar (each a slightly different shade of the palette) for visual variety. Light, energetic hover animations (slight bounce/scale) on interactive elements. Feels like a beloved local favorite that's modern and easy to work with."
    },
]

MODERN_TEMPLATES = [
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
