from fasthtml.common import *
import json
import sys
from collections import defaultdict
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from docopt import docopt

# Définition de l'aide de docopt
__doc__ = """Visualiseur de marque-pages Pinboard

Usage:
    app.py <file> [options]
    app.py -h | --help

Arguments:
    <file>          Fichier JSON de marque-pages à charger

Options:
    -h --help       Afficher cette aide
    --include-private       Inclure les marque-pages privés (exclus par défaut)
"""

# Analyser les arguments de ligne de commande avec docopt
args = docopt(__doc__)

# CSS personnalisé plus compact, sans PicoCSS
css = Style("""
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
           line-height: 1.4; max-width: 1300px; margin: 0 auto; padding: 15px; color: #333; }
    h1 { font-size: 24px; margin-bottom: 15px; }
    h1 a { color: inherit; text-decoration: none; }
    h1 a:hover { text-decoration: none; color: inherit; }
    h2 { font-size: 20px; margin-bottom: 10px; }
    a { color: #0066cc; text-decoration: none; }
    a:hover { text-decoration: none; }
    p { margin-bottom: 10px; }

    .container { display: flex; gap: 20px; }
    .content { flex: 1; }
    .sidebar { width: 300px; }

    .search-form { margin-bottom: 15px; display: flex; flex-wrap: wrap; gap: 10px; align-items: flex-end; }
    .search-field { flex: 1; min-width: 200px; }
    .search-form input { width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 3px; transition: border-color 0.2s; }
    .search-form input:focus { outline: none; border-color: #0066cc; }
    .search-form input.has-value { border-color: #28a745; box-shadow: 0 0 0 1px #28a745; }
    .search-form label { display: block; margin-bottom: 3px; font-size: 14px; color: #555; }
    .search-form button { padding: 8px 16px; background: #0066cc; color: white; border: none;
                         border-radius: 3px; cursor: pointer; height: 36px; }
    .search-form button:hover { background: #0055aa; }
    .form-actions { display: flex; gap: 5px; align-items: center; }
    .reset-link { font-size: 13px; color: #666; margin-left: 5px; }
    .reset-link:hover { color: #dc3545; text-decoration: underline; }

    .tag-list { margin-bottom: 15px; }
    .tag { display: inline-block; background: #f0f0f0; padding: 3px 8px;
           margin: 2px; border-radius: 3px; font-size: 13px; }
    .tag:hover { background: #e0e0e0; }
    .tag-count { color: #666; font-size: 0.9em; }
    .active-tag { background-color: #3a75c4; color: white; }
    .active-tag > .tag-count { color: white; }
    .active-tag:hover { background-color: #2c5d9e; }

    .filters { margin-bottom: 15px; font-size: 14px; }
    .filters a { color: #666; padding: 2px 6px; border-radius: 3px; margin-right: 5px; }
    .filters a:hover { background-color: #f0f0f0; }
    .filters a.active { font-weight: bold; color: #0066cc; background-color: #e9f0f9; }
    .filters-divider { color: #ccc; }

    .bookmark { padding: 8px 12px; margin-bottom: 2px; }
    .bookmark:hover { background: #f0f0f0f0; }
    .bookmark-title { font-size: 16px; font-weight: 600; margin-bottom: 3px; }
    .bookmark-domain { color: #666; font-size: 13px; margin-bottom: 5px; }
    .bookmark-description { margin-bottom: 5px; font-size: 14px; }
    .bookmark-footer { display: flex; justify-content: space-between;
                       align-items: center; font-size: 13px; }
    .bookmark-tags { flex: 1; }
    .bookmark-tag { background: #e9eef8; padding: 2px 6px; margin-right: 3px;
               border-radius: 3px; font-size: 12px; }
    .bookmark-tag:hover { background: #d9e2f2; }
    .bookmark-info { display: flex; align-items: center; gap: 5px; }
    .bookmark-attributes { display: flex; gap: 2px; }
    .bookmark-date { color: #666; font-size: 12px; font-family: monospace; position: relative; margin-left: 2px; }
    .bookmark-date:hover .full-date { display: block; }
    .full-date { display: none; position: absolute; right: 0; top: -30px; background: #333;
                color: white; padding: 5px; border-radius: 3px; font-size: 11px; white-space: nowrap;
                z-index: 10; }

    .return-link { display: block; margin-bottom: 15px; }
    .stats { margin-bottom: 15px; font-size: 14px; color: #666; }

    .pagination { display: flex; justify-content: center; margin: 20px 0; gap: 5px; }
    .pagination a, .pagination span {
        padding: 5px 10px;
        border: 1px solid #ddd;
        border-radius: 3px;
        color: #0066cc;
        background: #f8f8f8;
    }
    .pagination .current-page {
        background: #0066cc;
        color: white;
        border-color: #0066cc;
    }
    .pagination a:hover {
        background: #e0e0e0;
    }

    .htmx-indicator {
        display: none;
        margin-left: 10px;
        color: #666;
        font-size: 14px;
    }
    .htmx-request .htmx-indicator { display: inline; }

    @media (max-width: 768px) {
        .container { flex-direction: column; }
        .sidebar { width: 100%; order: 2; }
        .content { order: 1; }
    }
""")

# JavaScript pour mettre en évidence les champs remplis et gérer la réinitialisation
js = Script("""
document.addEventListener('DOMContentLoaded', function() {
    // Fonction pour mettre à jour la classe des inputs en fonction de leur valeur
    function updateInputStyles() {
        document.querySelectorAll('.search-form input').forEach(function(input) {
            if (input.value.trim() !== '') {
                input.classList.add('has-value');
            } else {
                input.classList.remove('has-value');
            }
        });
    }

    // Mettre à jour les styles au chargement initial
    updateInputStyles();

    // Mettre à jour les styles quand une entrée change
    document.querySelectorAll('.search-form input').forEach(function(input) {
        input.addEventListener('input', updateInputStyles);
    });

    // Vérifier après les requêtes HTMX complétées
    document.body.addEventListener('htmx:afterSettle', updateInputStyles);

    // Réinitialiser les champs de formulaire sur clic du bouton
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('reset-link')) {
            document.querySelectorAll('.search-form input').forEach(function(input) {
                input.value = '';
            });
            updateInputStyles();
        }
    });

    // Gérer le clic sur un tag pour l'ajouter au filtre
    document.body.addEventListener('click', function(e) {
        if (e.target.classList.contains('bookmark-tag')) {
            e.preventDefault();

            // Récupérer le tag cliqué
            const tagText = e.target.innerText.trim();
            const tagFilterInput = document.getElementById('tag-filter');

            if (tagFilterInput) {
                // Si le champ est vide, ajouter le tag
                if (tagFilterInput.value.trim() === '') {
                    tagFilterInput.value = tagText;
                }
                // Sinon, vérifier si le tag est déjà présent
                else {
                    const currentTags = tagFilterInput.value.split(',').map(t => t.trim());
                    if (!currentTags.includes(tagText)) {
                        tagFilterInput.value += ',' + tagText;
                    }
                }

                // Déclencher l'événement input pour mettre à jour les styles
                tagFilterInput.dispatchEvent(new Event('input'));

                // Déclencher la recherche HTMX
                tagFilterInput.dispatchEvent(new Event('keyup'));
            }
        }
    });
});
""")

# Créer l'application sans PicoCSS (conserver les headers css et js existants)
app, rt = fast_app(
    pico=False,
    hdrs=(
        Link(
            rel="icon",
            href="data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2016%2016'%3E%3Ctext%20x='0'%20y='14'%3E📌%3C/text%3E%3C/svg%3E",
            type="image/svg+xml"
        ),
        css,
        js
    )
)

# Fonction pour extraire le domaine
def get_domain(url):
    return urlparse(url).netloc

# Charger le fichier JSON spécifié en argument
try:
    json_path = args['<file>']
    with open(json_path, 'r', encoding='utf-8') as f:
        bookmarks = json.load(f)
        print(f"[+] {len(bookmarks)} marque-pages chargés depuis {json_path}")

    # Filtrer les marque-pages privés si l'option --include-private n'est pas spécifiée
    if not args['--include-private']:
        public_bookmarks = [b for b in bookmarks if b.get('shared') != 'no']
        print(f"[-] {len(bookmarks) - len(public_bookmarks)} marque-pages privés ignorés")
        bookmarks = public_bookmarks

    # Extraire la date du nom du fichier
    import re
    date_match = re.search(r'(\d{4})\.(\d{2})\.(\d{2})_(\d{2})\.(\d{2})', json_path)
    if date_match:
        year, month, day, hour, minute = date_match.groups()
        # export_date = f"{day}/{month}/{year} à {hour}:{minute}"
        export_date = f"{day}/{month}/{year}"
    else:
        export_date = "Date inconnue"

    # Extraire tous les tags et compter leurs occurrences
    tag_counts = defaultdict(int)

    # Compter les marque-pages par attribut
    attr_counts = {
        'all': len(bookmarks),
        'private': 0,
        'public': 0,
        'unread': 0,
        'untagged': 0
    }

    for bookmark in bookmarks:
        # Compter les tags
        if 'tags' in bookmark and bookmark['tags']:
            for tag in bookmark['tags'].split():
                tag_counts[tag] += 1
        else:
            attr_counts['untagged'] += 1

        # Compter les attributs
        if bookmark.get('shared') == 'no':
            attr_counts['private'] += 1
        else:
            attr_counts['public'] += 1

        if bookmark.get('toread') == 'yes':
            attr_counts['unread'] += 1

    # Trier les tags par nom
    sorted_tags = sorted(tag_counts.items())

except Exception as e:
    print(f"[!] Erreur lors du chargement du fichier: {e}")
    bookmarks = []
    sorted_tags = []
    attr_counts = {'all': 0, 'private': 0, 'public': 0, 'unread': 0, 'untagged': 0}

# Nombre d'éléments par page
ITEMS_PER_PAGE = 250

# Fonction pour filtrer les marque-pages selon les critères de recherche
def filter_bookmarks(bookmarks_list, search_text="", domains="", filter_tags="", attribute="all"):
    filtered = bookmarks_list

    # Filtrer par texte de recherche
    if search_text:
        search_text = search_text.lower()
        filtered = [b for b in filtered if
                  search_text in b['description'].lower() or
                  (b.get('extended') and search_text in b['extended'].lower())]

    # Filtrer par domaines (inclusion et exclusion)
    if domains:
        # Séparer les domaines à inclure et exclure
        include_domains = []
        exclude_domains = []
        for d in [d.strip().lower() for d in domains.split(',') if d.strip()]:
            if d.startswith('!'):
                exclude_domains.append(d[1:])  # Supprimer le '!' au début
            else:
                include_domains.append(d)

        # Appliquer le filtrage d'inclusion si des domaines à inclure sont spécifiés
        if include_domains:
            filtered = [b for b in filtered if
                      any(d in get_domain(b['href']).lower() for d in include_domains)]

        # Appliquer le filtrage d'exclusion si des domaines à exclure sont spécifiés
        if exclude_domains:
            filtered = [b for b in filtered if not
                      any(d in get_domain(b['href']).lower() for d in exclude_domains)]

    # Filtrer par tags (inclusion et exclusion)
    if filter_tags:
        # Séparer les tags à inclure et exclure
        include_tags = []
        exclude_tags = []
        for t in [t.strip().lower() for t in filter_tags.split(',') if t.strip()]:
            if t.startswith('!'):
                exclude_tags.append(t[1:])  # Supprimer le '!' au début
            else:
                include_tags.append(t)

        # Appliquer le filtrage d'inclusion si des tags à inclure sont spécifiés
        if include_tags:
            filtered = [b for b in filtered if
                      'tags' in b and
                      all(any(t == tag.lower() for tag in b['tags'].split()) for t in include_tags)]

        # Appliquer le filtrage d'exclusion si des tags à exclure sont spécifiés
        if exclude_tags:
            filtered = [b for b in filtered if
                      not ('tags' in b and
                          any(any(t == tag.lower() for tag in b['tags'].split()) for t in exclude_tags))]

    # Filtrer par attribut
    if attribute != "all":
        if attribute == "private":
            filtered = [b for b in filtered if b.get('shared') == 'no']
        elif attribute == "public":
            filtered = [b for b in filtered if b.get('shared') == 'yes']
        elif attribute == "unread":
            filtered = [b for b in filtered if b.get('toread') == 'yes']
        elif attribute == "untagged":
            filtered = [b for b in filtered if not b.get('tags') or b.get('tags') == '']

    return filtered

# Fonction pour paginer les résultats
def paginate_results(items, page=1, per_page=ITEMS_PER_PAGE):
    page = max(1, page)  # Assurer que la page est au moins 1
    start = (page - 1) * per_page
    end = start + per_page
    total_pages = (len(items) + per_page - 1) // per_page  # Arrondir au supérieur

    return {
        'items': items[start:end],
        'page': page,
        'total_pages': total_pages,
        'total_items': len(items),
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'showing_start': start + 1 if items else 0,
        'showing_end': min(end, len(items))
    }

# Fonction pour créer le formulaire de recherche
def create_search_form(search_text="", domains="", filter_tags="", current_tag="", results_target="#search-results", page=1, attribute="all"):
    form_action = f"/tag/{current_tag}" if current_tag else "/"

    return Form(
        Div(
            Label("Rechercher dans les descriptions", fr="search-text"),
            Input(type="text", id="search-text", name="search", value=search_text,
                  placeholder="Mots-clés à rechercher...",
                  hx_post=f"/search{'/' + current_tag if current_tag else ''}",
                  hx_trigger="keyup changed delay:300ms",
                  hx_target=results_target,
                  hx_include="#domain-filter,#tag-filter",
                  hx_vals=json.dumps({"attribute": attribute})),
            cls="search-field"
        ),
        Div(
            Label("Filtrer par domaines", fr="domain-filter"),
            Input(type="text", id="domain-filter", name="domains", value=domains,
                  placeholder="example.com, github.com...",
                  hx_post=f"/search{'/' + current_tag if current_tag else ''}",
                  hx_trigger="keyup changed delay:300ms",
                  hx_target=results_target,
                  hx_include="#search-text,#tag-filter",
                  hx_vals=json.dumps({"attribute": attribute})),
            cls="search-field"
        ),
        Div(
            Label("Filtrer par tags", fr="tag-filter"),
            Input(type="text", id="tag-filter", name="filter_tags", value=filter_tags,
                  placeholder="design, python, tutorial...",
                  hx_post=f"/search{'/' + current_tag if current_tag else ''}",
                  hx_trigger="keyup changed delay:300ms",
                  hx_target=results_target,
                  hx_include="#search-text,#domain-filter",
                  hx_vals=json.dumps({"attribute": attribute})),
            cls="search-field"
        ),
        Div(
            Button("Rechercher", type="submit"),
            A("Réinitialiser", href=f"/{'tag/' + current_tag if current_tag else ''}",
              cls="reset-link",
              hx_post=f"/search{'/' + current_tag if current_tag else ''}",
              hx_trigger="click",
              hx_target=results_target,
              hx_vals=json.dumps({"search": "", "domains": "", "filter_tags": "", "attribute": "all"}),
              hx_push_url=f"/{'tag/' + current_tag if current_tag else ''}"),
            cls="form-actions"
        ),
        Span("Recherche en cours...", cls="htmx-indicator"),
        method="get",
        action=form_action,
        cls="search-form"
    )

# Fonction pour créer les filtres par attribut
def create_attribute_filters(attribute="all", current_tag="", search="", domains="", filter_tags=""):
    attributes = [
        ('all', 'Tous'),
        ('private', 'Privés'),
        ('public', 'Publics'),
        ('unread', 'Non lus'),
        ('untagged', 'Sans tag')
    ]

    filter_elements = []

    for attr_id, attr_label in attributes:
        is_active = attr_id == attribute

        base_url = f"/tag/{current_tag}" if current_tag else "/"
        query_params = []
        if search:
            query_params.append(f"search={search}")
        if domains:
            query_params.append(f"domains={domains}")
        if filter_tags:
            query_params.append(f"filter_tags={filter_tags}")

        query_params.append(f"attribute={attr_id}")
        url = f"{base_url}?{'&'.join(query_params)}"

        filter_elements.append(
            A(f"{attr_label} ({attr_counts.get(attr_id, 0)})",
              href=url,
              hx_post=f"/search{'/' + current_tag if current_tag else ''}",
              hx_trigger="click",
              hx_target="#search-results",
              hx_include="#search-text,#domain-filter,#tag-filter",
              hx_vals=json.dumps({"attribute": attr_id}),
              hx_push_url=url,
              cls=f"{'active' if is_active else ''}")
        )

        # Ajouter un séparateur sauf pour le dernier élément
        if attr_id != attributes[-1][0]:
            filter_elements.append(Span("‧", cls="filters-divider"))

    return Div(*filter_elements, cls="filters")

# Fonction pour créer les éléments des marque-pages
def create_bookmark_elements(filtered_bookmarks, search="", domains="", filter_tags="", current_tag="", page=1, attribute="all"):
    bookmark_elements = []

    # Paginer les résultats
    paginated = paginate_results(filtered_bookmarks, page)

    for bookmark in paginated['items']:
        domain = get_domain(bookmark['href'])

        # Créer les éléments de tags pour ce marque-page
        tag_elements = []
        if 'tags' in bookmark and bookmark['tags']:
            for tag in bookmark['tags'].split():
                is_current = tag == current_tag

                tag_elements.append(
                    A(tag,
                      href=f"/tag/{tag}",
                      cls=f"bookmark-tag {'active-tag' if is_current else ''}")
                )

        # Afficher la date ISO en monospace avec le timezone au survol
        date_iso = bookmark['time'].split('T')[0]
        full_time = bookmark['time']

        # Attributs du marque-page avec emojis
        attr_elements = []
        if bookmark.get('shared') == 'no':
            attr_elements.append(Span("🙈", title="Privé", cls="bookmark-attribute"))
        # else:
        #     attr_elements.append(Span("🌐", title="Public", cls="bookmark-attribute"))

        if bookmark.get('toread') == 'yes':
            attr_elements.append(Span("👀", title="À lire", cls="bookmark-attribute"))

        # Créer le marque-page
        bookmark_card = Div(
            Div(A(bookmark['description'], href=bookmark['href'], target="_blank"),
                cls="bookmark-title"),
            Div(domain, cls="bookmark-domain"),
            Div(bookmark.get('extended', ''), cls="bookmark-description") if bookmark.get('extended') else None,
            Div(
                Div(*tag_elements if tag_elements else [], cls="bookmark-tags"),
                Div(
                    Div(*attr_elements, cls="bookmark-attributes"),
                    Div(date_iso, Span(full_time, cls="full-date"), cls="bookmark-date"),
                    cls="bookmark-info"
                ),
                cls="bookmark-footer"
            ),
            cls="bookmark"
        )
        bookmark_elements.append(bookmark_card)

    return bookmark_elements, paginated

# Fonction pour créer la pagination
def create_pagination(paginated, base_url, search="", domains="", filter_tags="", current_tag="", attribute="all"):
    # Ne pas afficher la pagination s'il n'y a qu'une seule page
    if paginated['total_pages'] <= 1:
        return None

    # Construire l'URL de base avec les paramètres de recherche
    url_params = []
    if search:
        url_params.append(f"search={search}")
    if domains:
        url_params.append(f"domains={domains}")
    if filter_tags:
        url_params.append(f"filter_tags={filter_tags}")
    if attribute and attribute != "all":
        url_params.append(f"attribute={attribute}")

    params_str = "&".join(url_params)
    if params_str:
        params_str = "&" + params_str

    # Créer les éléments de pagination
    pagination_elements = []

    # Lien "Précédent"
    if paginated['has_prev']:
        pagination_elements.append(
            A("« Précédent",
              href=f"{base_url}?page={paginated['page']-1}{params_str}",
              hx_post=f"/search{'/'+current_tag if current_tag else ''}?page={paginated['page']-1}",
              hx_trigger="click",
              hx_target="#search-results",
              hx_include="#search-text,#domain-filter,#tag-filter",
              hx_vals=json.dumps({"attribute": attribute}),
              hx_push_url=f"{base_url}?page={paginated['page']-1}{params_str}")
        )

    # Pages numérotées
    max_pages = 7  # Nombre maximum de liens de page à afficher

    if paginated['total_pages'] <= max_pages:
        # Afficher toutes les pages si leur nombre est inférieur à max_pages
        for i in range(1, paginated['total_pages'] + 1):
            if i == paginated['page']:
                pagination_elements.append(Span(str(i), cls="current-page"))
            else:
                pagination_elements.append(
                    A(str(i),
                      href=f"{base_url}?page={i}{params_str}",
                      hx_post=f"/search{'/'+current_tag if current_tag else ''}?page={i}",
                      hx_trigger="click",
                      hx_target="#search-results",
                      hx_include="#search-text,#domain-filter,#tag-filter",
                      hx_vals=json.dumps({"attribute": attribute}),
                      hx_push_url=f"{base_url}?page={i}{params_str}")
                )
    else:
        # Afficher une pagination avec ellipses pour les grands nombres de pages
        # Toujours montrer la première page, la dernière page, et les pages autour de la page courante

        # Calculer les pages à afficher
        pages_to_show = set([1, paginated['total_pages']])  # Toujours montrer la première et la dernière

        # Pages autour de la page courante
        for i in range(max(1, paginated['page'] - 2), min(paginated['total_pages'] + 1, paginated['page'] + 3)):
            pages_to_show.add(i)

        # Trier les pages
        pages_to_show = sorted(list(pages_to_show))

        # Afficher les pages avec ellipses si nécessaire
        prev_page = 0
        for i in pages_to_show:
            if prev_page + 1 < i:
                pagination_elements.append(Span("...", cls="ellipsis"))

            if i == paginated['page']:
                pagination_elements.append(Span(str(i), cls="current-page"))
            else:
                pagination_elements.append(
                    A(str(i),
                      href=f"{base_url}?page={i}{params_str}",
                      hx_post=f"/search{'/'+current_tag if current_tag else ''}?page={i}",
                      hx_trigger="click",
                      hx_target="#search-results",
                      hx_include="#search-text,#domain-filter,#tag-filter",
                      hx_vals=json.dumps({"attribute": attribute}),
                      hx_push_url=f"{base_url}?page={i}{params_str}")
                )

            prev_page = i

    # Lien "Suivant"
    if paginated['has_next']:
        pagination_elements.append(
            A("Suivant »",
              href=f"{base_url}?page={paginated['page']+1}{params_str}",
              hx_post=f"/search{'/'+current_tag if current_tag else ''}?page={paginated['page']+1}",
              hx_trigger="click",
              hx_target="#search-results",
              hx_include="#search-text,#domain-filter,#tag-filter",
              hx_vals=json.dumps({"attribute": attribute}),
              hx_push_url=f"{base_url}?page={paginated['page']+1}{params_str}")
        )

    return Div(*pagination_elements, cls="pagination")

# Fonction pour créer le contenu de recherche
def create_search_content(filtered_bookmarks, search="", domains="", filter_tags="", current_tag="", page=1, attribute="all"):
    bookmark_elements, paginated = create_bookmark_elements(filtered_bookmarks, search, domains, filter_tags, current_tag, page, attribute)

    # Créer la pagination
    base_url = f"/tag/{current_tag}" if current_tag else "/"
    pagination = create_pagination(paginated, base_url, search, domains, filter_tags, current_tag, attribute)

    # Construire le contenu
    content_elements = [
        create_attribute_filters(attribute, current_tag, search, domains, filter_tags),
        Div(f"{paginated['total_items']} résultats ({paginated['showing_start']}-{paginated['showing_end']} marque-pages affichés)", cls="stats")
    ]

    # Ajouter les éléments de marque-pages ou un message si aucun résultat
    if bookmark_elements:
        content_elements.extend(bookmark_elements)
    else:
        content_elements.append(P("Aucun marque-page trouvé."))

    # Ajouter la pagination si nécessaire
    if pagination:
        content_elements.append(pagination)

    # Créer la structure de résultats de recherche
    return Div(*content_elements, id="search-results")

# Fonction pour créer les liens de tags
def create_tag_links(tag_list, current_tag=""):
    tag_links = []
    for tag, count in tag_list:
        is_active = tag == current_tag

        tag_links.append(
            A(f"{tag} ", Span(f"({count})", cls="tag-count"),
              href=f"/tag/{tag}",
              cls=f"tag {'active-tag' if is_active else ''}")
        )

    return tag_links

# Endpoint pour la recherche instantanée
@rt("/search")
def post(search: str = "", domains: str = "", filter_tags: str = "", page: int = 1, attribute: str = "all"):
    # Filtrer les marque-pages selon les critères de recherche
    filtered = filter_bookmarks(bookmarks, search, domains, filter_tags, attribute)
    # Retourner uniquement la partie résultats (pour HTMX)
    return create_search_content(filtered, search, domains, filter_tags, page=page, attribute=attribute)

# Endpoint pour la recherche instantanée avec tag
@rt("/search/{tag_name}")
def post(tag_name: str, search: str = "", domains: str = "", filter_tags: str = "", page: int = 1, attribute: str = "all"):
    # Filtrer les marque-pages selon les critères de recherche et le tag
    filtered = filter_bookmarks(bookmarks, search, domains, filter_tags, attribute)
    # Filtrer par le tag de l'URL (toujours appliqué)
    filtered = [b for b in filtered if 'tags' in b and tag_name in b['tags'].split()]
    # Retourner uniquement la partie résultats (pour HTMX)
    return create_search_content(filtered, search, domains, filter_tags, tag_name, page, attribute)

# Route principale - Affiche tous les marque-pages
@rt
def index(search: str = "", domains: str = "", filter_tags: str = "", page: int = 1, attribute: str = "all"):
    # Filtrer les marque-pages selon les critères de recherche (s'il y en a)
    filtered_bookmarks = filter_bookmarks(bookmarks, search, domains, filter_tags, attribute)

    # Créer la structure de la page
    page_title = f"Marque-pages Pinboard "

    page_content = Div(
        Div(
            H1(A(f"📌 Marque-pages Pinboard", href="/")),
            create_search_form(search, domains, filter_tags, results_target="#search-results", page=page, attribute=attribute),
            create_search_content(filtered_bookmarks, search, domains, filter_tags, page=page, attribute=attribute),
            cls="content"
        ),
        Div(
            H2("Tags ", Span(f"({len(sorted_tags)})", cls="tag-count")),
            Div(*create_tag_links(sorted_tags), cls="tag-list"),
            cls="sidebar"
        ),
        cls="container"
    )

    return Title(page_title), page_content

# Route pour la page de tag
@rt("/tag/{tag_name}")
def get(tag_name: str, search: str = "", domains: str = "", filter_tags: str = "", page: int = 1, attribute: str = "all"):
    # Filtrer les marque-pages selon les critères de recherche et le tag
    filtered_bookmarks = filter_bookmarks(bookmarks, search, domains, filter_tags, attribute)
    # Filtrer par le tag de l'URL (toujours appliqué)
    filtered_bookmarks = [b for b in filtered_bookmarks if 'tags' in b and tag_name in b['tags'].split()]

    # Créer la structure de la page
    page_title = f"Marque-pages Pinboard - Tag: {tag_name}"

    page_content = Div(
        Div(
            H1(A(f"📌 Marque-pages Pinboard", href="/")),
            A("← Retour à tous les marque-pages",
              href="/",
              cls="return-link"),
            create_search_form(search, domains, filter_tags, tag_name, "#search-results", page, attribute),
            create_search_content(filtered_bookmarks, search, domains, filter_tags, tag_name, page, attribute),
            cls="content"
        ),
        Div(
            H2("Tags ", Span(f"({len(sorted_tags)})", cls="tag-count")),
            Div(*create_tag_links(sorted_tags, tag_name), cls="tag-list"),
            cls="sidebar"
        ),
        cls="container"
    )

    return Title(page_title), page_content

# Démarrer le serveur
if __name__ == "__main__":
    serve()
