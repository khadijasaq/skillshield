"""SkillShield's local web UI (docs/product-plan.md P6; docs/product-spec.md §22).

Stdlib-only: ``http.server.ThreadingHTTPServer`` plus a single static
HTML/CSS/vanilla-JS page. No new runtime dependency, no build chain, per
the decision recorded in DECISIONS.md ("P5/P6"). The UI contains zero
security logic -- it calls ``skillshield.pipeline.assess()`` once per
request and renders exactly what comes back.
"""
