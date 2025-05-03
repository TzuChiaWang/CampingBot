from flask import Blueprint, Response, url_for
from datetime import datetime

sitemap_bp = Blueprint("sitemap", __name__)


@sitemap_bp.route("/sitemap.xml", methods=["GET"])
def sitemap():
    pages = []
    base_url = "https://camping.ddnsking.com"

    now = datetime.utcnow().date().isoformat()

    # 靜態頁面
    static_pages = ["index", "login", "about"]  # 如有更多可加
    for page in static_pages:
        pages.append({"loc": url_for(page, _external=True), "lastmod": now})

    sitemap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
"""
    for page in pages:
        sitemap_xml += f"""  <url>
    <loc>{page["loc"]}</loc>
    <lastmod>{page["lastmod"]}</lastmod>
    <priority>0.8</priority>
  </url>
"""

    sitemap_xml += "</urlset>"

    return Response(sitemap_xml, mimetype="application/xml")
