# Citizenship Search App

Discovery-first app for family-tree evidence gathering focused on Polish citizenship research.

## What it includes

- Case and claim schema with provenance and conflict tracking.
- Multilingual normalization/transliteration helpers for Polish/Ukrainian/Russian variants.
- Source adapter framework for UK, Poland, Ukraine, Russia, and Polish Armed Forces in the West data channels.
- Manual archive request template and tracking primitives.
- Candidate scoring and contradiction reconciliation.
- Export-ready outputs: timeline, discovery report, missing-doc packet, and citizenship bundle draft.
- Translation pipeline that preserves originals and records translation metadata + source hash.
- Security primitives for encrypted storage, role checks, and tamper-evident audit log chains.

## Run locally

```bash
python -m pip install -e .
python -m pytest
citizenship-search --query "Roman Senus Stryj 1957"
```

## Notes

- Current adapters are static/demo connectors and should be replaced with live integrations and request workflows.
- This project supports research operations and is not legal advice.
