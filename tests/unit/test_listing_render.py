from phd_searcher.pipeline.listing_render import listing_render_selector, render_wait_options


def _shell(contents=""):
    return ('<h2>Recruitment</h2><div><div class="custom-list-entry-wrapper">'
            + contents + '</div><div class="loadingLoadMore">Loading</div></div>')


def test_dynamic_list_hint_is_specific_and_reusable_after_render():
    selector = ".custom-list-entry-wrapper > * a[href]"
    assert listing_render_selector(_shell()) == selector
    assert listing_render_selector(_shell('<div><a href="/job/1">PhD</a></div>')) == selector
    assert render_wait_options({"render_wait_for": selector}) == {
        "wait_for": "css:" + selector, "wait_for_timeout": 6000,
    }


def test_no_extra_wait_for_static_unrelated_or_ambiguous_pages():
    assert listing_render_selector(_shell().replace("loadingLoadMore", "other")) is None
    assert listing_render_selector(_shell().replace("Recruitment", "News")) is None
    assert listing_render_selector(_shell() + _shell()) is None
    assert render_wait_options({}) == {}
    assert render_wait_options({"render_wait_for": "js:alert(1)"}) == {}
