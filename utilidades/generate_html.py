import markdown
import codecs

# Read markdown content
with codecs.open("Portafolio_Evidencias.md", "r", encoding="utf-8") as f:
    text = f.read()

# Convert to HTML with tables extension
html = markdown.markdown(text, extensions=["tables"])

# Read CSS
with codecs.open("style.css", "r", encoding="utf-8") as f:
    css = f.read()

# Generate full HTML page
full_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Reporte de Proyecto Unidad 2</title>
    <style>
        {css}
    </style>
</head>
<body>
    <div class="content">
        {html}
    </div>
</body>
</html>
"""

# Write to output file
with codecs.open("Reporte_Proyecto_Unidad_2.html", "w", encoding="utf-8") as f:
    f.write(full_html)

print("HTML generated successfully.")
