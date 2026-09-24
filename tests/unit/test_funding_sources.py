from datetime import date

import pytest

from phd_searcher.pipeline.funding_sources import HONOR_FROST_SCHOLARSHIPS_URL, funding_items
from phd_searcher.pipeline.normalize import normalize_item
from phd_searcher.pipeline.source_adapters import fetch_source_adapter

EVIDENCE = ('This scholarship is available to nationals of Cyprus, Lebanon, Egypt and Syria. '
            'Applicants must first apply to their chosen university. Tuition fees and a stipend are funded.')
HTML = f'''<main>
<h3>The deadline for all Masters and PhD scholarship applications to HFF is March 16th annually.</h3>
<a id="master-label" aria-controls="masters">Masters</a>
<a id="doctoral-label" aria-controls="doctoral">PhD</a>
<div id="masters" role="tabpanel" aria-labelledby="master-label"><div class="awb-tab-pane-inner">
<h2>Open Scholarships</h2><p>{EVIDENCE}</p><p>One year of Masters funding.</p></div></div>
<div id="doctoral" role="tabpanel" aria-labelledby="doctoral-label"><div class="awb-tab-pane-inner">
<h2>Open Scholarships</h2><p>{EVIDENCE}</p><p>Three years of doctoral funding.</p>
<h2>Targeted Scholarships</h2><p>{EVIDENCE}</p><p>Coastal archaeology at Cyprus.</p>
<p>Application deadline for HFF scholarship: 16 March 2026 (apply here)</p>
<p>Application deadline to the University of Cyprus: 31 March 2026 (Apply here)</p>
</div></div></main>'''


def test_tabs_and_sections_keep_identity_evidence_and_deadlines_separate():
    items = funding_items(HTML, HONOR_FROST_SCHOLARSHIPS_URL)
    normalized = [normalize_item(item, base_url=HONOR_FROST_SCHOLARSHIPS_URL) for item in items]
    assert [p.title for p in normalized] == ['Masters — Open Scholarships', 'PhD — Open Scholarships',
                                           'PhD — Targeted Scholarships']
    assert len({p.url for p in normalized}) == 3
    assert [p.deadline for p in normalized] == [None, None, date(2026, 3, 16)]
    assert 'annually' in normalized[1].deadline_raw
    assert 'Coastal archaeology' not in normalized[1].description
    assert 'One year' not in normalized[1].description
    assert 'Three years' not in normalized[2].description
    assert normalized[0].position_type == 'masters_mph'
    assert normalized[1].position_type == 'phd'


def test_changing_targeted_deadline_does_not_date_neighbouring_recurring_scheme():
    items = funding_items(HTML.replace('16 March 2026', '20 April 2030'), HONOR_FROST_SCHOLARSHIPS_URL)
    assert normalize_item(items[1], base_url=HONOR_FROST_SCHOLARSHIPS_URL).deadline is None
    assert normalize_item(items[2], base_url=HONOR_FROST_SCHOLARSHIPS_URL).deadline == date(2030, 4, 20)


@pytest.mark.parametrize('html', [
    'Access denied',
    HTML.replace('aria-labelledby="doctoral-label"', 'aria-labelledby="unknown"'),
    HTML.replace('aria-controls="doctoral"', 'aria-controls="another"'),
    HTML.replace('awb-tab-pane-inner', 'changed-layout'),
    HTML.replace('deadline for all Masters and PhD', 'general information for'),
    HTML.replace('Targeted Scholarships', 'Current recipients'),
    HTML.replace('Application deadline for HFF scholarship:', 'Opening date:'),
    HTML.replace('<h2>Targeted Scholarships</h2>', '<section><h2>Targeted Scholarships</h2></section>'),
])
def test_changed_layout_fails_instead_of_silently_clearing_the_feed(html):
    with pytest.raises(RuntimeError):
        funding_items(html, HONOR_FROST_SCHOLARSHIPS_URL)


async def test_adapter_is_source_scoped_and_never_paginates_or_fetches_arbitrary_hosts():
    assert await fetch_source_adapter({'adapter': 'funding'}, page_number=1,
                                      source_url=HONOR_FROST_SCHOLARSHIPS_URL) == []
    with pytest.raises(RuntimeError, match='untrusted'):
        await fetch_source_adapter({'adapter': 'funding'}, page_number=0, source_url='https://other.example/')
