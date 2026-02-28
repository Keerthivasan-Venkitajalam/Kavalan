# Extension Icons

This directory should contain the following icon files:

- `icon-16.png` - 16x16 pixels (toolbar icon)
- `icon-48.png` - 48x48 pixels (extension management page)
- `icon-128.png` - 128x128 pixels (Chrome Web Store)

## Creating Icons

You can create these icons using any image editor. The icons should:

1. Use the Kavalan brand colors (purple/blue gradient)
2. Include a shield or protection symbol
3. Be clear and recognizable at small sizes

## Temporary Solution

For development, you can use placeholder icons or remove the icon references from manifest.json temporarily.

To generate icons quickly, you can use online tools like:
- https://www.favicon-generator.org/
- https://realfavicongenerator.net/

Or use ImageMagick to create simple colored squares:
```bash
convert -size 16x16 xc:#667EEA icon-16.png
convert -size 48x48 xc:#667EEA icon-48.png
convert -size 128x128 xc:#667EEA icon-128.png
```
