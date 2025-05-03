from flask import Blueprint, Response

sitemap_bp = Blueprint("sitemap", __name__)


@sitemap_bp.route("/sitemap.xml")
def sitemap():
    base_url = "https://camping.ddnsking.com"
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml += f"  <url><loc>{base_url}/</loc></url>\n"
    xml += "</urlset>"
    return Response(xml, mimetype="application/xml")
