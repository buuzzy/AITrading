通过 CDN 使用 daisyUI
如何通过 CDN 使用 daisyUI？

您无需安装任何东西。 只需将以下任一代码添加到您 HTML 的 <head> 标签中:
<link href="https://cdn.jsdelivr.net/npm/daisyui@5" rel="stylesheet" type="text/css" />
<script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
Adding all themes
daisyui.css includes light and dark themes. For other themes, add themes.css file as well:

<link href="https://cdn.jsdelivr.net/npm/daisyui@5/themes.css" rel="stylesheet" type="text/css" />
Every part of daisyUI is available on CDN as separate CSS files.
Some uncommon Tailwind CSS color utility classes for daisyUI colors are available on additional CSS files for CDN usage, see colors docs for more info.
daisyUI variant class names like is-drawer-open and is-drawer-close are not included in the CDN files because adding them for all class names will result in a very large file size.
