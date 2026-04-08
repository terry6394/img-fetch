# img-fetch Skill - Requirements & Backlog

## Project Overview

**Project:** Claude Code Skill for automated product image fetching
**Location:** `/Users/cyril/code/luxeway/youzanskills/img_fetch`
**Input:** Excel/CSV/JSON files with product info (商品名称, 商品规格)
**Test Data:** `tests/fixtures/sample_test.xlsx` (5 products, 5 brands)

---

## Current State Analysis

### Completed Components

| Component | Status | Location |
|-----------|--------|----------|
| File readers (Excel/CSV/JSON) | ✅ Complete | `src/img_fetch/readers/` |
| Brand extraction | ✅ Complete | `src/img_fetch/core/brand_extractor.py` |
| File naming | ✅ Complete | `src/img_fetch/core/file_namer.py` |
| Manifest/Report generation | ✅ Complete | `src/img_fetch/writers/` |
| Directory structure | ✅ Complete | `src/img_fetch/config.py` |
| Browser automation | ✅ Complete | `src/img_fetch/automation/` |
| Rate limiting | ✅ Complete | `src/img_fetch/utils/rate_limiter.py` |
| Exception handling | ✅ Complete | `src/img_fetch/utils/exceptions.py` |
| Product data model | ✅ Complete | `src/img_fetch/core/product.py` |
| Image saving | ✅ Complete | `src/img_fetch/writers/image_saver.py` |
| Description extraction (async) | ✅ Complete | `src/img_fetch/agents/descriptor.py` |
| Search strategy planning (LLM) | ✅ Complete | `src/img_fetch/agents/planner.py` |
| E-commerce fetcher skeleton | ⚠️ Partial | `src/img_fetch/fetchers/` |
| Main entry point | ⚠️ Partial | `src/img_fetch/main.py` |

---

## Missing/Incomplete Features

### Critical Gaps

1. **Fetcher Orchestration Not Integrated**
   - `BrandFetcher` and `EcommerceFetcher` classes exist but are NOT used by `main.py`
   - `main.py` uses mock implementations (`_try_fetch_from_url`, `_try_brand_fetcher`)
   - No proper fallback chain execution

2. **Youzan URL Fetching Not Implemented**
   - `youzan.com` is in `ECOMMERCE_SITES` config but no dedicated fetcher exists
   - No Youzan-specific page parsing logic

3. **Image Search Fallback Missing**
   - Referenced in `IMAGE_SOURCE_PRIORITY` but never implemented
   - No Google/Bing image search integration

4. **Page Description Extraction Not Integrated**
   - `DescriptionExtractor` class exists but is never called
   - `ImageMetadata` fields (title, description, keywords, alt_text) remain empty

5. **SearchStrategyPlanner Not Used**
   - LLM-based planning exists but workflow bypasses it
   - Products don't benefit from intelligent source selection

6. **Retry Logic Not Implemented**
   - `MAX_RETRIES` and `RETRY_DELAYS` defined in config but not used
   - No exponential backoff implementation

7. **Error Recovery Missing**
   - No circuit breaker pattern
   - No graceful degradation when sources fail

---

## Prioritized Backlog

### Phase 1: Core Fetching Pipeline (P0)

#### Feature 1: Fetcher Orchestration
**Priority:** P0 - Critical
**Description:** Wire up the existing `BrandFetcher` and `EcommerceFetcher` classes to the main workflow with proper fallback chain.

**Acceptance Criteria:**
- [ ] `BrandFetcher` is invoked for products with known brands
- [ ] `EcommerceFetcher` is invoked for products with direct product URLs
- [ ] Fallback chain: brand_site → ecommerce → image_search
- [ ] Each attempt is logged in `product.attempts` list
- [ ] `product.tried_sources` tracks which sources have been attempted

**Implementation Notes:**
- Modify `main.py` `_fetch_product_image()` to use actual fetchers
- Create `FetcherOrchestrator` class to manage the fallback chain
- Respect `IMAGE_SOURCE_PRIORITY` from config

---

#### Feature 2: Youzan Fetcher
**Priority:** P0 - Critical
**Description:** Implement Youzan e-commerce platform fetcher for products listed on youzan.com.

**Acceptance Criteria:**
- [ ] `YouzanFetcher` class extends `BaseFetcher`
- [ ] Handles Youzan-specific page structure and anti-bot measures
- [ ] Extracts product images from Youzan product pages
- [ ] Respects Youzan rate limits (30 req/min per config)
- [ ] Integrates with `DescriptionExtractor` for metadata

**Youzan Page Patterns:**
```python
# Expected selectors for Youzan
YOUZAN_SELECTORS = {
    "main_image": "#J_goodsPic img",
    "gallery": ".goods-gallery img",
    "thumbnail": "[class*='thumb'] img",
}
```

---

### Phase 2: Multi-Source Fallback (P0)

#### Feature 3: Image Search Fallback
**Priority:** P0 - Critical
**Description:** Implement Google/Bing image search as final fallback when other sources fail.

**Acceptance Criteria:**
- [ ] `ImageSearchFetcher` class extends `BaseFetcher`
- [ ] Performs search using product name + spec as query
- [ ] Uses browser automation to navigate to image search
- [ ] Extracts and validates image URLs from results
- [ ] Logs source as "image_search" in attempts

**Search Query Format:** `{brand} {product_name} {spec} product image`

---

#### Feature 4: Retry Logic with Exponential Backoff
**Priority:** P0 - Critical
**Description:** Implement retry mechanism for failed fetches with exponential backoff.

**Acceptance Criteria:**
- [ ] Retries use `RETRY_DELAYS` config: [5, 15, 30] seconds
- [ ] Maximum retries per source: `MAX_RETRIES` (3)
- [ ] Anti-bot detection triggers immediate retry (no backoff)
- [ ] Network errors trigger backoff retry
- [ ] `product.retries` counter is incremented on each retry

---

### Phase 3: Metadata & Intelligence (P1)

#### Feature 5: Page Description Extraction Integration
**Priority:** P1 - High
**Description:** Integrate `DescriptionExtractor` to populate `ImageMetadata` fields.

**Acceptance Criteria:**
- [ ] `DescriptionExtractor.extract_from_url()` is called after successful image fetch
- [ ] `ImageMetadata` fields populated: title, description, keywords, alt_text
- [ ] Extraction is non-blocking (async)
- [ ] Extraction failures are logged but don't fail the overall fetch

---

#### Feature 6: LLM Strategy Planner Integration
**Priority:** P1 - High
**Description:** Use `SearchStrategyPlanner` to determine optimal source order per product.

**Acceptance Criteria:**
- [ ] `SearchStrategyPlanner.plan_search_strategy()` is called per product
- [ ] Strategy is logged in product metadata
- [ ] Sources are tried in LLM-recommended order
- [ ] Fallback to default priority if LLM call fails

---

### Phase 4: Reliability & Observability (P2)

#### Feature 7: Error Recovery & Circuit Breaker
**Priority:** P2 - Medium
**Description:** Implement circuit breaker pattern to prevent cascading failures.

**Acceptance Criteria:**
- [ ] Track failure rate per source domain
- [ ] "Open" circuit after 5 consecutive failures
- [ ] Circuit auto-resets after 60 seconds
- [ ] Log circuit state changes

---

#### Feature 8: Enhanced Logging & Tracing
**Priority:** P2 - Medium
**Description:** Add structured logging for debugging and monitoring.

**Acceptance Criteria:**
- [ ] Log each fetch attempt with source, URL, status
- [ ] Log image dimensions after download
- [ ] Log total duration per product
- [ ] Log memory usage on large batches

---

## Image Fetching Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                        START: Load Products                     │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    For Each Product                              │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 1. Check if image already fetched (resume support)        │  │
│  │ 2. Build search query: {brand} {name} {spec}             │  │
│  │ 3. Optionally call LLM Strategy Planner                   │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SOURCE FALLBACK CHAIN                         │
│                                                                 │
│  ┌─────────────────┐                                           │
│  │ 1. BRAND_SITE   │ ──► Known brand website search           │
│  └────────┬────────┘                                           │
│           │ FAIL                                               │
│           ▼                                                    │
│  ┌─────────────────┐                                           │
│  │ 2. ECOMMERCE    │ ──► Direct URL or search on platform    │
│  └────────┬────────┘                                           │
│           │ FAIL                                               │
│           ▼                                                    │
│  ┌─────────────────┐                                           │
│  │ 3. IMAGE_SEARCH │ ──► Google/Bing image search            │
│  └────────┬────────┘                                           │
│           │ FAIL                                               │
│           ▼                                                    │
│  ┌─────────────────┐                                           │
│  │    FAILED       │ ──► Record error, move to next product │
│  └─────────────────┘                                           │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    POST-FETCH PROCESSING                         │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 1. Download image to: output/images/{BRAND}/             │  │
│  │ 2. Extract page metadata (title, description, keywords)  │  │
│  │ 3. Update product.status = "success" or "failed"        │  │
│  │ 4. Record attempt in product.attempts[]                   │  │
│  │ 5. Update manifest.json                                  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    END: Generate Report                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Detailed Requirements by Feature

### Fetcher Interface Contract

All fetchers MUST implement `BaseFetcher`:

```python
class BaseFetcher(ABC):
    @abstractmethod
    def fetch(self, product: Product) -> Optional[str]:
        """Fetch image for product. Returns path or None."""
        pass

    @abstractmethod
    def supports(self, product: Product) -> bool:
        """Check if this fetcher can handle this product."""
        pass

    @abstractmethod
    def can_retry(self) -> bool:
        """Whether this fetcher supports retries."""
        pass
```

### Data Flow Requirements

1. **Input:** Product with fields: name, spec, brand, product_url
2. **Output:** Image saved to `output/images/{BRAND}/{BRAND}_{NAME}_{SPEC}.jpg`
3. **Metadata:** `ImageMetadata` attached to product with all available fields

### Error Handling Requirements

| Error Type | Behavior |
|------------|----------|
| `AntiBotDetectedError` | Switch to next source immediately |
| `BrowserError` | Retry with backoff, then next source |
| `ImageNotFoundError` | Try next source or fallback |
| `NetworkError` | Retry with backoff, then next source |
| `RateLimitError` | Wait and retry within same source |

### Configuration Requirements

All thresholds must be configurable via `config.py`:

```python
# Required config values
IMAGE_SOURCE_PRIORITY = ["brand_site", "ecommerce", "image_search"]
MAX_RETRIES = 3
RETRY_DELAYS = [5, 15, 30]  # seconds
RATE_LIMITS = {...}  # requests per minute per domain
BROWSER_CONFIG = {...}
```

---

## Test Requirements

### Unit Tests

| Module | Test Coverage Target |
|--------|---------------------|
| `core/brand_extractor.py` | > 90% |
| `core/file_namer.py` | > 90% |
| `fetchers/base.py` | 100% |
| `fetchers/brand_fetcher.py` | > 80% |
| `fetchers/ecommerce_fetcher.py` | > 80% |
| `writers/manifest_writer.py` | > 90% |

### Integration Tests

1. **End-to-end workflow test** with 5 products from `sample_test.xlsx`
2. **Fallback chain test** - verify each source is tried in order
3. **Resume test** - stop mid-way, restart, verify state preserved
4. **Rate limiting test** - verify delays between requests

---

## File Structure (Expected After Implementation)

```
src/img_fetch/
├── main.py                    # Entry point (needs refactoring)
├── config.py                  # Configuration
├── core/
│   ├── product.py             # Product data model
│   ├── brand_extractor.py     # Brand extraction
│   └── file_namer.py          # File naming
├── readers/
│   ├── base.py
│   ├── excel_reader.py
│   ├── csv_reader.py
│   ├── json_reader.py
│   └── factory.py
├── fetchers/
│   ├── base.py                # Abstract base
│   ├── brand_fetcher.py       # Brand website fetcher
│   ├── ecommerce_fetcher.py  # Amazon/JD/Taobao fetcher
│   ├── youzan_fetcher.py     # TODO: Youzan fetcher
│   ├── image_search_fetcher.py # TODO: Google/Bing image search
│   └── orchestrator.py        # TODO: Fetcher orchestration
├── agents/
│   ├── planner.py             # LLM strategy planner
│   └── descriptor.py          # Page description extractor
├── automation/
│   ├── browser.py             # Selenium browser controller
│   └── human_behavior.py      # Human-like behavior
├── writers/
│   ├── manifest_writer.py     # manifest.json
│   ├── report_writer.py       # report.xlsx
│   └── image_saver.py         # Image download & save
└── utils/
    ├── exceptions.py
    └── rate_limiter.py
```

---

## Open Questions

1. **Youzan Authentication:** Does Youzan require login? If so, how are credentials managed?
2. **Image Quality:** Is there a minimum resolution requirement? Target size?
3. **Batch Size:** Is there a maximum products per run? Memory constraints?
4. **Concurrent Runs:** Can multiple instances run simultaneously? Share rate limits?
5. **Brand Coverage:** Which brands are in scope? Only Canada Goose, Haglofs, Helly Hansen, Stone Island, L.I.M?

---

## Next Steps for Developer

1. **Immediate:** Replace mock implementations in `main.py` with actual fetcher classes
2. **Next Sprint:** Implement `YouzanFetcher` and `ImageSearchFetcher`
3. **Following:** Add retry logic and circuit breaker
4. **Finally:** Integrate LLM planner and description extractor
