from weasyprint import HTML


def generar_pdf(html_renderizado: str) -> bytes:
    """
    Convierte un documento HTML renderizado en un archivo PDF.

    Args:
        html_renderizado: HTML generado por las plantillas Jinja2.

    Returns:
        Contenido del PDF en formato bytes.
    """
    return HTML(string=html_renderizado).write_pdf()
