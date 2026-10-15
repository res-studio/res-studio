# Customize the RES Studio look

RES Studio's GitHub landing page uses a customizable SVG banner and GitHub Markdown. The **GitHub website chrome (header, menus, sidebar and global colors) cannot be changed by repository code**.

## Color system

| Token | Hex | Role |
| --- | --- | --- |
| Background | `#080C1D` | Deep night canvas |
| Surface | `#111B38` | Panels |
| Cyan | `#32E6DD` | Technical highlight |
| Blue | `#6488FF` | Secondary highlight |
| Purple | `#C17CFF` | Brand gradient |
| Text | `#F5F8FF` | Headlines |

## Change the appearance

1. Open [`assets/res-banner.svg`](assets/res-banner.svg) and click the pencil icon on GitHub.
2. Replace the `#RRGGBB` color values to create a different palette.
3. Change the banner text, terminal illustration, or the gradient stops. Keep the `viewBox="0 0 1200 380"` for consistent proportions.
4. Commit your changes; the README automatically displays the updated banner.
5. Edit [`README.md`](README.md) to reorder cards, change the intro, update badges or navigation links.
6. Use the repository's **Settings → General** to update its description, website and topics; add a social preview under **Settings → General → Social preview**, if available.

## Theme presets

| Preset | Background | Accent A | Accent B |
| --- | --- | --- | --- |
| Neon ocean (default) | `#080C1D` | `#32E6DD` | `#6488FF` |
| Cyber violet | `#100820` | `#A855F7` | `#F472B6` |
| Matrix green | `#06140F` | `#4ADE80` | `#2DD4BF` |
| Solar amber | `#17110B` | `#FBBF24` | `#FB7185` |

## GitHub limitations

The README cannot inject CSS or JavaScript into GitHub's interface. Images, badges, tables and collapsible sections are supported; SVG should be treated as a static image, not an interactive app. The repository is open source, but the RES Studio application remains local-only.
