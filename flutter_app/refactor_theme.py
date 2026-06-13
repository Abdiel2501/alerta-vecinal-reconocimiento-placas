import os
import re
import glob

replacements = {
    r'AppTheme\.colorFondo': 'Theme.of(context).colorScheme.surface',
    r'AppTheme\.colorSuperficie': 'Theme.of(context).colorScheme.surfaceContainerHigh',
    r'AppTheme\.colorTarjetaHover': 'Theme.of(context).colorScheme.surfaceContainerHighest',
    r'AppTheme\.colorTarjeta': 'Theme.of(context).colorScheme.surfaceContainer',
    r'AppTheme\.colorAcentoSecundario': 'Theme.of(context).colorScheme.secondary',
    r'AppTheme\.colorAcentoOscuro': 'Theme.of(context).colorScheme.primaryContainer',
    r'AppTheme\.colorAcento': 'Theme.of(context).colorScheme.primary',
    r'AppTheme\.colorPurpuraClaro': 'Theme.of(context).colorScheme.onTertiary',
    r'AppTheme\.colorPurpura': 'Theme.of(context).colorScheme.tertiary',
    r'AppTheme\.colorTextoSecundario': 'Theme.of(context).colorScheme.onSurfaceVariant',
    r'AppTheme\.colorTextoTenue': 'Theme.of(context).colorScheme.outlineVariant',
    r'AppTheme\.colorTexto': 'Theme.of(context).colorScheme.onSurface',
    r'AppTheme\.colorBordeActivo': 'Theme.of(context).colorScheme.primary',
    r'AppTheme\.colorBordeSuave': 'Theme.of(context).colorScheme.surfaceContainerHighest',
    r'AppTheme\.colorBorde': 'Theme.of(context).colorScheme.outline',
    r'AppTheme\.colorExitoFondo': 'const Color(0xFF10B981).withValues(alpha: 0.1)',
    r'AppTheme\.colorExito': 'const Color(0xFF10B981)',
    r'AppTheme\.colorAdvertenciaFondo': 'const Color(0xFFF59E0B).withValues(alpha: 0.1)',
    r'AppTheme\.colorAdvertencia': 'const Color(0xFFF59E0B)',
    r'AppTheme\.colorErrorFondo': 'Theme.of(context).colorScheme.errorContainer',
    r'AppTheme\.colorError': 'Theme.of(context).colorScheme.error',
    r'AppTheme\.colorInfoFondo': 'const Color(0xFF3B82F6).withValues(alpha: 0.1)',
    r'AppTheme\.colorInfo': 'const Color(0xFF3B82F6)',
    r'AppTheme\.sombraElevada': 'AppTheme.sombraElevada(context)',
    r'AppTheme\.sombraBoton\((.*?)\)': r'AppTheme.sombraBoton(context, \1)',
    r'AppTheme\.gradienteBoton': 'AppTheme.gradienteBoton(context)',
    r'AppTheme\.gradienteFondo': 'AppTheme.gradienteFondo(context)',
    r'AppTheme\.gradienteAcento': 'AppTheme.gradienteAcento(context)',
}

def remove_const(content):
    # Intentar remover const invalidos de lineas comunes
    content = content.replace('const Theme.of', 'Theme.of')
    content = content.replace('const AppTheme.gradiente', 'AppTheme.gradiente')
    content = content.replace('const AppTheme.sombra', 'AppTheme.sombra')
    return content

for filepath in glob.glob('lib/**/*.dart', recursive=True):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    for pattern, repl in replacements.items():
        content = re.sub(pattern, repl, content)
        
    content = remove_const(content)
        
    if original != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
            print(f"Refactored: {filepath}")
