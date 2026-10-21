import json
import unittest
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
CONTENT_SCRIPT = ROOT / "content.js"
TARGET_URL = (
    "https://chatgpt.com/g/g-p-6a9b75aa03608191a247260fa120c1ae-impurity/"
    "c/6aa6e282-9290-83e9-a810-87cd1ae29cc1"
)


def long_paragraph(label: str) -> str:
    sentence = f"{label} records the experimental observation and explains the underlying mechanism. "
    return sentence * 18


def export_fixture(page, body: str, url: str = TARGET_URL):
    page.route(
        "**/*",
        lambda route: route.fulfill(status=200, content_type="text/html; charset=utf-8", body=body),
    )
    page.add_init_script(
        """
        window.chrome = {
          runtime: {
            onMessage: {
              addListener(listener) {
                window.__exportListener = listener;
              }
            }
          }
        };
        """
    )
    page.add_init_script(f"window.__sourceUrl = {json.dumps(TARGET_URL)}")
    page.goto(url, wait_until="domcontentloaded")
    page.add_script_tag(path=str(CONTENT_SCRIPT))
    response = page.evaluate(
        """
        () => new Promise((resolve) => {
          window.__exportListener(
            { type: 'DEEP_RESEARCH_EXPORT_MARKDOWN', titlePrefix: 'gpt-', sourceUrl: window.__sourceUrl },
            null,
            resolve,
          );
        })
        """
    )
    return json.loads(json.dumps(response))


class ContentExportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.page = self.browser.new_page(viewport={"width": 1440, "height": 1000})

    def tearDown(self):
        self.page.close()

    def test_prefers_open_fullscreen_report_over_conversation(self):
        body = f"""
        <!doctype html><html><body>
          <main>
            <article data-testid="conversation-turn-1">
              <div data-message-author-role="user">SECRET USER PROMPT MUST NOT BE EXPORTED</div>
            </article>
            <article data-testid="conversation-turn-2">
              <div data-message-author-role="assistant"><p>Earlier short answer.</p></div>
            </article>
          </main>
          <div role="dialog" aria-label="Deep research report">
            <button aria-label="Close">Close</button>
            <button aria-expanded="false" onclick="setTimeout(() => {{
              const panel = document.createElement('section');
              panel.innerHTML = `
                <h2>Sources</h2>
                <div>1 <a href='https://example.com/source-one'>Primary source</a></div>
                <div>2 <a href='https://example.org/source-two'>Secondary source</a></div>
              `;
              document.body.appendChild(panel);
            }}, 350)">Sources</button>
            <article data-testid="deep-research-report" class="markdown prose">
              <h1>Impurity Solubility Report</h1>
              <h2>Thermodynamic evidence</h2>
              <p>{long_paragraph('FULLSCREEN REPORT MARKER')}</p>
              <p>Primary evidence <sup data-citation-id="source-1">1</sup>.</p>
              <h2>Crystallization consequences</h2>
              <p>{long_paragraph('CRYSTALLIZATION SECTION')}</p>
              <p>Secondary evidence <sup data-citation-id="source-2">2</sup>.</p>
            </article>
          </div>
        </body></html>
        """

        response = export_fixture(self.page, body)

        self.assertTrue(response["ok"])
        result = response["result"]
        self.assertEqual(result["title"], "gpt-Impurity Solubility Report")
        self.assertIn("FULLSCREEN REPORT MARKER", result["markdown"])
        self.assertNotIn("SECRET USER PROMPT", result["markdown"])
        self.assertEqual(result["sourceCount"], 2)
        self.assertEqual(result["citationCount"], 2, result["markdown"])
        self.assertEqual(result["markdown"].count("# gpt-Impurity Solubility Report"), 1)

    def test_direct_conversation_requires_a_fullscreen_report(self):
        body = f"""
        <!doctype html><html><body>
          <main>
            <article data-testid="conversation-turn-1">
              <div data-message-author-role="user">
                USER QUESTION MUST NOT BE EXPORTED {long_paragraph('question')}
              </div>
            </article>
            <article data-testid="conversation-turn-2">
              <div data-message-author-role="assistant">
                <div class="markdown prose">
                  <h1>Older Deep Research</h1>
                  <h2>Old evidence</h2>
                  <p>{long_paragraph('OLDER REPORT MARKER')}</p>
                  <h2>Old conclusion</h2>
                  <p>{long_paragraph('OLDER CONCLUSION')}</p>
                </div>
              </div>
            </article>
            <article data-testid="conversation-turn-3">
              <div data-message-author-role="assistant">
                <div class="markdown prose">
                  <h1>Final Deep Research</h1>
                  <h2>Evidence base</h2>
                  <p>{long_paragraph('LATEST REPORT MARKER')}</p>
                  <p>Evidence <a href="https://example.net/evidence">1</a>.</p>
                  <h2>Conclusion</h2>
                  <p>{long_paragraph('FINAL CONCLUSION')}</p>
                </div>
              </div>
            </article>
            <form><textarea>Ask anything</textarea></form>
          </main>
        </body></html>
        """

        response = export_fixture(self.page, body)

        self.assertFalse(response["ok"])
        self.assertIn("全屏报告", response["error"])

    def test_selected_fullscreen_writing_block_wins_over_latest_message(self):
        body = f"""
        <!doctype html><html><body>
          <main>
            <div data-message-author-role="assistant">
              <div class="markdown prose">
                <h1>Wrong Latest Report</h1>
                <h2>Latest evidence</h2>
                <p>{long_paragraph('WRONG LATEST REPORT')}</p>
                <h2>Latest conclusion</h2>
                <p>{long_paragraph('WRONG LATEST CONCLUSION')}</p>
              </div>
            </div>
          </main>
          <div class="fixed start-0 end-0 top-0 bottom-0">
            <div
              class="markdown prose"
              data-writing-block-fullscreen-editor-region="true"
              data-writing-block-fullscreen-editor-layout="fullscreen"
            >
              <h1>Selected First Report</h1>
              <h2>Selected evidence</h2>
              <p>{long_paragraph('SELECTED FIRST REPORT')}</p>
              <h2>Selected conclusion</h2>
              <p>{long_paragraph('SELECTED FIRST CONCLUSION')}</p>
              <p>Evidence <a href="https://example.edu/selected">1</a>.</p>
            </div>
          </div>
        </body></html>
        """

        response = export_fixture(self.page, body)

        self.assertTrue(response["ok"])
        result = response["result"]
        self.assertEqual(result["title"], "gpt-Selected First Report")
        self.assertIn("SELECTED FIRST REPORT", result["markdown"])
        self.assertNotIn("WRONG LATEST REPORT", result["markdown"])

    def test_extracts_report_inside_deep_research_content_frame(self):
        body = f"""
        <!doctype html><html><body>
          <button aria-label="Sources and activity" onclick="setTimeout(() => {{
            const panel = document.createElement('section');
            panel.innerHTML = `
              <h2>Sources</h2>
              <div>1 <a href='https://example.gov/research'>Government research</a></div>
            `;
            document.body.appendChild(panel);
          }}, 350)"></button>
          <main>
            <h1>First Conversation Research Report</h1>
            <h2>Executive summary</h2>
            <p>{long_paragraph('IFRAME REPORT MARKER')}</p>
            <h2>Evidence</h2>
            <p>{long_paragraph('IFRAME EVIDENCE')}</p>
            <p>Source <sup data-citation-index="1">1</sup>.</p>
          </main>
        </body></html>
        """
        frame_url = "https://connector-openai-deep-research.web-sandbox.oaiusercontent.com/report"

        response = export_fixture(self.page, body, frame_url)

        self.assertTrue(response["ok"])
        self.assertEqual(response["result"]["title"], "gpt-First Conversation Research Report")
        self.assertIn("IFRAME REPORT MARKER", response["result"]["markdown"])
        self.assertIn(f'source: "{TARGET_URL}"', response["result"]["markdown"])
        self.assertEqual(response["result"]["sourceCount"], 1)
        self.assertEqual(response["result"]["citationCount"], 1)

    def test_maps_grouped_fullscreen_citations_by_dom_index(self):
        body = f"""
        <!doctype html><html><body>
          <button aria-label="Sources and activity" aria-expanded="false" onclick="setTimeout(() => {{
            const panel = document.createElement('aside');
            panel.innerHTML = `
              <div role='tabpanel'>
                <section aria-labelledby='report-references-citations'>
                  <p id='report-references-citations'>Citations · 2</p>
                  <div role='button' aria-label='Open source 2'>
                    <button data-citation-index='2'>2</button>
                    <a href='https://beta.example/paper'>Beta paper</a>
                    <a href='https://beta.example/paper'>Beta snippet</a>
                  </div>
                  <div role='button' aria-label='Open source 1'>
                    <button data-citation-index='1'>1</button>
                    <a href='https://alpha.example/study'>Alpha study</a>
                  </div>
                </section>
                <section aria-labelledby='report-references-sources-scanned'>
                  <p id='report-references-sources-scanned'>Sources scanned · 1</p>
                  <a href='https://uncited.example/noise'>Uncited source</a>
                </section>
              </div>
            `;
            document.body.appendChild(panel);
          }}, 350)"></button>
          <main>
            <h1>Grouped Citation Report</h1>
            <h2>Evidence</h2>
            <p>{long_paragraph('GROUPED CITATION REPORT')}</p>
            <p>First <sup data-citation-index="1">1</sup>; second <sup data-citation-index="2">2</sup>.</p>
            <h2>Conclusion</h2>
            <p>{long_paragraph('GROUPED CITATION CONCLUSION')}</p>
          </main>
        </body></html>
        """
        frame_url = "https://connector-openai-deep-research.web-sandbox.oaiusercontent.com/report"

        response = export_fixture(self.page, body, frame_url)

        self.assertTrue(response["ok"])
        result = response["result"]
        self.assertEqual(result["sourceCount"], 2)
        self.assertEqual(result["citationCount"], 2, result["markdown"])
        self.assertIn(r"[[1](https://alpha.example/study)]", result["markdown"])
        self.assertIn(r"[[2](https://beta.example/paper)]", result["markdown"])
        self.assertNotIn("uncited.example", result["markdown"])

    def test_renumbers_sparse_chatgpt_indexes_and_appends_references(self):
        # ChatGPT 的 citation 编号是会话级连续的（中间 51-102 属于其他消息），
        # 导出必须重排为连续编号，并在末尾附上与正文编号一致的参考文献列表。
        body = f"""
        <!doctype html><html><body>
          <button aria-label="Sources and activity" aria-expanded="false" onclick="setTimeout(() => {{
            const panel = document.createElement('aside');
            panel.innerHTML = `
              <div role='tabpanel'>
                <section aria-labelledby='report-references-citations'>
                  <p id='report-references-citations'>Citations · 2</p>
                  <div role='button' aria-label='Open source 50'>
                    <button data-citation-index='50'>50</button>
                    <a href='https://alpha.example/sparse'>Sparse alpha study</a>
                  </div>
                  <div role='button' aria-label='Open source 103'>
                    <button data-citation-index='103'>103</button>
                    <a href='https://beta.example/sparse'>Sparse beta paper</a>
                  </div>
                </section>
              </div>
            `;
            document.body.appendChild(panel);
          }}, 350)"></button>
          <main>
            <h1>Sparse Index Report</h1>
            <h2>Evidence</h2>
            <p>{long_paragraph('SPARSE INDEX REPORT')}</p>
            <p>First <sup data-citation-index="50">50</sup>; second <sup data-citation-index="103">103</sup>.</p>
            <h2>Conclusion</h2>
            <p>{long_paragraph('SPARSE INDEX CONCLUSION')}</p>
          </main>
        </body></html>
        """
        frame_url = "https://connector-openai-deep-research.web-sandbox.oaiusercontent.com/report"

        response = export_fixture(self.page, body, frame_url)

        self.assertTrue(response["ok"])
        result = response["result"]
        markdown = result["markdown"]
        # 正文编号重排为连续的 1、2，且不再出现 ChatGPT 的稀疏编号
        self.assertIn(r"First [[1](https://alpha.example/sparse)]", markdown)
        self.assertIn(r"second [[2](https://beta.example/sparse)]", markdown)
        self.assertNotIn("[[50]", markdown)
        self.assertNotIn("[[103]", markdown)
        # 末尾参考文献列表与正文编号一致；慢速路径用来源面板里的真实标题
        self.assertIn("## References", markdown)
        self.assertIn(r"- [[1](https://alpha.example/sparse)] Sparse alpha study", markdown)
        self.assertIn(r"- [[2](https://beta.example/sparse)] Sparse beta paper", markdown)
        self.assertGreater(markdown.index("## References"), markdown.index("SPARSE INDEX CONCLUSION"))
        self.assertTrue(result["sourceCount"] >= 2)

    def test_expands_one_fullscreen_citation_into_multiple_source_links(self):
        body = f"""
        <!doctype html><html><body>
          <button aria-label="Sources and activity" aria-expanded="false" onclick="setTimeout(() => {{
            const panel = document.createElement('aside');
            panel.innerHTML = `
              <div role='tabpanel'>
                <section aria-labelledby='report-references-citations'>
                  <p id='report-references-citations'>Citations · 2</p>
                  <div role='button' aria-label='Open citation 1'>
                    <button data-citation-index='1'>1</button>
                    <a href='https://alpha.example/study'>Alpha study</a>
                    <a href='https://beta.example/paper'>Beta paper</a>
                  </div>
                  <div role='button' aria-label='Open citation 2'>
                    <button data-citation-index='2'>2</button>
                    <a href='https://gamma.example/result'>Gamma result</a>
                  </div>
                </section>
              </div>
            `;
            document.body.appendChild(panel);
          }}, 350)"></button>
          <main>
            <h1>Merged Citation Report</h1>
            <h2>Evidence</h2>
            <p>{long_paragraph('MERGED CITATION REPORT')}</p>
            <p>Merged evidence <sup data-citation-index="1">1</sup>.</p>
            <h2>Conclusion</h2>
            <p>{long_paragraph('MERGED CITATION CONCLUSION')}</p>
            <p>Other evidence <sup data-citation-index="2">2</sup>.</p>
          </main>
        </body></html>
        """
        frame_url = "https://connector-openai-deep-research.web-sandbox.oaiusercontent.com/report"

        response = export_fixture(self.page, body, frame_url)

        self.assertTrue(response["ok"])
        result = response["result"]
        self.assertEqual(result["sourceCount"], 3)
        self.assertEqual(result["citationCount"], 3, result["markdown"])
        self.assertIn(
            r"Merged evidence [[1](https://alpha.example/study)][[2](https://beta.example/paper)].",
            result["markdown"],
        )
        self.assertIn(r"Other evidence [[3](https://gamma.example/result)].", result["markdown"])

    def test_renders_every_citation_inside_a_numeric_span_group(self):
        body = f"""
        <!doctype html><html><body>
          <button aria-label="Sources and activity" aria-expanded="false" onclick="setTimeout(() => {{
            const panel = document.createElement('aside');
            panel.innerHTML = `
              <div role='tabpanel'>
                <section aria-labelledby='report-references-citations'>
                  <p id='report-references-citations'>Citations · 2</p>
                  <div><button data-citation-index='1'>1</button><a href='https://alpha.example/study'>Alpha</a></div>
                  <div><button data-citation-index='2'>2</button><a href='https://beta.example/paper'>Beta</a></div>
                </section>
              </div>
            `;
            document.body.appendChild(panel);
          }}, 350)"></button>
          <main>
            <h1>Grouped Superscript Report</h1>
            <h2>Evidence</h2>
            <p>{long_paragraph('GROUPED SUPERSCRIPT REPORT')}</p>
            <p>Combined evidence <span class="citation-group"><sup data-citation-index="1">1</sup><sup data-citation-index="2">2</sup></span>.</p>
            <p>Linked group <a href="#citations"><sup data-citation-index="1">1</sup><sup data-citation-index="2">2</sup></a>.</p>
            <h2>Conclusion</h2>
            <p>{long_paragraph('GROUPED SUPERSCRIPT CONCLUSION')}</p>
          </main>
        </body></html>
        """
        frame_url = "https://connector-openai-deep-research.web-sandbox.oaiusercontent.com/report"

        response = export_fixture(self.page, body, frame_url)

        self.assertTrue(response["ok"])
        result = response["result"]
        self.assertEqual(result["citationCount"], 4, result["markdown"])
        self.assertIn(
            r"Combined evidence [[1](https://alpha.example/study)][[2](https://beta.example/paper)].",
            result["markdown"],
        )
        self.assertIn(
            r"Linked group [[1](https://alpha.example/study)][[2](https://beta.example/paper)].",
            result["markdown"],
        )

    def test_collects_every_url_from_a_citation_carousel(self):
        body = f"""
        <!doctype html><html><body>
          <script>
            const carouselSources = [
              ['Alpha carousel source', 'https://alpha.example/carousel'],
              ['Beta carousel source', 'https://beta.example/carousel'],
            ];
            let carouselIndex = 0;
            function renderCarousel() {{
              let popover = document.getElementById('citation-popover');
              if (!popover) {{
                popover = document.createElement('div');
                popover.id = 'citation-popover';
                popover.style = 'position: fixed; left: 300px; top: 200px; width: 420px; height: 180px; background: white;';
                popover.innerHTML = `
                  <button onclick='carouselIndex = (carouselIndex + 1) % 2; renderCarousel()'><svg width='20' height='20'><path d='m15 18-6-6 6-6'></path></svg></button>
                  <button onclick='window.__carouselOpacityWhenAdvanced = getComputedStyle(this.parentElement).opacity; carouselIndex = (carouselIndex + 1) % 2; renderCarousel()'><svg width='20' height='20'><path d='m9 18 6-6-6-6'></path></svg></button>
                  <a id='carousel-link'></a>
                  <button aria-label='Open source' onclick='window.__openedSource = true'>↗</button>
                `;
                document.body.appendChild(popover);
              }}
              const link = popover.querySelector('#carousel-link');
              link.textContent = carouselSources[carouselIndex][0];
              link.href = carouselSources[carouselIndex][1];
            }}
          </script>
          <aside style="position: fixed; right: 0; top: 0; width: 280px; background: white;">
            <div role="tabpanel">
              <section aria-labelledby="report-references-citations">
                <p id="report-references-citations">Citations · 2</p>
                <div class="domain-group">
                  <a href="https://alpha.example/carousel">Grouped domain link</a>
                  <button aria-label="Previous item">←</button>
                  <button aria-label="Next item">→</button>
                  <div><button data-citation-index="1">1</button><a href="https://alpha.example/carousel">Alpha source</a></div>
                  <div><button data-citation-index="2">2</button><a href="https://beta.example/carousel">Beta source</a></div>
                </div>
              </section>
            </div>
          </aside>
          <div id="stale-source-card" style="position: fixed; left: 0; top: 0; width: 180px; height: 80px; background: white;">
            <a href="https://link.springer.com/">Springer</a>
            <button aria-label="Previous source">←</button>
            <button aria-label="Next source">→</button>
          </div>
          <main>
            <h1>Citation Carousel Report</h1>
            <h2>Evidence</h2>
            <p>{long_paragraph('CITATION CAROUSEL REPORT')}</p>
            <p>Carousel evidence <a href="https://link.springer.com/"><sup data-citation-index="1" onclick="renderCarousel()">1</sup></a>.</p>
            <h2>Conclusion</h2>
            <p>{long_paragraph('CITATION CAROUSEL CONCLUSION')}</p>
          </main>
        </body></html>
        """
        frame_url = "https://connector-openai-deep-research.web-sandbox.oaiusercontent.com/report"

        response = export_fixture(self.page, body, frame_url)

        self.assertTrue(response["ok"])
        result = response["result"]
        self.assertEqual(result["sourceCount"], 2, result["markdown"])
        self.assertEqual(result["citationCount"], 2, result["markdown"])
        self.assertFalse(self.page.evaluate("Boolean(window.__openedSource)"))
        self.assertEqual(self.page.evaluate("window.__carouselOpacityWhenAdvanced"), "0")
        self.assertNotIn("link.springer.com", result["markdown"])
        self.assertIn(
            r"Carousel evidence [[1](https://alpha.example/carousel)][[2](https://beta.example/carousel)].",
            result["markdown"],
        )

    def test_waits_for_reused_citation_carousel_to_update_all_urls(self):
        body = f"""
        <!doctype html><html><body>
          <script>
            const carouselSources = [
              ['Source one', 'https://alpha.example/one'],
              ['Source fifteen', 'https://alpha.example/fifteen'],
              ['Source eighteen', 'https://alpha.example/eighteen'],
            ];
            let carouselIndex = 0;
            function renderCarousel() {{
              const link = document.querySelector('#citation-popover a');
              link.textContent = carouselSources[carouselIndex][0];
              link.href = carouselSources[carouselIndex][1];
            }}
            function openCitationCarousel() {{
              window.setTimeout(() => {{
                carouselIndex = 0;
                renderCarousel();
              }}, 350);
            }}
            function showNextSource() {{
              window.setTimeout(() => {{
                carouselIndex = (carouselIndex + 1) % carouselSources.length;
                renderCarousel();
              }}, 350);
            }}
          </script>
          <div id="citation-popover" style="position: fixed; left: 300px; top: 200px; width: 420px; height: 180px; background: white;">
            <button aria-label="Previous source">←</button>
            <button aria-label="Next source" onclick="showNextSource()">→</button>
            <a href="https://link.springer.com/">Unrelated stale card</a>
          </div>
          <aside style="position: fixed; right: 0; top: 0; width: 280px; background: white;">
            <div role="tabpanel">
              <section aria-labelledby="report-references-citations">
                <p id="report-references-citations">Citations · 3</p>
                <div><button data-citation-index="1">1</button><a href="https://alpha.example/one">Source one</a></div>
                <div><button data-citation-index="15">15</button><a href="https://alpha.example/fifteen">Source fifteen</a></div>
                <div><button data-citation-index="18">18</button><a href="https://alpha.example/eighteen">Source eighteen</a></div>
              </section>
            </div>
          </aside>
          <main>
            <h1>Delayed Carousel Report</h1>
            <h2>Evidence</h2>
            <p>{long_paragraph('DELAYED CAROUSEL REPORT')}</p>
            <p>Grouped evidence <sup data-citation-index="1" onclick="openCitationCarousel()">1</sup>.</p>
            <h2>Conclusion</h2>
            <p>{long_paragraph('DELAYED CAROUSEL CONCLUSION')}</p>
          </main>
        </body></html>
        """
        frame_url = "https://connector-openai-deep-research.web-sandbox.oaiusercontent.com/report"

        response = export_fixture(self.page, body, frame_url)

        self.assertTrue(response["ok"])
        result = response["result"]
        self.assertNotIn("link.springer.com", result["markdown"])
        self.assertIn(
            "Grouped evidence "
            r"[[1](https://alpha.example/one)]"
            r"[[2](https://alpha.example/fifteen)]"
            r"[[3](https://alpha.example/eighteen)].",
            result["markdown"],
        )

    def test_matches_only_the_cards_present_in_each_linkless_citation_tooltip(self):
        body = f"""
        <!doctype html><html><body>
          <script>
            const citationCards = {{
              1: [
                ['arxiv.org', 'Solubility prediction of organic molecules with molecular dynamics simulations'],
                ['acs.figshare.com', 'Rational Solvent Selection for Pharmaceutical Impurity Purge'],
              ],
              2: [
                ['researchgate.net', 'A single-source solubility study'],
              ],
            }};
            let activeCitation = 0;
            let activeCard = 0;

            function renderLinklessTooltip() {{
              let tooltip = document.getElementById('citation-tooltip');
              if (!tooltip) {{
                tooltip = document.createElement('div');
                tooltip.id = 'citation-tooltip';
                tooltip.setAttribute('role', 'tooltip');
                tooltip.setAttribute('data-state', 'open');
                tooltip.style = 'position: fixed; left: 300px; top: 200px; width: 344px; height: 159px; background: white;';
                document.body.appendChild(tooltip);
              }}
              const card = citationCards[activeCitation][activeCard];
              const controls = citationCards[activeCitation].length > 1
                ? `<button aria-label='←'>←</button><button aria-label='→' onclick='showNextLinklessCard()'>→</button>`
                : '';
              tooltip.innerHTML = `${{controls}}<div class='card-domain'></div><div class='card-title'></div>`;
              tooltip.querySelector('.card-domain').textContent = card[0];
              tooltip.querySelector('.card-title').textContent = card[1];
            }}

            function openLinklessCitation(index) {{
              activeCitation = index;
              activeCard = 0;
              renderLinklessTooltip();
            }}

            function showNextLinklessCard() {{
              const cards = citationCards[activeCitation];
              activeCard = (activeCard + 1) % cards.length;
              renderLinklessTooltip();
            }}
          </script>
          <aside style="position: fixed; right: 0; top: 0; width: 360px; background: white;">
            <div role="tabpanel">
              <section aria-labelledby="linkless-citations">
                <p id="linkless-citations">Citations · 4</p>
                <div>
                  <a href="https://arxiv.org/abs/2104.10792">arxiv.org</a>
                  <div><button data-citation-index="1">1</button><a href="https://arxiv.org/abs/2104.10792">Solubility prediction of organic molecules with molecular dynamics simulations</a></div>
                  <div><button data-citation-index="18">18</button><a href="https://arxiv.org/abs/2407.03434">Predicting another property from molecular structure</a></div>
                </div>
                <div><button data-citation-index="15">15</button><a href="https://acs.figshare.com/collections/Rational_Solvent_Selection_for_Pharmaceutical_Impurity_Purge/3984081">Rational Solvent Selection for Pharmaceutical Impurity Purge</a></div>
                <div><button data-citation-index="2">2</button><a href="https://www.researchgate.net/publication/12345_A_single-source_solubility_study">A single-source solubility study</a></div>
              </section>
            </div>
          </aside>
          <main>
            <h1>Mixed Citation Tooltip Report</h1>
            <h2>Evidence</h2>
            <p>{long_paragraph('MIXED CITATION TOOLTIP REPORT')}</p>
            <p>Multiple sources <sup role="button" tabindex="0" data-citation-index="1" onclick="openLinklessCitation(1)">1</sup>.</p>
            <p>Single source <sup role="button" tabindex="0" data-citation-index="2" onclick="openLinklessCitation(2)">2</sup>.</p>
            <h2>Conclusion</h2>
            <p>{long_paragraph('MIXED CITATION TOOLTIP CONCLUSION')}</p>
          </main>
        </body></html>
        """
        frame_url = "https://connector-openai-deep-research.web-sandbox.oaiusercontent.com/report"

        started_at = self.page.evaluate("Date.now()")
        response = export_fixture(self.page, body, frame_url)
        elapsed_ms = self.page.evaluate("Date.now()") - started_at

        self.assertTrue(response["ok"])
        markdown = response["result"]["markdown"]
        self.assertIn(
            "Multiple sources "
            r"[[1](https://arxiv.org/abs/2104.10792)]"
            r"[[2](https://acs.figshare.com/collections/Rational_Solvent_Selection_for_Pharmaceutical_Impurity_Purge/3984081)].",
            markdown,
        )
        self.assertIn(
            "Single source "
            r"[[3](https://www.researchgate.net/publication/12345_A_single-source_solubility_study)].",
            markdown,
        )
        self.assertNotIn(
            r"Single source [[3](https://www.researchgate.net/publication/12345_A_single-source_solubility_study)][",
            markdown,
        )
        self.assertLess(elapsed_ms, 4000)

    def test_preserves_citation_urls_inside_tables(self):
        body = f"""
        <!doctype html><html><body>
          <aside><div role="tabpanel"><section aria-labelledby="table-citations">
            <p id="table-citations">Citations · 2</p>
            <div><button data-citation-index="1">1</button><a href="https://alpha.example/table">Alpha table source</a></div>
            <div><button data-citation-index="2">2</button><a href="https://beta.example/table">Beta table source</a></div>
          </section></div></aside>
          <main>
            <h1>Table Citation Report</h1>
            <h2>Evidence</h2>
            <p>{long_paragraph('TABLE CITATION REPORT')}</p>
            <table>
              <thead><tr><th>Study</th><th>Evidence</th></tr></thead>
              <tbody>
                <tr><td>Alpha</td><td>First result <sup data-citation-index="1">1</sup></td></tr>
                <tr><td>Beta</td><td>Second result <sup data-citation-index="2">2</sup></td></tr>
              </tbody>
            </table>
            <h2>Conclusion</h2>
            <p>{long_paragraph('TABLE CITATION CONCLUSION')}</p>
          </main>
        </body></html>
        """
        frame_url = "https://connector-openai-deep-research.web-sandbox.oaiusercontent.com/report"

        response = export_fixture(self.page, body, frame_url)

        self.assertTrue(response["ok"])
        markdown = response["result"]["markdown"]
        self.assertIn(r"First result [[1](https://alpha.example/table)]", markdown)
        self.assertIn(r"Second result [[2](https://beta.example/table)]", markdown)

    def test_renumbers_distinct_urls_that_chatgpt_labels_as_one(self):
        body = f"""
        <!doctype html><html><body><main>
          <h1>Repeated Label Report</h1>
          <h2>Evidence</h2>
          <p>{long_paragraph('REPEATED LABEL REPORT')}</p>
          <p>Sources <a href="https://alpha.example/repeated">[1]</a><a href="https://beta.example/repeated">[1]</a>.</p>
          <h2>Conclusion</h2>
          <p>{long_paragraph('REPEATED LABEL CONCLUSION')}</p>
        </main></body></html>
        """
        frame_url = "https://connector-openai-deep-research.web-sandbox.oaiusercontent.com/report"

        response = export_fixture(self.page, body, frame_url)

        self.assertTrue(response["ok"])
        result = response["result"]
        self.assertIn(
            r"Sources [[1](https://alpha.example/repeated)][[2](https://beta.example/repeated)].",
            result["markdown"],
        )

    def test_clicks_show_code_before_exporting_mermaid(self):
        body = f"""
        <!doctype html><html><body>
        <script>
          function showMermaidCode(control) {{
            const rendered = control.closest('pre');
            const widget = control.closest('.mermaid-widget');
            setTimeout(() => {{
              rendered.remove();
              const sourcePre = document.createElement('pre');
              const code = document.createElement('code');
              code.className = 'language-meriad';
              code.textContent = 'flowchart TD\\nA[Raw node] --> B{{Result}}';
              sourcePre.appendChild(code);
              widget.appendChild(sourcePre);
            }}, 80);
          }}
          function resetMermaid() {{
            const template = document.getElementById('rendered-mermaid-template');
            document.querySelector('.mermaid-widget').replaceChildren(template.content.cloneNode(true));
          }}
        </script>
        <template id="rendered-mermaid-template"><pre><style>#mermaid-rendered {{ color: red; }}</style><svg><text>RENDERED MERMAID LABEL MUST NOT BE EXPORTED</text></svg><p class="show-code" style="opacity: 0" onclick="showMermaidCode(this)">显示代码</p></pre></template>
        <aside><div role="tabpanel"><section aria-labelledby="mermaid-citations"><p id="mermaid-citations">Citations · 1</p><div><button data-citation-index="1">1</button><a href="https://alpha.example/mermaid">Mermaid source</a></div></section></div></aside>
        <main>
          <h1>Mermaid Report</h1>
          <h2>Evidence</h2>
          <p>{long_paragraph('MERMAID REPORT')}</p>
          <div class="mermaid-widget">
            <pre><style>#mermaid-rendered {{ color: red; }}</style><svg><text>RENDERED MERMAID LABEL MUST NOT BE EXPORTED</text></svg><p class="show-code" style="opacity: 0" onclick="showMermaidCode(this)">显示代码</p></pre>
          </div>
          <p>Diagram evidence <sup data-citation-index="1" onclick="resetMermaid()">1</sup>.</p>
          <h2>Conclusion</h2>
          <p>{long_paragraph('MERMAID CONCLUSION')}</p>
        </main></body></html>
        """
        frame_url = "https://connector-openai-deep-research.web-sandbox.oaiusercontent.com/report"

        response = export_fixture(self.page, body, frame_url)

        self.assertTrue(response["ok"])
        markdown = response["result"]["markdown"]
        self.assertIn("```mermaid\nflowchart TD", markdown)
        self.assertIn('A["Raw node"] --> B{"Result"}', markdown)
        self.assertNotIn("```meriad", markdown)
        self.assertNotIn("#mermaid-rendered", markdown)
        self.assertNotIn("RENDERED MERMAID LABEL", markdown)

    def test_popup_waits_for_explicit_start(self):
        self.page.add_init_script(
            f"""
            window.__exportFrames = [];
            window.__sourceOpenFrames = [];
            window.__copiedMarkdown = '';
            Object.defineProperty(navigator, 'clipboard', {{
              value: {{ writeText: async (text) => {{ window.__copiedMarkdown = text; }} }},
            }});
            window.chrome = {{
              tabs: {{
                query: async () => [{{ id: 42, url: {json.dumps(TARGET_URL)} }}],
              sendMessage: async (_tabId, message, options) => {{
                if (message?.type === 'DEEP_RESEARCH_OPEN_SOURCES') {{
                  window.__sourceOpenFrames.push(options?.frameId ?? 0);
                  return {{ ok: true, openedSources: options?.frameId === 7 }};
                }}
                if (message?.type === 'DEEP_RESEARCH_EXPORT_STRUCTURED_REPORT') return {{ ok: false }};
                if (message?.type === 'DEEP_RESEARCH_REPORT_HEADING') return {{ ok: true, heading: '' }};
                window.__exportFrames.push(options?.frameId ?? 0);
                  if (options?.frameId !== 7) return {{ ok: false, error: 'Wrong frame' }};
                  return {{
                    ok: true,
                    result: {{
                      title: 'gpt-Selected Fullscreen Report',
                      filename: 'gpt-Selected Fullscreen Report',
                      markdown: String.raw`# gpt-Selected Fullscreen Report

See [source](https://example.com).

\\[
x^2 + y^2
\\]

[ \\Delta G = x^2 ]

[ordinary bracketed text]`,
                      sourceCount: 3,
                      citationCount: 3,
                      warnings: [],
                    }},
                  }};
                }},
              }},
              webNavigation: {{
                getAllFrames: async () => [
                  {{ frameId: 0, parentFrameId: -1, url: {json.dumps(TARGET_URL)} }},
                  {{ frameId: 7, parentFrameId: 0, url: 'https://connector-openai-deep-research.web-sandbox.oaiusercontent.com/' }},
                ],
              }},
              downloads: {{ download: async () => 1 }},
            }};
            """
        )
        self.page.goto((ROOT / "popup.html").as_uri(), wait_until="domcontentloaded")

        self.assertEqual(self.page.evaluate("window.__exportFrames.length"), 0)
        self.assertTrue(self.page.locator("#downloadButton").is_disabled())
        self.assertTrue(self.page.locator("#copyButton").is_disabled())
        self.assertTrue(self.page.locator("#latexFixButton").is_disabled())
        self.assertIn("start detection", self.page.locator("#status").inner_text().lower())

        self.page.locator("#startButton").click()
        self.page.wait_for_function("window.__exportFrames.length === 1")
        self.page.wait_for_function("!document.querySelector('#downloadButton').disabled")

        self.assertIn("Page detected", self.page.locator("#status").inner_text())
        self.assertEqual(self.page.evaluate("window.__sourceOpenFrames"), [7, 0])
        self.assertEqual(self.page.evaluate("window.__exportFrames"), [7])
        self.assertFalse(self.page.locator("#copyButton").is_disabled())
        self.assertFalse(self.page.locator("#latexFixButton").is_disabled())

        self.page.locator("#latexFixButton").click()
        self.assertTrue(self.page.locator("#latexFixButton").is_disabled())
        self.page.locator("#copyButton").click()
        self.page.wait_for_function("window.__copiedMarkdown.length > 0")
        copied = self.page.evaluate("window.__copiedMarkdown")
        self.assertIn("$$\nx^2 + y^2\n$$", copied)
        self.assertIn("$$\n\\Delta G = x^2\n$$", copied)
        self.assertNotIn("\\[", copied)
        self.assertIn("[ordinary bracketed text]", copied)
        self.assertIn("[source](https://example.com)", copied)
        fenced = self.page.evaluate(
            "value => fixLatexDisplayDelimiters(value)",
            "```text\n[ \\not_math ]\n```",
        )
        self.assertEqual(fenced["replacementCount"], 0)
        self.assertEqual(fenced["markdown"], "```text\n[ \\not_math ]\n```")
        # 整行只有引用链接（URL 含下划线等公式特征）不能被误判成裸公式。
        citation_line = self.page.evaluate(
            "value => fixLatexDisplayDelimiters(value)",
            "[[1](https://example.com/my_paper_2024)]",
        )
        self.assertEqual(citation_line["replacementCount"], 0)
        self.assertEqual(citation_line["markdown"], "[[1](https://example.com/my_paper_2024)]")
        self.assertEqual(
            self.page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"),
            True,
        )

    def test_download_uses_named_anchor_with_report_title_filename(self):
        self.page.add_init_script(
            f"""
            window.__anchorDownloadArgs = null;
            window.chrome = {{
              tabs: {{
                query: async () => [{{ id: 42, url: {json.dumps(TARGET_URL)}, title: '6aa6e282-9290-83e9-a810-87cd1ae29cc1' }}],
                sendMessage: async (_tabId, message) => {{
                  if (message?.type === 'DEEP_RESEARCH_OPEN_SOURCES') return {{ ok: true, openedSources: false }};
                  return {{
                    ok: true,
                    result: {{
                      title: 'gpt-电子围栏技术调研报告',
                      filename: 'gpt-电子围栏技术调研报告',
                      markdown: '# gpt-电子围栏技术调研报告\\n\\nSee [source](https://example.com).',
                      sourceCount: 1,
                      citationCount: 1,
                      warnings: [],
                    }},
                  }};
                }},
              }},
              webNavigation: {{
                getAllFrames: async () => [{{ frameId: 0, parentFrameId: -1, url: {json.dumps(TARGET_URL)} }}],
              }},
            }};
            """
        )
        self.page.goto((ROOT / "popup.html").as_uri(), wait_until="domcontentloaded")
        # Chrome 忽略 chrome.downloads.download 的 filename 参数，生产代码改用
        # anchor download 属性命名；测试拦截该函数并断言 data URL 与文件名。
        self.page.evaluate(
            """() => {
                window.triggerNamedDownload = (url, filename) => {
                    window.__anchorDownloadArgs = { url, filename };
                };
            }"""
        )

        self.page.locator("#startButton").click()
        self.page.wait_for_function("!document.querySelector('#downloadButton').disabled")
        self.page.locator("#downloadButton").click()
        self.page.wait_for_function("window.__anchorDownloadArgs !== null")

        args = self.page.evaluate("window.__anchorDownloadArgs")
        self.assertTrue(args["url"].startswith("data:text/markdown;charset=utf-8;base64,"))
        # 标签页标题是会话 UUID 时不采用；文件名使用插件识别出的报告标题。
        self.assertRegex(args["filename"], r"^gpt-电子围栏技术调研报告_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}\.md$")
        # data URL 内容可解码回报告正文。
        import base64
        decoded = base64.b64decode(args["url"].split(",", 1)[1]).decode("utf-8")
        self.assertIn("# gpt-电子围栏技术调研报告", decoded)
        self.assertIn("download started", self.page.locator("#status").inner_text().lower())

    def test_structured_payload_export_preserves_latex_delimiters(self):
        marker = "\ue200cite1\ue201"
        report_md = (
            "# 电子围栏结构化报告\n\n"
            f"正文引用 {marker} 出现。\n\n"
            "行间公式 \\[ E = mc^2 \\] 与行内 \\frac{a}{b} 保留。"
        )
        # 与真实页面一致的两层编码：会话 JSON 作为字符串嵌在内层，引用走 content_references。
        inner = {
            "record": {
                "report_message": {
                    "content": {"parts": [report_md]},
                    "status": "DONE",
                },
                "content_references": [
                    {"matched_text": marker, "prefix": "", "safe_urls": ["https://example.com/structured-source"]}
                ],
            }
        }
        payload_json = json.dumps({"wrapper": json.dumps(inner, ensure_ascii=False)}, ensure_ascii=False)
        script = f"streamController.enqueue({json.dumps(payload_json, ensure_ascii=False)});"
        body = f"<!doctype html><html><body><script>{script}</script></body></html>"

        response = export_fixture(self.page, body, "https://chatgpt.com/share/s-structured-1")

        self.assertTrue(response["ok"])
        result = response["result"]
        self.assertEqual(result["title"], "gpt-电子围栏结构化报告")
        self.assertIn("\\[ E = mc^2 \\]", result["markdown"])
        self.assertIn("\\frac{a}{b}", result["markdown"])
        self.assertIn(r"[[1](https://example.com/structured-source)]", result["markdown"])
        self.assertEqual(result["citationCount"], 1)
        # 快路径同样在末尾追加参考文献列表（中文报告用中文标题）；
        # payload 没有来源标题时用 URL 派生的可读标题（host · 路径词）
        self.assertIn("## 参考文献", result["markdown"])
        self.assertIn(
            r"- [[1](https://example.com/structured-source)] example.com · structured source",
            result["markdown"],
        )

    def test_structured_export_selects_payload_matching_heading(self):
        # 同一会话有多份深度调研时，数据流里有多个 report payload；
        # 必须按当前打开报告的标题选 payload，而不是总取第一份。
        def build_payload(title, marker, url):
            report_md = f"# {title}\n\n正文引用 {marker} 出现。"
            inner = {
                "record": {
                    "report_message": {"content": {"parts": [report_md]}, "status": "DONE"},
                    "content_references": [
                        {"matched_text": marker, "prefix": "", "safe_urls": [url]}
                    ],
                }
            }
            payload_json = json.dumps(
                {"wrapper": json.dumps(inner, ensure_ascii=False)}, ensure_ascii=False
            )
            return f"streamController.enqueue({json.dumps(payload_json, ensure_ascii=False)});"

        script = (
            build_payload("第一份调研报告", "\ue200citeA\ue201", "https://example.com/first-source")
            + build_payload("第二份调研报告", "\ue200citeB\ue201", "https://example.com/second-source")
        )
        body = f"<!doctype html><html><body><script>{script}</script></body></html>"

        def run_structured(match_title):
            return self.page.evaluate(
                """(matchTitle) => new Promise((resolve) => {
                    window.__exportListener(
                      {
                        type: 'DEEP_RESEARCH_EXPORT_STRUCTURED_REPORT',
                        titlePrefix: 'gpt-',
                        sourceUrl: window.__sourceUrl,
                        matchTitle,
                      },
                      null,
                      resolve,
                    );
                })""",
                match_title,
            )

        self.page.route(
            "**/*",
            lambda route: route.fulfill(
                status=200, content_type="text/html; charset=utf-8", body=body
            ),
        )
        self.page.add_init_script(
            """
            window.chrome = {
              runtime: {
                onMessage: { addListener(listener) { window.__exportListener = listener; } }
              }
            };
            """
        )
        self.page.add_init_script(f"window.__sourceUrl = {json.dumps(TARGET_URL)}")
        self.page.goto("https://chatgpt.com/share/s-multi-report", wait_until="domcontentloaded")
        self.page.add_script_tag(path=str(CONTENT_SCRIPT))

        # 打开的是第二份：按标题选中第二份 payload
        second = run_structured("第二份调研报告")
        self.assertTrue(second["ok"], second)
        self.assertEqual(second["result"]["title"], "gpt-第二份调研报告")
        self.assertIn(r"[[1](https://example.com/second-source)]", second["result"]["markdown"])
        self.assertNotIn("first-source", second["result"]["markdown"])

        # 标题不匹配任何 payload 时返回失败，交给 DOM 路径兜底
        missing = run_structured("不存在的报告标题")
        self.assertFalse(missing["ok"])

        # 不指定标题（分享页单报告场景）保持旧行为：取第一份
        first = run_structured("")
        self.assertTrue(first["ok"])
        self.assertEqual(first["result"]["title"], "gpt-第一份调研报告")
        self.assertIn(r"[[1](https://example.com/first-source)]", first["result"]["markdown"])

    def test_fast_path_prefers_matching_structured_payload(self):
        self.page.add_init_script(
            f"""
            window.__exportFrames = [];
            window.__headingFrames = [];
            window.__structuredProbes = [];
            window.__structuredMatchTitles = [];
            window.chrome = {{
              tabs: {{
                query: async () => [{{ id: 42, url: {json.dumps(TARGET_URL)} }}],
                sendMessage: async (_tabId, message, options) => {{
                  if (message?.type === 'DEEP_RESEARCH_OPEN_SOURCES') return {{ ok: true, openedSources: false }};
                  if (message?.type === 'DEEP_RESEARCH_EXPORT_STRUCTURED_REPORT') {{
                    window.__structuredProbes.push(options?.frameId ?? 0);
                    window.__structuredMatchTitles.push(message?.matchTitle || '');
                    return {{
                      ok: true,
                      result: {{
                        title: 'gpt-电子围栏结构化报告',
                        filename: 'gpt-电子围栏结构化报告',
                        markdown: '# gpt-电子围栏结构化报告\\n\\n快路径正文 [[1](https://example.com/source)]。行间 \\\\[ E = mc^2 \\\\]。',
                        sourceCount: 1,
                        citationCount: 1,
                        warnings: [],
                      }},
                    }};
                  }}
                  if (message?.type === 'DEEP_RESEARCH_REPORT_HEADING') {{
                    window.__headingFrames.push(options?.frameId ?? 0);
                    return {{
                      ok: true,
                      heading: options?.frameId === 7 ? '电子围栏结构化报告' : '',
                      visible: options?.frameId === 7,
                    }};
                  }}
                  window.__exportFrames.push(options?.frameId ?? 0);
                  return {{ ok: false, error: 'slow path should not run' }};
                }},
              }},
              webNavigation: {{
                getAllFrames: async () => [
                  {{ frameId: 0, parentFrameId: -1, url: {json.dumps(TARGET_URL)} }},
                  {{ frameId: 7, parentFrameId: 0, url: 'https://connector-openai-deep-research.web-sandbox.oaiusercontent.com/' }},
                ],
              }},
            }};
            """
        )
        self.page.goto((ROOT / "popup.html").as_uri(), wait_until="domcontentloaded")

        self.page.locator("#startButton").click()
        self.page.wait_for_function("!document.querySelector('#downloadButton').disabled")

        # 快路径命中：先收集各 frame 标题（报告 frame 优先），再带 matchTitle 探测
        # 顶层 payload，完全不需要逐 frame 导出。
        self.assertEqual(self.page.evaluate("window.__structuredProbes"), [0])
        self.assertEqual(self.page.evaluate("window.__structuredMatchTitles"), ["电子围栏结构化报告"])
        self.assertEqual(self.page.evaluate("window.__headingFrames"), [7, 0])
        self.assertEqual(self.page.evaluate("window.__exportFrames"), [])
        self.assertIn("Page detected", self.page.locator("#status").inner_text())
        self.assertIn("电子围栏结构化报告", self.page.locator("#summary").inner_text())

    def test_manifest_injects_into_deep_research_frames(self):
        manifest = json.loads((ROOT / "manifest.json").read_text())
        content_script = manifest["content_scripts"][0]

        self.assertIn("webNavigation", manifest["permissions"])
        self.assertIn(
            "https://connector-openai-deep-research.web-sandbox.oaiusercontent.com/*",
            manifest["host_permissions"],
        )
        self.assertTrue(content_script["all_frames"])
        self.assertTrue(content_script["match_origin_as_fallback"])


if __name__ == "__main__":
    unittest.main()
