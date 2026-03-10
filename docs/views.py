from django.shortcuts import render

from .services import get_doc_or_404, group_docs, load_docs, search_docs


def docs_index(request):
    query = request.GET.get("q", "").strip()
    results = search_docs(query)
    all_pages = load_docs()
    page = results[0] if results else (all_pages[0] if all_pages else None)

    context = {
        "page": page,
        "content_html": page["content_html"] if page else "",
        "doc_sections": group_docs(all_pages, active_slug=page["slug"] if page else "", query=query),
        "search_query": query,
        "search_results": results if query else [],
    }
    return render(request, "docs/manual.html", context)


def docs_detail(request, slug):
    query = request.GET.get("q", "").strip()
    page = get_doc_or_404(slug)
    all_pages = load_docs()

    context = {
        "page": page,
        "content_html": page["content_html"],
        "doc_sections": group_docs(all_pages, active_slug=page["slug"], query=query),
        "search_query": query,
        "search_results": search_docs(query) if query else [],
    }
    return render(request, "docs/manual.html", context)
